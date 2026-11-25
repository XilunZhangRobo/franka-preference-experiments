"""Read-only verification of the prospective audit-policy comparison and its report."""

import argparse
import hashlib
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.audit_revision import scene_case, tray_case
from tools.verify_interactions import Validator, digest, read, require
from visual_prefs.interaction_study import FAMILIES


def identity(value):
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def note(reply):
    title, text = reply["title"].strip(), reply["note"].strip()
    return (f"# {title}\n\n{text}\n" if title else text + "\n") if text else ""


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.targets = []
        self.anchors = set()

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        self.anchors.add(a.get("id"))
        if tag in ("a", "video", "img", "source"):
            self.targets.extend(a[k] for k in ("href", "src") if k in a)


def check_links(page):
    parser = Links()
    parser.feed(page.read_text())
    for raw in parser.targets:
        url = urlsplit(raw)
        if url.scheme or url.netloc:
            continue
        path = (page.parent / unquote(url.path)).resolve() if url.path else page
        require(path.is_file(), f"broken link in {page}: {raw}")
        if url.fragment and path == page:
            require(unquote(url.fragment) in parser.anchors, f"missing anchor {raw}")
    return len(parser.targets)


def check_freeze_sources(root, plan, freeze):
    if "source_plan_sha256" in freeze:
        require(
            digest(root / "plan.json") == freeze["source_plan_sha256"], "freeze source plan hash"
        )
    if "dev_result_sha256" in freeze:
        policies = read(root / "dev" / "completed.json")["policies"]
        paths = {
            f"dev/{policy}/cases/{case}/result.json" for policy in policies for case in plan["dev"]
        }
        hashes = freeze["dev_result_sha256"]
        require(
            isinstance(hashes, dict) and set(hashes) == paths, "freeze development case coverage"
        )
        for rel in sorted(paths):
            require(digest(root / rel) == hashes[rel], f"freeze development result hash: {rel}")


class Audit:
    def __init__(self, root):
        self.root = root.resolve()
        self.transport = Validator(self.root, False)
        self.receipts = {}
        self.results = []

    def case(self, directory, case, policy, stage, case_id):
        d = directory
        result = read(d / "result.json")
        ident = read(d / "identity.json")
        turns = read(d / "transcript.json")
        audit_ctx = dict(
            task=case["task"],
            your_action=case["action"],
            seconds=case["seconds"],
            heard=case.get("heard", []),
        )
        if "choice_reason" in case:
            audit_ctx["choice_reason"] = case["choice_reason"]
        require(
            result["identity_sha256"] == identity(ident)
            and ident["audit_context"] == audit_ctx
            and ident["audit_image_hashes"] == [digest(i) for i in case["images"]]
            and ident["private_brief"] == case["private_brief"]
            and ident["case_id"] == result["case_id"] == case_id
            and ident["seed_metadata"] == result["seed_metadata"] == stage
            and ident["protocol_version"] == 1
            and ident["model"] == policy.get("model", "gpt-6.2-astra"),
            "case identity",
        )
        require(
            ident["prompts"]
            == {k: policy[k] for k in ("audit", "refine", "decide", "selective", "answer")},
            "policy changed",
        )
        require(set(ident["probes"]) == set(result["probes"]) == set(case["probes"]), "probe set")
        turn_iter = iter(turns)
        observed = set()

        def turn(key, prompt, ctx, images, role, session, persistent=False, shared=False):
            t = next(turn_iter, {})
            require(
                t.get("stage") == key and t.get("actor") == role, f"transcript order/actor: {key}"
            )
            path = (d / (t["source"] if shared else t["receipt"])).resolve()
            if shared:
                require(
                    path == d.parent / "color" / "receipts" / (key + ".json")
                    and t["receipt_sha256"] == digest(path),
                    "shared source",
                )
            else:
                require(path == d / "receipts" / (key + ".json"), "receipt location")
                observed.add(path)
            receipt = read(path)
            req = path.parent.parent / receipt["request"]
            require(
                req.resolve().parent.parent
                == (path.parent.parent / "sessions" / session).resolve(),
                "session location",
            )
            require(
                receipt["session"] == session
                and receipt["input_sha256"]
                == identity([ident["model"], policy[prompt], ctx, [digest(i) for i in images]]),
                "request signature",
            )
            if shared:
                require(
                    self.receipts.get(path) == receipt["reply"], "unverified shared raw response"
                )
            else:
                group = str(req.parent.parent)
                reply = self.transport.raw(
                    req, policy[prompt], ctx, images, group, persistent=persistent
                )
                (only,) = req.parent.glob("attempt-*/result.json")
                require(
                    (d / receipt["result"]).resolve() == only
                    and receipt["reply"] == reply
                    and receipt["thread"] == t["thread"] == self.transport.last[group],
                    "raw receipt discrepancy",
                )
                self.receipts[path] = reply
            require(t["reply"] == receipt["reply"], "transcript reply")
            return receipt["reply"], path

        paired = stage == "challenge" and case_id in ("color", "location")
        donor = paired and case_id == "location"
        require(ident["branch_selective"] == paired, "selective branch design")
        draft, dp = turn(
            "audit", "audit", audit_ctx, case["images"], "robot", "writer", shared=donor
        )
        require(
            Path(result["draft_receipt"]) == dp
            and ident["shared_draft_receipt_sha256"] == (digest(dp) if donor else None),
            "draft donor",
        )
        require(
            result["draft_reply"] == draft
            and result["draft_note"] == (d / "draft.md").read_text() == note(draft),
            "draft note",
        )
        q = draft["question"].strip()
        require(result["audit_question"] == q, "audit question")

        def answer(key, task, q, images):
            return turn(
                key + "-answer",
                "answer",
                dict(task=task, private_brief=case["private_brief"], question=q),
                images,
                "person",
                key + "-person",
            )[0]["answer"]

        spoken = answer("audit", case["task"], q, []) if q else None
        refined = (
            turn(
                "refine",
                "refine",
                dict(draft=note(draft), question=q, person_answer=spoken),
                [],
                "robot",
                "refiner",
            )[0]
            if q
            else None
        )
        memory = note(refined or draft)
        require(
            result["audit_answer"] == spoken
            and result["refined_reply"] == refined
            and result["post_answer_note"] == (d / "post-answer.md").read_text() == memory,
            "note refinement",
        )
        opportunities = {"audit": dict(available=1, asked=int(bool(q)))}
        changes = {"audit": [], "selective": []}
        forced = {}
        for phase in ("transfer", "control"):
            if phase not in case["probes"]:
                opportunities[phase] = dict(available=0, asked=0)
                continue
            p = case["probes"][phase]
            r = result["probes"][phase]
            ctx = dict(task=p["task"], options=p["options"])
            imgs = p["images"]
            gold = p["expected"]
            require(
                ident["probes"][phase]
                == dict(public=ctx, image_hashes=[digest(i) for i in imgs], expected=gold)
                and r["expected"] == gold,
                "gold/public probe",
            )
            acc = []
            for arm, text in (("draft", note(draft)), ("post_answer", memory)):
                public = ctx | {"memory": text}
                sig = identity(
                    [ident["model"], policy["decide"], public, [digest(i) for i in imgs]]
                )
                reused = sig in forced
                if not reused:
                    forced[sig] = turn(
                        phase + "-" + arm, "decide", public, imgs, "fresh robot", "forced-" + sig
                    )
                reply, path = forced[sig]
                require(reply["choice"] in p["options"], "unavailable choice")
                hit = reply["choice"] == gold
                require(
                    r[arm]
                    == dict(
                        reply=reply,
                        correct=hit,
                        input_sha256=sig,
                        reused=reused,
                        receipt=str(path.relative_to(d)),
                    ),
                    "forced probe score",
                )
                acc.append(hit)
            s = r["selective"]
            ctx_note = ctx | {"memory": memory}
            donor_path = d.parent / "color" / "receipts" / (phase + "-selective.json")
            sig = identity(
                [ident["model"], policy["selective"], ctx_note, [digest(i) for i in imgs]]
            )
            same = donor and read(donor_path)["input_sha256"] == sig
            if donor:
                require(
                    ident["shared_selective_receipt_hashes"][phase] == digest(donor_path),
                    "tentative donor hash",
                )
            require(
                s["share_status"]
                == ("identical input" if same else "inputs differ" if donor else "not requested"),
                "tentative sharing",
            )
            tentative, path = turn(
                phase + "-selective",
                "selective",
                ctx_note,
                imgs,
                "robot",
                phase + "-selective",
                True,
                same,
            )
            require(
                s["tentative"] == tentative and Path(s["tentative_receipt"]) == path,
                "tentative reply",
            )
            q = tentative.get("question", "").strip()
            spoken = answer(phase, ctx["task"], q, imgs) if q else None
            final = tentative
            if q:
                final_ctx = (
                    ctx_note | dict(tentative_reply=tentative, question=q, person_answer=spoken)
                    if paired
                    else ctx | dict(question=q, person_answer=spoken)
                )
                final = turn(
                    phase + "-final",
                    "decide",
                    final_ctx,
                    imgs if paired else [],
                    "robot",
                    phase + ("-branch" if paired else "-selective"),
                    not paired,
                )[0]
            require(
                s["final_context"]
                == ("fresh branch" if q and paired else "same thread" if q else "tentative action")
                and s["question"] == q
                and s["answer"] == spoken
                and s["final"] == final,
                "prospective clarification",
            )
            require(
                all(a["choice"] in p["options"] for a in (tentative, final)),
                "unavailable selective choice",
            )
            b, a = tentative["choice"] == gold, final["choice"] == gold
            require(
                s["before_correct"] == b
                and s["after_correct"] == a
                and r["audit_note_change"] == int(acc[1]) - int(acc[0])
                and r["selective_change"] == int(a) - int(b),
                "selective score",
            )
            changes["audit"].append(r["audit_note_change"])
            changes["selective"].append(r["selective_change"])
            opportunities[phase] = dict(available=1, asked=int(bool(q)))
        require(
            result["changes"]
            == {
                k: dict(pairs=len(v), gains=v.count(1), losses=v.count(-1), net=sum(v))
                for k, v in changes.items()
            }
            and opportunities == result["opportunities"],
            "aggregate scores",
        )
        quiet = bool(case.get("quiet"))
        require(
            result["quiet"] == ident["quiet"] == quiet
            and result["quiet_checks"]
            == (
                dict(
                    draft_note_written=bool(note(draft)),
                    asked=bool(draft["question"].strip()),
                    post_answer_note_written=bool(memory),
                )
                if quiet
                else None
            ),
            "silence result",
        )
        require(
            next(turn_iter, None) is None and observed == set((d / "receipts").glob("*.json")),
            "extra transcripts/receipts",
        )
        require(
            set((d / "sessions").rglob("request.json"))
            == {p for p in self.transport.requests if p.is_relative_to(d)},
            "unaccounted model request",
        )
        self.results.append(
            dict(
                stage=stage,
                policy=d.parent.parent.name,
                case=case_id,
                questions=opportunities,
                changes=result["changes"],
            )
        )

    def run(self, core, plan_only):
        root = self.root
        plan = read(root / "plan.json")
        require(
            digest(root / "plan.json")
            == "ef090ac7a0f7ecc9d3957dc9d6b45d0782368c36259363f264eb6a360cfeadf7",
            "prospectively locked plan changed",
        )
        ordered = sorted(
            FAMILIES, key=lambda f: hashlib.sha256(("notes-v1-split/" + f).encode()).hexdigest()
        )
        require(plan["dev"] == ordered[:4] and plan["holdout"] == ordered[4:], "prospective split")
        require(
            plan["inputs"]
            == {
                f: digest(core / "episodes/isolated" / f / "receipts/audit.json") for f in FAMILIES
            },
            "plan inputs",
        )
        folder = root / "locked-trays"
        manifest = read(folder / "private/manifest.json")
        require(
            digest(folder / "private/manifest.json")
            == "dc992358fe972edcc2b6118cfd2ee5e3e1bea713104b1a555dd7c02f7b2e4185",
            "prospective tray lock",
        )
        require(
            manifest["packet_sha256"]
            == {
                str(p.relative_to(folder)): digest(p)
                for p in (folder / "public").rglob("*")
                if p.is_file()
            },
            "stimulus hashes",
        )
        cases = {c: tray_case(folder, c) for c in ("color", "location", "silence")}
        color_case, location_case = cases["color"], cases["location"]
        require(
            all(
                color_case[k] == location_case[k]
                for k in ("task", "action", "seconds", "images", "heard")
            )
            and color_case["private_brief"] != location_case["private_brief"],
            "ambiguous public teaching",
        )
        for phase in ("transfer", "control"):
            a, b = color_case["probes"][phase], location_case["probes"][phase]
            require(
                all(a[k] == b[k] for k in ("task", "options", "images"))
                and (a["expected"] != b["expected"]) == (phase == "transfer"),
                "paired fork/control",
            )
        if plan_only:
            return dict(
                status="plan-verified",
                plan_sha256=digest(root / "plan.json"),
                stimulus_files=len(manifest["packet_sha256"]),
            )
        freeze = read(root / "selection.json")
        check_freeze_sources(root, plan, freeze)
        fixed = {"legacy", freeze["selected"]}
        require(
            len(fixed) == 2
            and all(
                digest(root / "policies" / (k + ".json")) == freeze["policy_sha256"][k]
                for k in fixed
            ),
            "policy freeze",
        )
        for stage, families in (
            ("dev", plan["dev"]),
            ("holdout", plan["holdout"]),
            ("challenge", list(cases)),
        ):
            base = root / stage
            policies = set(read(base / "completed.json")["policies"])
            require(
                policies == {p.name for p in base.iterdir() if p.is_dir()}
                and (fixed <= policies if stage == "dev" else policies == fixed),
                "stage policy completeness",
            )
            for label in sorted(policies):
                dirs = base / label / "cases"
                require(
                    set(families) == {p.name for p in dirs.iterdir() if p.is_dir()},
                    "stage case completeness",
                )
                for f in families:
                    self.case(
                        dirs / f,
                        cases[f] if stage == "challenge" else scene_case(core, f),
                        read(root / "policies" / (label + ".json")),
                        stage,
                        f,
                    )
        links = check_links(root / "index.html")
        md = (root / "analysis.md").read_text()
        for raw in re.findall(r"\[[^\]\n]*\]\(([^)\n]+)\)", md):
            u = urlsplit(raw.strip("<>"))
            if not u.scheme and u.path:
                require((root / unquote(u.path)).is_file(), f"broken Markdown link {raw}")
        return dict(
            status="passed",
            plan_sha256=digest(root / "plan.json"),
            selection_sha256=digest(root / "selection.json"),
            calls=self.transport.calls,
            threads=len(self.transport.threads),
            links=links,
            cases=self.results,
        )


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("core", type=Path)
    p.add_argument("audit", type=Path)
    p.add_argument("--plan-only", action="store_true", help="Read plan and locked stimuli only.")
    a = p.parse_args()
    try:
        print(json.dumps(Audit(a.audit).run(a.core.resolve(), a.plan_only), indent=2))
    except (ValueError, OSError, KeyError, IndexError, TypeError) as exc:
        print(json.dumps(dict(status="failed", error=str(exc))))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
