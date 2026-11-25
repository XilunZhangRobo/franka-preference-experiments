"""Replay visible robot observations with frozen, caller-supplied prompts.

evaluate_episode writes under root/cases/case_id. Different policies need different
case IDs or roots. Only shared_draft permits reuse across cases.
"""

import fcntl
import hashlib
import json
import math
from pathlib import Path

from .interaction_astra import AstraSession


def _read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _save(path, value):
    temp = path.with_suffix(".part")
    temp.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    temp.replace(path)


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _id(value):
    # Preserve insertion order, including the actual order in which options are shown.
    raw = json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(raw.encode()).hexdigest()


def _visible_signature(model, instruction, context, hashes):
    return _id([model, instruction, context, hashes])


def _required_text(value, key, *, empty=True):
    text = value.get(key)
    if not isinstance(text, str) or (not empty and not text.strip()):
        raise ValueError(f"Invalid text field {key}")
    return text


def _note(reply):
    note = _required_text(reply, "note").strip()
    title = _required_text(reply, "title").strip()
    if not note:
        return ""
    return f"# {title}\n\n{note}\n" if title else note + "\n"


def _valid_choice(reply, options):
    choice = _required_text(reply, "choice", empty=False)
    if choice not in options:
        raise ValueError("Model selected an unavailable choice")
    _required_text(reply, "reason")
    return choice


def _journaled_response(directory, signature, *, pending=False):
    """Adopt the latest complete request if receipt publication was interrupted."""
    requests = sorted(directory.glob("*/request.json"))
    if not requests:
        return None
    request_path = requests[-1]
    request = _read(request_path)
    actual = _visible_signature(
        request["model"],
        request["instruction"],
        request["context"],
        [img["sha256"] for img in request["images"]],
    )
    if actual != signature:
        return None
    for image in request["images"]:
        if _sha(request_path.parent / image["file"]) != image["sha256"]:
            raise ValueError(f"Archived model input changed at {request_path}")
    if pending:
        return None
    results = list(request_path.parent.glob("attempt-*/result.json"))
    if len(results) > 1:
        raise ValueError(f"Multiple final results in {request_path.parent}")
    if not results:
        return None
    result = _read(results[0])
    return request_path, results[0], result


class _Replay:
    def __init__(self, directory, model):
        self.directory = directory
        self.model = model
        self.receipts = directory / "receipts"
        self.receipts.mkdir(exist_ok=True)
        self.turns = []

    def call(
        self, stage, actor, channel, instruction, context, images, *, session, persistent=False
    ):
        hashes = [_sha(p) for p in images]
        signature = _visible_signature(self.model, instruction, context, hashes)
        target = self.receipts / (stage + ".json")
        session_dir = self.directory / "sessions" / session
        if target.exists():
            receipt = _read(target)
            if receipt["input_sha256"] != signature or receipt["session"] != session:
                raise ValueError(f"Checkpoint input mismatch at {target}")
            _verify_receipt(target)
        else:
            done = _journaled_response(
                session_dir, signature, pending=(session_dir / "pending.json").exists()
            )
            if not done:
                cli = AstraSession(session_dir, persistent=persistent, model=self.model)
                cli.ask(instruction, context, images)
                done = _journaled_response(session_dir, signature)
            if not done:
                raise RuntimeError(f"Missing durable adapter response at {session_dir}")
            request, result_file, result = done
            receipt = {
                "input_sha256": signature,
                "session": session,
                "thread": result["thread_id"],
                "request": str(request.relative_to(self.directory)),
                "result": str(result_file.relative_to(self.directory)),
                "reply": result["reply"],
            }
            _save(target, receipt)
        self.turns.append(
            {
                "stage": stage,
                "actor": actor,
                "channel": channel,
                "receipt": str(target.relative_to(self.directory)),
                "thread": receipt["thread"],
                "reply": receipt["reply"],
            }
        )
        return receipt["reply"], target


def _verify_receipt(path):
    receipt = _read(path)
    base = path.parent.parent
    reqfile = base / receipt["request"]
    req = _read(reqfile)
    hashes = [i["sha256"] for i in req["images"]]
    if [_sha(reqfile.parent / i["file"]) for i in req["images"]] != hashes or (
        _visible_signature(req["model"], req["instruction"], req["context"], hashes)
        != receipt["input_sha256"]
    ):
        raise ValueError(f"Archived receipt input mismatch at {path}")
    result = _read(base / receipt["result"])
    if result["reply"] != receipt["reply"] or result["thread_id"] != receipt["thread"]:
        raise ValueError(f"Archived receipt output mismatch at {path}")
    return receipt


def evaluate_episode(
    root,
    case_id,
    case,
    policy,
    input_seed=None,
    *,
    shared_draft=None,
    shared_selective=None,
    branch_selective=False,
):
    """Evaluate one case. Unrecognized input fields never enter robot-visible context.

    case contains task, action, optional choice_reason, seconds, images, heard, private_brief
    and probes (transfer/control each with task, options, images and expected). An empty
    probes mapping is valid. quiet=True enables descriptive no-feedback outcomes.
    policy contains audit, refine, decide, selective and answer prompt strings and optional model.
    shared_draft accepts an original draft_receipt path from another observationally identical case.
    shared_selective maps phases to donor tentative_receipt paths. branch_selective=True
    runs fresh final contexts so the first and second persona can use symmetric branches.
    """
    case_id = str(case_id)
    parts = Path(case_id)
    if not parts.parts or parts.is_absolute() or ".." in parts.parts:
        raise ValueError("case_id must be a relative path without traversal")
    directory = Path(root).resolve() / "cases" / parts
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / ".lock").open("a") as guard:
        fcntl.flock(guard, fcntl.LOCK_EX)
        return _evaluate(
            directory,
            case_id,
            case,
            policy,
            input_seed,
            shared_draft,
            shared_selective or {},
            branch_selective,
        )


def _evaluate(
    directory, case_id, case, policy, input_seed, donor, shared_selective, branch_selective
):
    model = policy.get("model", "gpt-6.2-astra")
    prompts = {
        k: _required_text(policy, k, empty=False)
        for k in ("audit", "refine", "decide", "selective", "answer")
    }
    images = [Path(p) for p in case["images"]]
    seconds = list(case["seconds"])
    if not images or len(seconds) != len(images) or any(not math.isfinite(t) for t in seconds):
        raise ValueError("Supply one finite timestamp for each teaching frame")
    audit_context = {
        "task": _required_text(case, "task", empty=False),
        "your_action": _required_text(case, "action", empty=False),
        "seconds": seconds,
        "heard": [],
    }
    for event in case.get("heard", []):
        # Only the time, audible speaker and actual text may cross this boundary.
        audit_context["heard"].append({k: event[k] for k in ("t", "speaker", "text") if k in event})
    if case.get("choice_reason") is not None:
        audit_context["choice_reason"] = _required_text(case, "choice_reason")
    brief = _required_text(case, "private_brief")
    probes = {}
    for phase, probe in case["probes"].items():
        if phase not in {"transfer", "control"}:
            raise ValueError("Unknown probe type")
        options = probe["options"]
        if not isinstance(options, dict) or len(options) < 2 or probe["expected"] not in options:
            raise ValueError("Invalid options or scorer")
        frames = [Path(p) for p in probe["images"]]
        if not frames:
            raise ValueError("Probe needs an observation")
        probes[phase] = (
            {"task": _required_text(probe, "task", empty=False), "options": options},
            frames,
            probe["expected"],
        )
    hashes = [_sha(p) for p in images]
    draft_sig = _visible_signature(model, prompts["audit"], audit_context, hashes)
    donor = Path(donor).resolve() if donor else None
    if set(shared_selective) - set(probes):
        raise ValueError("Shared selective receipt supplied for an absent probe")
    selective_donors = {phase: Path(path).resolve() for phase, path in shared_selective.items()}
    identity = {
        "protocol_version": 1,
        "branch_selective": branch_selective,
        "shared_selective_receipt_hashes": {
            phase: _sha(p) for phase, p in selective_donors.items()
        },
        "case_id": case_id,
        "model": model,
        "prompts": prompts,
        "seed_metadata": input_seed,
        "quiet": bool(case.get("quiet")),
        "private_brief": brief,
        "audit_context": audit_context,
        "audit_image_hashes": hashes,
        "probes": {
            k: {"public": ctx, "image_hashes": [_sha(p) for p in imgs], "expected": score}
            for k, (ctx, imgs, score) in probes.items()
        },
        "shared_draft_receipt_sha256": _sha(donor) if donor else None,
    }
    identity_hash = _id(identity)
    identity_file = directory / "identity.json"
    if identity_file.exists() and _id(_read(identity_file)) != identity_hash:
        raise ValueError(f"Case inputs or policy changed at {directory}")
    _save(identity_file, identity)
    replay = _Replay(directory, model)

    if donor:
        data = _verify_receipt(donor)
        if data["input_sha256"] != draft_sig or data["session"] != "writer":
            raise ValueError("Shared draft differs from the original public audit")
        audit, draft_receipt = data["reply"], donor
        replay.turns.append(
            {
                "stage": "audit",
                "actor": "robot",
                "channel": "shared visual draft",
                "source": str(donor),
                "receipt_sha256": _sha(donor),
                "reply": audit,
            }
        )
    else:
        audit, draft_receipt = replay.call(
            "audit",
            "robot",
            "visual draft",
            prompts["audit"],
            audit_context,
            images,
            session="writer",
        )
    for key in ("observation", "interpretation", "question"):
        _required_text(audit, key)
    draft = _note(audit)
    (directory / "draft.md").write_text(draft)
    question = audit["question"].strip()
    audit_answer, refined, note = None, None, draft

    def answer(stage, task, q, frames):
        value, _ = replay.call(
            stage + "-answer",
            "person",
            "spoken answer",
            prompts["answer"],
            {"task": task, "private_brief": brief, "question": q},
            frames,
            session=stage + "-person",
        )
        return _required_text(value, "answer", empty=False)

    if question:
        audit_answer = answer("audit", audit_context["task"], question, [])
        refined, _ = replay.call(
            "refine",
            "robot",
            "written note",
            prompts["refine"],
            {"draft": draft, "question": question, "person_answer": audit_answer},
            [],
            session="refiner",
        )
        note = _note(refined)
    (directory / "post-answer.md").write_text(note)
    forced = {}
    outcomes = {}
    opportunities = {"audit": {"available": 1, "asked": int(bool(question))}}
    for phase in ("transfer", "control"):
        if phase not in probes:
            opportunities[phase] = {"available": 0, "asked": 0}
            continue
        ctx, frames, expected = probes[phase]
        readings = {}
        for arm, memory in (("draft", draft), ("post_answer", note)):
            public = {**ctx, "memory": memory}
            key = _visible_signature(model, prompts["decide"], public, [_sha(p) for p in frames])
            reused = key in forced
            if not reused:
                forced[key] = replay.call(
                    phase + "-" + arm,
                    "fresh robot",
                    "forced choice",
                    prompts["decide"],
                    public,
                    frames,
                    session="forced-" + key,
                )
            reply, path = forced[key]
            choice = _valid_choice(reply, ctx["options"])
            readings[arm] = {
                "reply": reply,
                "correct": choice == expected,
                "input_sha256": key,
                "reused": reused,
                "receipt": str(path.relative_to(directory)),
            }
        session = phase + "-selective"
        selective_ctx = {**ctx, "memory": note}
        selective_key = _visible_signature(
            model, prompts["selective"], selective_ctx, [_sha(p) for p in frames]
        )
        share_status = "not requested"
        tentative_path = selective_donors.get(phase)
        if tentative_path:
            donor_reply = _verify_receipt(tentative_path)
            if donor_reply["session"] != session:
                raise ValueError("Donor is not a tentative decision for the requested probe")
            if donor_reply["input_sha256"] == selective_key:
                tentative = donor_reply["reply"]
                share_status = "identical input"
                replay.turns.append(
                    {
                        "stage": phase + "-selective",
                        "actor": "robot",
                        "channel": "shared tentative decision",
                        "source": str(tentative_path),
                        "receipt_sha256": _sha(tentative_path),
                        "reply": tentative,
                    }
                )
            else:
                share_status = "inputs differ"
        if share_status != "identical input":
            tentative, tentative_path = replay.call(
                phase + "-selective",
                "robot",
                "tentative decision",
                prompts["selective"],
                selective_ctx,
                frames,
                session=session,
                persistent=True,
            )
        branch = bool(branch_selective or phase in selective_donors)
        before = _valid_choice(tentative, ctx["options"])
        q = _required_text(tentative, "question").strip() if "question" in tentative else ""
        spoken = None
        final = tentative
        if q:
            spoken = answer(phase, ctx["task"], q, frames)
            if branch:
                final, _ = replay.call(
                    phase + "-final",
                    "robot",
                    "fresh branch decision",
                    prompts["decide"],
                    {
                        **selective_ctx,
                        "tentative_reply": tentative,
                        "question": q,
                        "person_answer": spoken,
                    },
                    frames,
                    session=phase + "-branch",
                )
            else:
                final, _ = replay.call(
                    phase + "-final",
                    "robot",
                    "final decision",
                    prompts["decide"],
                    {**ctx, "question": q, "person_answer": spoken},
                    [],
                    session=session,
                    persistent=True,
                )
        after = _valid_choice(final, ctx["options"])
        opportunities[phase] = {"available": 1, "asked": int(bool(q))}
        outcomes[phase] = {
            "expected": expected,
            **readings,
            "selective": {
                "tentative": tentative,
                "question": q,
                "tentative_receipt": str(tentative_path),
                "share_status": share_status,
                "final_context": "fresh branch"
                if q and branch
                else ("same thread" if q else "tentative action"),
                "answer": spoken,
                "final": final,
                "before_correct": before == expected,
                "after_correct": after == expected,
            },
            "audit_note_change": int(readings["post_answer"]["correct"])
            - int(readings["draft"]["correct"]),
            "selective_change": int(after == expected) - int(before == expected),
        }
    changes = {}
    for channel, field in (("audit", "audit_note_change"), ("selective", "selective_change")):
        diffs = [p[field] for p in outcomes.values()]
        changes[channel] = {
            "pairs": len(diffs),
            "gains": diffs.count(1),
            "losses": diffs.count(-1),
            "net": sum(diffs),
        }
    result = {
        "case_id": case_id,
        "identity_sha256": identity_hash,
        "seed_metadata": input_seed,
        "draft_receipt": str(draft_receipt),
        "draft_reply": audit,
        "draft_note": draft,
        "audit_question": question,
        "audit_answer": audit_answer,
        "refined_reply": refined,
        "post_answer_note": note,
        "quiet": identity["quiet"],
        "quiet_checks": (
            {
                "draft_note_written": bool(draft),
                "asked": bool(question),
                "post_answer_note_written": bool(note),
            }
            if identity["quiet"]
            else None
        ),
        "opportunities": opportunities,
        "changes": changes,
        "probes": outcomes,
    }
    _save(directory / "transcript.json", replay.turns)
    _save(directory / "result.json", result)
    return result
