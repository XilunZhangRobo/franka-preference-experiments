"""Compare note-writing policies on fixed camera evidence and a paired ambiguity."""

import argparse
import hashlib
import json
import random
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from visual_prefs.audit_replay import evaluate_episode
from visual_prefs.interaction_sim import prepare
from visual_prefs.interaction_study import FAMILIES, load, save, sha, snapshot


def scene_case(core, family):
    ep = core / "episodes" / "isolated" / family

    def request(key):
        record = load(ep / "receipts" / f"{key}.json")
        return record, load(core / record["request"])["context"]

    evidence, audit = request("audit")
    decision, _ = request("first-choice")
    case = {
        "task": audit["task"],
        "action": audit["your_action"],
        "choice_reason": decision["reply"]["reason"],
        "seconds": audit["seconds"],
        "heard": audit["heard"],
        "images": [core / i for i in evidence["images"]],
        "probes": {},
    }
    seed = 37 + FAMILIES.index(family) * 11
    case["private_brief"] = prepare(family, "teach", seed).persona("standard")
    for i, (phase, label) in enumerate((("transfer", "transfer"), ("exception", "control")), 1):
        record, req = request(phase + "-cold")
        case["probes"][label] = {
            "task": req["task"],
            "options": req["options"],
            "images": [core / img for img in record["images"]],
            "expected": prepare(family, phase, seed + 103 * i).expected("standard"),
        }
    return case


def lock_plan(out, core):
    order = sorted(
        FAMILIES, key=lambda f: hashlib.sha256(("notes-v1-split/" + f).encode()).hexdigest()
    )
    plan = {
        "dev": order[:4],
        "holdout": order[4:],
        "basis": "Membership is determined by the SHA-256 sort order of notes-v1-split/ plus family. The six were withheld from revision decisions; all ten families were known to the project. The independent tray family is an additional prospective challenge.",
        "sequence": "Finish original study analysis. Compare archived camera evidence under fresh legacy and revised writers on development families. Freeze one candidate before opening holdout or tray results. Run both on the same held-out cases and on two people with identical visible teaching histories. Keep every response.",
        "metrics": "Count optional audit questions over demonstrations, prospective questions over decisions, episodes with any question, visual-only and post-answer transfer and control scores, tentative and final decisions, gains and losses. Report the deliberately ambiguous pairs separately. About one question per five ordinary opportunities is a soft guide. No quota, forced abstentions or forced questions.",
        "inputs": {
            f: sha(core / "episodes" / "isolated" / f / "receipts" / "audit.json") for f in FAMILIES
        },
        "primary_criterion": "A useful revision reduces interruptions while preserving written transfer and scope. Assess whether it asks when a novel scene separates indistinguishable preferences. Small samples give descriptive evidence.",
        "silence": "Include the robot-only rehearsal as one separate negative control. Updating a pre-existing file from an uneventful task remains a future hypothesis.",
    }
    snapshot(out / "plan.json", plan)
    return plan


def tray_case(folder, profile):
    manifest = load(folder / "private" / "manifest.json")
    stage = "silence" if profile == "silence" else "teach"

    def packet(stage):
        base = folder / "public" / stage
        return base, load(base / "packet.json")

    base, clip = packet(stage)
    frames = clip["frames"]
    selected = sorted({round(i * (len(frames) - 1) / 15) for i in range(16)})
    record = manifest["profiles"]["color" if profile == "silence" else profile]
    case = {
        "task": clip["task"],
        "action": "You put the finished piece in the amber tray.",
        "seconds": [frames[i]["t"] for i in selected],
        "heard": clip.get("speech_transcript", []),
        "images": [base / frames[i]["file"] for i in selected],
        "private_brief": record["brief"],
        "probes": {},
        "quiet": profile == "silence",
    }
    if profile != "silence":
        for key, stage in (("transfer", "fork"), ("control", "control")):
            b, probe = packet(stage)
            case["probes"][key] = {
                "task": probe["task"],
                "options": probe["options"],
                "images": [b / probe["frames"][0]["file"]],
                "expected": record["expected"][stage],
            }
    return case


def main():
    par = argparse.ArgumentParser(__doc__)
    par.add_argument("core", type=Path)
    par.add_argument("out", type=Path)
    par.add_argument("stage", choices=("plan", "dev", "holdout", "challenge"))
    par.add_argument("policies", nargs="*")
    par.add_argument("--workers", type=int, default=4)
    args = par.parse_args()
    core, out = args.core.resolve(), args.out.resolve()
    out.mkdir(exist_ok=True, parents=True)
    plan = lock_plan(out, core)
    if args.stage == "plan":
        print(json.dumps({k: plan[k] for k in ("dev", "holdout")}))
        return
    if not (core / "analysis.md").is_file():
        raise ValueError("Begin the note-writing study after the original analysis is available.")
    if not args.policies:
        par.error("Choose at least one policy")
    if args.stage in ("holdout", "challenge"):
        selection = load(out / "selection.json")
        if set(args.policies) != {"legacy", selection["selected"]}:
            raise ValueError("Held-out policy selection differs from the freeze record.")
        for label in args.policies:
            if sha(out / "policies" / (label + ".json")) != selection["policy_sha256"][label]:
                raise ValueError("Frozen prompt changed")

    def evaluate(job):
        label, case_id = job
        policy = load(out / "policies" / (label + ".json"))
        case = (
            scene_case(core, case_id)
            if args.stage != "challenge"
            else tray_case(out / "locked-trays", case_id)
        )
        kwargs = {}
        if args.stage == "challenge" and case_id != "silence":
            kwargs["branch_selective"] = True
            if case_id == "location":
                first = load(out / args.stage / label / "cases" / "color" / "result.json")
                kwargs["shared_draft"] = first["draft_receipt"]
                kwargs["shared_selective"] = {
                    k: p["selective"]["tentative_receipt"] for k, p in first["probes"].items()
                }
        result = evaluate_episode(
            out / args.stage / label, case_id, case, policy, input_seed=args.stage, **kwargs
        )
        print(args.stage, label, case_id, result["opportunities"], flush=True)
        return result

    if args.stage == "challenge":
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            initial_jobs = [
                (label, case_id) for label in args.policies for case_id in ("color", "silence")
            ]
            list(pool.map(evaluate, initial_jobs))
            list(pool.map(evaluate, [(label, "location") for label in args.policies]))
    else:
        jobs = [(label, case_id) for case_id in plan[args.stage] for label in args.policies]
        random.Random("audit-presentation-v1/" + args.stage).shuffle(jobs)
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            list(pool.map(evaluate, jobs))
    save(out / args.stage / "completed.json", {"policies": args.policies})


if __name__ == "__main__":
    main()
