"""Analyze the interactive preference study and optionally run paired draft-note probes."""

import argparse
import fcntl
import hashlib
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from visual_prefs.interaction_astra import AstraSession


def read(p):
    return json.loads(p.read_text())


def save(p, value):
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    tmp.replace(p)


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def signature(prompt, context, hashes):
    return hashlib.sha256(
        json.dumps([prompt, context, hashes], sort_keys=True).encode()
    ).hexdigest()


def evidence(root, path):
    receipt = read(path)
    reqfile = root / receipt["request"]
    req = read(reqfile)
    hashes = [digest(root / p) for p in receipt["images"]]
    if (
        hashes != [i["sha256"] for i in req["images"]]
        or signature(req["instruction"], req["context"], hashes) != receipt["input_sha256"]
    ):
        raise ValueError(f"Request hash mismatch: {path}")
    results = [read(p) for p in reqfile.parent.glob("attempt-*/result.json")]
    if not any(
        r["reply"] == receipt["reply"] and r["thread_id"] == receipt["thread"] for r in results
    ):
        raise ValueError(f"Result mismatch: {path}")
    valid_attempt = next(
        p.parent
        for p in reqfile.parent.glob("attempt-*/result.json")
        if read(p)["reply"] == receipt["reply"] and read(p)["thread_id"] == receipt["thread"]
    )
    events = [
        json.loads(line) for line in (valid_attempt / "events.jsonl").read_text().splitlines()
    ]
    messages = [
        e["item"]["text"]
        for e in events
        if e["type"] == "item.completed" and e.get("item", {}).get("type") == "agent_message"
    ]
    if (
        not messages
        or json.loads(messages[-1].strip().removeprefix("```json").removesuffix("```").strip())
        != receipt["reply"]
        or not any(e.get("thread_id") == receipt["thread"] for e in events)
    ):
        raise ValueError(f"Raw CLI event mismatch: {path}")
    return receipt, req


def correct_letter(choice, correct, options):
    if choice not in options or len(options) != 2:
        raise ValueError("Expected a valid binary choice")
    return choice if correct else next(k for k in options if k != choice)


def visual(root, ep, run=False):
    if ep["mode"] != "isolated":
        return None
    directory = (root / ep["transcript"]).parent
    draft = (directory / "visual-only.md").read_text()
    final = (directory / "memory.md").read_text()
    audit, _ = evidence(root, directory / "receipts/audit.json")
    if not audit["reply"].get("question", "").strip() or draft == final:
        return None
    folder = root / "visual-only-comparisons" / ep["scenario"]
    receipt = folder / "receipt.json"
    if not run and not receipt.exists():
        return None
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / ".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        cold, coldreq = evidence(root, directory / "receipts/transfer-cold.json")
        note, req = evidence(root, directory / "receipts/transfer-note.json")
        frame = root / note["images"][0]
        context = req["context"]
        if (
            len(note["images"]) != 1
            or cold["images"] != note["images"]
            or coldreq["instruction"] != req["instruction"]
            or coldreq["context"] != context | {"memory": ""}
            or context["memory"] != final
            or req["persistent"]
            or coldreq["persistent"]
        ):
            raise ValueError(f"Unmatched original comparisons: {directory}")
        ctx = context | {"memory": draft}
        key = signature(req["instruction"], ctx, [digest(frame)])
        expected = correct_letter(
            note["reply"]["choice"], ep["scores"]["transfer_note"], ctx["options"]
        )
        if receipt.exists():
            data, _ = evidence(root, receipt)
            if data["input_sha256"] != key:
                raise ValueError(f"Changed draft comparison: {receipt}")
        else:
            session = AstraSession(folder / "session", model=req["model"])
            reply = session.ask(req["instruction"], ctx, [frame])
            request = sorted(session.log_dir.glob("*/request.json"))[-1]
            data = {
                "reply": reply,
                "request": str(request.relative_to(root)),
                "thread": session.session_id,
                "images": note["images"],
                "input_sha256": key,
            }
            save(receipt, data)
        choice = data["reply"].get("choice")
        return {
            "family": ep["scenario"],
            "draft_correct": choice == expected,
            "valid": choice in ctx["options"],
            "draft_choice": choice,
            "expected": expected,
            "cold_correct": ep["scores"]["transfer_cold"],
            "note_correct": ep["scores"]["transfer_note"],
            "receipt": str(receipt.relative_to(root)),
            "receipt_sha256": digest(receipt),
        }


def episode_row(root, ep):
    directory = (root / ep["transcript"]).parent
    transcript = read(directory / "transcript.json")
    if transcript != ep["turns"]:
        raise ValueError(f"Transcript mismatch: {directory}")
    calls = {k: evidence(root, root / v) for k, v in read(directory / "calls.json").items()}

    def reply(k):
        return calls[k][0]["reply"]

    def checked(label, condition):
        if not condition:
            raise ValueError(f"{directory}: {label}")

    from visual_prefs.interaction_sim import prepare

    plan = read(root / "plan.json")

    def trial(phase):
        seed = (
            37
            + 11 * plan["families"].index(ep["scenario"])
            + 103 * plan["phase_order"].index(phase)
        )
        return prepare(ep["scenario"], phase, seed)

    scores = ep["scores"]
    teaching = trial("teach")
    first = reply("first-choice")["choice"]
    checked(
        "teaching score mismatch",
        scores["teaching_miss"] == (first != teaching.expected(ep["profile"])),
    )
    motions = list(teaching.person_menu(first).items())
    random.Random(f"person-choice/{ep['scenario']}").shuffle(motions)
    expected_motion = teaching.expected_response(ep["profile"], first)
    motion = reply("person-response")["response"]
    motion_label = calls["person-response"][1]["context"]["motion_options"][motion]
    move, label = motions[ord(motion) - ord("A")]
    checked(
        "feedback score mismatch",
        label == motion_label and scores["feedback_matches_persona"] == (move == expected_motion),
    )
    checked("private motion absent", any(t["text"] == motion_label for t in transcript))
    draft = (directory / "visual-only.md").read_text()
    final = (directory / "memory.md").read_text()
    audit = reply("audit")
    questions = {}
    for phase, key in (
        ("audit", "audit"),
        ("transfer", "transfer-learner"),
        ("exception", "exception-learner"),
    ):
        q = reply(key).get("question", "").strip()
        if q:
            a = reply(phase + "-answer")["answer"]
            checked("question missing", any(t["text"].strip() == q for t in transcript))
            checked("answer missing", any(t["text"] == a for t in transcript))
            questions[phase] = {"question": q, "answer": a}
    probes = {}
    for phase, pre in (("transfer", "transfer"), ("exception", "control")):
        cold, req = calls[phase + "-cold"]
        options = req["context"]["options"]
        expected = correct_letter(cold["reply"]["choice"], scores[pre + "_cold"], options)
        probe = trial(phase)
        checked(
            "independent scorer mismatch",
            options == probe.options and expected == probe.expected(ep["profile"]),
        )
        arms = {}
        for arm, suffix, metric in (
            ("cold", "cold", "cold"),
            ("note", "note", "note"),
            ("tentative", "learner", "before_question"),
            ("executed", "act" if phase in questions else "learner", "learner"),
        ):
            key = phase + "-" + suffix
            r = reply(key)
            v = r["choice"]
            checked(
                "score mismatch", v in options and (v == expected) == scores[pre + "_" + metric]
            )
            if arm in ("note", "tentative"):
                checked("image pairing", cold["images"] == calls[key][0]["images"])
            arms[arm] = {
                "choice": v,
                "action": options[v],
                "correct": v == expected,
                "reason": r["reason"],
            }
        checked(
            "executed action missing",
            any(
                t["channel"] == "executed probe action"
                and t["text"] == arms["executed"]["action"] + " " + arms["executed"]["reason"]
                and (root / t["clip"]).is_file()
                for t in transcript
            ),
        )
        probes[phase] = {"expected": options[expected], **arms}
    robot = {
        d[0]["thread"]
        for k, d in calls.items()
        if not k.endswith(("-cold", "-answer"))
        and k not in {"transfer-note", "exception-note"}
        and k not in {"person-response"}
    }
    robot.add(calls["audit"][0]["thread"])
    checked("robot continuity", robot == {ep["robot_thread"]})
    person = {
        d[0]["thread"] for k, d in calls.items() if k.endswith("-answer") or k == "person-response"
    }
    checked("person continuity", person == {ep["person_thread"]})
    return {
        "mode": ep["mode"],
        "family": ep["scenario"],
        "profile": ep["profile"],
        "teaching_miss": scores["teaching_miss"],
        "feedback_agreement": scores["feedback_matches_persona"],
        "motion": motion_label,
        "motion_id": move,
        "expected_motion_id": expected_motion,
        "teaching_action": teaching.options[first],
        "preferred_teaching_action": teaching.options[teaching.expected(ep["profile"])],
        "audit_observation": audit["observation"],
        "audit_interpretation": audit["interpretation"],
        "dialogue": questions,
        "draft": draft,
        "first_probe_note": final,
        "final_note": (directory / "final-note.md").read_text(),
        "draft_changed": draft != final,
        "probes": probes,
        "robot_thread": ep["robot_thread"],
        "person_thread": ep["person_thread"],
        "prior_note_count": len(read(directory / "library-before.json")),
        "transcript": ep["transcript"],
    }


def totals(rows):
    result = {
        "episodes": len(rows),
        "teaching_misses": sum(r["teaching_miss"] for r in rows),
        "feedback_agreements": sum(r["feedback_agreement"] for r in rows),
        "questions": sum(len(r["dialogue"]) for r in rows),
        "episodes_without_questions": sum(not r["dialogue"] for r in rows),
        "draft_changes": sum(r["draft_changed"] for r in rows),
    }
    result["questions_by_stage"] = {
        k: sum(k in r["dialogue"] for r in rows) for k in ("audit", "transfer", "exception")
    }
    for phase in ("transfer", "exception"):
        pairs = [r["probes"][phase] for r in rows]
        result[phase] = {
            k: sum(p[k]["correct"] for p in pairs)
            for k in ("cold", "note", "tentative", "executed")
        }
        result[phase].update(
            gains=sum(not p["cold"]["correct"] and p["note"]["correct"] for p in pairs),
            losses=sum(p["cold"]["correct"] and not p["note"]["correct"] for p in pairs),
        )
    return result


def render(summary):
    out = [
        "# Interactive preference study",
        "",
        "Each probe uses a fresh cold choice, a fresh choice with the first-probe note, and an executed choice by the continuing robot. The continuing robot could ask the person before acting. Scores use the task's prespecified preference or exception.",
        "",
    ]
    rows = summary["episodes"]
    for mode, title in (
        ("isolated", "Original preferences"),
        ("contrast", "Conditional diagnostic contrasts"),
        ("continuous", "Longitudinal learner"),
    ):
        group = [r for r in rows if r["mode"] == mode]
        t = summary["groups"][mode]
        out += [
            "## " + title,
            "",
            f"{t['teaching_misses']}/{len(group)} teaching actions missed the preference. Person feedback agreed with the brief in {t['feedback_agreements']}/{len(group)} episodes. The robot asked {t['questions']} questions across all stages. {t['episodes_without_questions']} episodes had no questions, and {t['draft_changes']} pre-question drafts changed before transfer.",
            "",
            "| Family | Teaching miss | Feedback agrees | Questions at | Draft changed | Transfer C/N/E | Exception C/N/E |",
            "|---|---|---|---|---|---|---|",
        ]
        for r in group:

            def marks(phase):
                return " / ".join(
                    "✓" if r["probes"][phase][k]["correct"] else "×"
                    for k in ("cold", "note", "executed")
                )

            out += [
                f"| [{r['family']}]({r['transcript']}) | {r['teaching_miss']} | {r['feedback_agreement']} | {', '.join(r['dialogue']) or 'none'} | {r['draft_changed']} | {marks('transfer')} | {marks('exception')} |"
            ]
        out += [
            "",
            "C/N/E shows correct choices for cold, first-probe note and executed action, in that order.",
            "",
        ]
        for phase in ("transfer", "exception"):
            p = t[phase]
            out += [
                f"{phase.title()} had {p['cold']}/{len(group)} cold, {p['note']}/{len(group)} written-note and {p['executed']}/{len(group)} executed choices correct. The written note gained {p['gains']} and lost {p['losses']} relative to cold. The continuing learner initially selected {p['tentative']}/{len(group)} correctly before any probe question.",
                "",
            ]
    out += ["## Transcript examples", ""]
    original = [r for r in rows if r["mode"] == "isolated"]
    seen = set()
    categories = (
        lambda p: not p["cold"]["correct"] and p["note"]["correct"],
        lambda p: not p["executed"]["correct"],
        lambda p: not p["note"]["correct"],
        lambda p: p["cold"]["correct"] and p["executed"]["correct"],
    )
    for matches in categories:
        for r in [
            r for r in original if r["family"] not in seen and matches(r["probes"]["transfer"])
        ][:1]:
            seen.add(r["family"])
            p = r["probes"]["transfer"]
            out += [
                f"**{r['family']}**. The person selected “{r['motion']}”. The robot recorded “{r['audit_observation']}”. The fresh cold choice was “{p['cold']['action']}”, and the written-note choice was “{p['note']['action']}”. The continuing learner executed “{p['executed']['action']}” on transfer. The expected action was “{p['expected']}”. [Transcript]({r['transcript']})",
                "",
            ]
    out += ["## Visual draft and dialogue", ""]
    for r in original:
        if r["draft_changed"]:
            out += [
                f"**{r['family']}**",
                "",
                "Draft",
                "",
                r["draft"].strip() or "(empty)",
                "",
                "First-probe note",
                "",
                r["first_probe_note"].strip() or "(empty)",
                "",
            ]
    comparisons = summary["visual_comparisons"]
    eligible = sum("audit" in r["dialogue"] and r["draft_changed"] for r in original)
    out += [
        f"Matched draft comparisons cover {len(comparisons)}/{eligible} eligible originals. "
        f"Cold, draft and conversational-note choices were correct on "
        f"{sum(v['cold_correct'] for v in comparisons)}, {sum(v['draft_correct'] for v in comparisons)} "
        f"and {sum(v['note_correct'] for v in comparisons)} of these transfers. "
        f"The conversational note gained {sum(v['note_correct'] and not v['draft_correct'] for v in comparisons)} "
        f"and lost {sum(v['draft_correct'] and not v['note_correct'] for v in comparisons)} relative to the draft.",
        "",
    ]
    for v in comparisons:
        out += [
            f"{v['family']} transfer correctness was {v['cold_correct']} cold, {v['draft_correct']} with the draft and {v['note_correct']} with the conversational note. [Matched trial]({v['receipt']})",
            "",
        ]
    c = summary["continuity"]
    out += [
        "## Continuity and final-library retention",
        "",
        f"The longitudinal sequence used {c['robot_threads']} robot thread(s) and {c['person_threads']} person thread(s). Prior written-note counts in episode order were {c['prior_note_counts']}. The independent held-out probes tested a fresh reader and the frozen written library.",
        "",
    ]
    for phase, p in summary["retention"]["summary"].items():
        out += [
            f"{phase.title()} cold scored {p['cold_correct']}/{p['cold_scored']}, and retrieval with notes scored {p['library_correct']}/{p['library_scored']}. Across {p['paired_scored']} valid pairs there were {p['gains']} gains and {p['losses']} losses. {p['planned']} probes were planned.",
            "",
        ]
    out += [
        "## Limits",
        "",
        "Each family contributes one development episode per ordinary condition. Conditional contrasts select families after an initially correct choice and can change the persona. The final written note can include spoken clarification. A fresh draft comparison covers only original episodes where an audit question changed the note. Each condition samples the model once per scene. Changes across samples can reflect sampling variation. The continuing learner also has thread history and can ask probe questions. Final-library probes combine retrieval and decision quality. All feedback and executed motions come from a simulator with a role-played person.",
        "",
    ]
    return "\n".join(out)


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--visual-only", action="store_true")
    parser.add_argument("--comparisons-only", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    if args.comparisons_only:
        if not args.visual_only:
            parser.error("--comparisons-only requires --visual-only")
        episodes = [
            read(root / "episodes/isolated" / f / "episode.json")
            for f in read(root / "plan.json")["families"]
        ]
    else:
        manifest = read(root / "report_manifest.json")
        episodes = manifest["episodes"]
    comparisons = [v for ep in episodes if (v := visual(root, ep, args.visual_only)) is not None]
    if args.comparisons_only:
        print(f"Verified {len(comparisons)} paired visual-draft comparisons")
        return
    families = read(root / "plan.json")["families"]
    originals = [e for e in episodes if e["mode"] == "isolated"]
    contrasts = [e["scenario"] for e in episodes if e["mode"] == "contrast"]
    if (
        [e["scenario"] for e in originals] != families
        or [e["scenario"] for e in episodes if e["mode"] == "continuous"] != families
        or contrasts != [e["scenario"] for e in originals if not e["scores"]["teaching_miss"]]
    ):
        raise ValueError("Manifest is incomplete or disagrees with the study plan")
    rows = [episode_row(root, ep) for ep in episodes]
    groups = {
        m: totals([r for r in rows if r["mode"] == m])
        for m in ("isolated", "contrast", "continuous")
    }
    chain = [r for r in rows if r["mode"] == "continuous"]
    summary = {
        "episodes": rows,
        "groups": groups,
        "visual_comparisons": comparisons,
        "retention": read(root / manifest["artifacts"]["Retention scores"]),
        "continuity": {
            "robot_threads": len({r["robot_thread"] for r in chain}),
            "person_threads": len({r["person_thread"] for r in chain}),
            "prior_note_counts": [r["prior_note_count"] for r in chain],
        },
    }
    save(root / "summary.json", summary)
    (root / "analysis.md").write_text(render(summary))
    print(root / "analysis.md")


if __name__ == "__main__":
    main()
