"""Supplemental paired, held-out mug handoffs using the original isolated note."""

# ruff: noqa: E402
import argparse
import hashlib
import html
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from random import Random

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from visual_prefs.episode import Motion
from visual_prefs.handover import _object, receiving_hand
from visual_prefs.interaction_astra import AstraSession
from visual_prefs.interaction_sim import Trial
from visual_prefs.interaction_study import DECIDE, RUNTIME, save
from visual_prefs.scene import Scene
from visual_prefs.study import new_directory, public_choices

SEED = 3931
CONDITIONS = ("both-free", "left-occupied")
ARMS = ("empty", "original-note")
CAMERA = dict(
    size=(640, 480), fps=6, renderer="blender-cycles", samples=12, camera="agent", device="CPU"
)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(condition):
    phase = "transfer" if condition == "both-free" else "exception"
    scene = Scene("kitchen")
    case = receiving_hand(scene, phase, SEED)
    scene.world.remove(scene.props.pop("remote"))
    scene.grasps.pop("remote", None)
    rng = Random(SEED)
    origin = (rng.uniform(0.090, 0.120), rng.uniform(-0.120, -0.088), scene.table_z)
    _object(scene, "tumbler", origin)
    mug = scene.props["tumbler"]
    scene.cyl(mug, (0, 0, 0.099), 0.035, 0.009, "#e9d9bf")
    scene.cyl(mug, (0, 0, 0.105), 0.029, 0.005, "#d9ccb5")
    scene.box(mug, (0, -0.016, 0.109), (0.021, 0.010, 0.004), "#403b37")
    actions = {}
    for side, sequence in case.robot.items():
        offer = replace(sequence[0], item="tumbler")
        x, y, z = offer.target
        actor = "human-left" if side == "left" else "human"
        actions[side] = [offer]
        if side == "right" or condition == "both-free":
            actions[side].append(Motion(actor, "tumbler", (x, y + 0.025, z + 0.014), "hold"))
    case = replace(case, command="Pass me my lidded drinking mug.", robot=actions)
    # Keep option letters and mug position matched in the two contexts.
    return Trial("receiving-hand", phase, scene, case, public_choices(case, SEED, "transfer"))


def render(folder, condition, choice):
    trial = build(condition)
    with new_directory(folder) as stage:
        if choice == "initial":
            cap, trace = trial.initial(stage / "view", **CAMERA)
        else:
            cap, trace = trial.execute(stage / "view", choice, **CAMERA)
        save(stage / "view" / "packet.json", cap)
        save(stage / "measurement.json", trace)
        save(stage / "render.json", dict(condition=condition, choice=choice, seed=SEED, **CAMERA))


def render_process(folder, condition, choice):
    if folder.exists():
        return
    folder.parent.mkdir(parents=True, exist_ok=True)
    with folder.with_suffix(".log").open("a") as log:
        cmd = RUNTIME[: RUNTIME.index("-m")] + [
            str(Path(__file__).resolve()),
            str(folder),
            "--render",
            condition,
            choice,
        ]
        subprocess.run(cmd, cwd=REPO, stdout=log, stderr=subprocess.STDOUT, check=True)


def run(root):
    out = root / "mug-handoff"
    out.mkdir(exist_ok=True)
    note_path = root / "episodes/isolated/receiving-hand/memory.md"
    note = note_path.read_text()
    plan = dict(
        label="Supplemental held-out mug handoff",
        conditions=CONDITIONS,
        arms=ARMS,
        task="Pass me my lidded drinking mug.",
        renderer=CAMERA,
        seed=SEED,
        original_note="../episodes/isolated/receiving-hand/memory.md",
        original_note_sha256=sha(note_path),
        expected={"both-free": "left", "left-occupied": "right"},
        design="Four fresh independent Astra decisions; each pair sees identical camera bytes and option ordering. A free hand can receive the mug; an occupied hand leaves the robot holding its offer. Both conditions share a kitchen layout and starting mug position. No teaching or clarification.",
    )
    plan_path = out / "plan.json"
    if plan_path.exists():
        if json.loads(plan_path.read_text()) != json.loads(json.dumps(plan)):
            raise ValueError("Cannot resume with a changed study or note")
    else:
        save(plan_path, plan)

    def pair(condition):
        base = out / condition
        render_process(base / "initial", condition, "initial")
        image = base / "initial/view/frame-00000.jpg"
        t = build(condition)
        rows = []
        for arm in ARMS:
            folder = base / arm
            checkpoint = folder / "choice.json"
            folder.mkdir(exist_ok=True)
            ctx = dict(
                task=t.case.command,
                options=t.options,
                memory=note if arm == "original-note" else "",
            )
            if checkpoint.exists():
                record = json.loads(checkpoint.read_text())
                if ctx != record["context"] or sha(image) != record["image_sha256"]:
                    raise ValueError("Cannot resume a changed mug observation")
            else:
                if list((folder / "session").glob("*/request.json")):
                    raise ValueError(
                        "Archived model turn already exists without a choice checkpoint"
                    )
                session = AstraSession(folder / "session", persistent=False, retries=0)
                reply = session.ask(DECIDE, ctx, [image])
                record = dict(
                    instruction=DECIDE,
                    context=ctx,
                    reply=reply,
                    thread_id=session.session_id,
                    image_sha256=sha(image),
                )
                save(checkpoint, record)
            choice = record["reply"]["choice"]
            if choice not in t.choices:
                raise ValueError(f"Invalid mug choice {choice}")
            side = t.choices[choice]
            dest = folder / "execution"
            rows.append(
                dict(
                    condition=condition,
                    arm=arm,
                    choice=choice,
                    hand=side,
                    expected=plan["expected"][condition],
                    correct=side == plan["expected"][condition],
                    transcript=str(checkpoint.relative_to(out)),
                    clip=str((dest / "view/view.mp4").relative_to(out)),
                    image=str(image.relative_to(out)),
                    session=record["thread_id"],
                    reason=record["reply"]["reason"],
                )
            )
        for row in rows:
            render_process(base / row["arm"] / "execution", condition, row["choice"])
            row["clip_sha256"] = sha(out / row["clip"])
            row["frames"] = len(
                json.loads((base / row["arm"] / "execution" / "measurement.json").read_text())[
                    "events"
                ]
            )
        return rows

    with ThreadPoolExecutor(max_workers=2) as pool:
        rows = [row for group in pool.map(pair, CONDITIONS) for row in group]
    if len({r["session"] for r in rows}) != 4:
        raise ValueError("Four distinct model sessions required")
    for condition in CONDITIONS:
        pair_rows = [r for r in rows if r["condition"] == condition]
        if (
            len(
                {json.loads((out / r["transcript"]).read_text())["image_sha256"] for r in pair_rows}
            )
            != 1
        ):
            raise ValueError("Unmatched within-condition observations")
    save(out / "results.json", rows)
    esc = html.escape
    parts = [
        '<!doctype html><html lang="en"><meta charset="utf-8"><title>Supplemental mug handoffs</title><style>body{max-width:64rem;margin:2rem auto;font:17px/1.5 system-ui}video{max-width:100%;width:35rem}article{border-top:1px solid #ccc}pre{white-space:pre-wrap}</style><main><h1>Supplemental mug handoffs</h1>',
        "<p>Four fresh held-out decisions used the same lidded drinking mug. Within each context both readers saw the same image. The note reader received the original isolated flashlight-handoff note. A robot offering to an occupied hand waits with the mug. Each selected action was rendered separately.</p>",
        '<p><a href="plan.json">Run plan</a> · <a href="results.json">Scores</a> · <a href="../episodes/isolated/receiving-hand/memory.md">Original memory</a></p>',
    ]
    for r in rows:
        section = out / r["condition"] / r["arm"]
        requests = list((section / "session").glob("*/request.json"))
        if len(requests) != 1:
            raise ValueError("Exactly one model call expected per mug arm")
        path = requests[0]
        source = path.relative_to(out)
        raw = (path.parent / "attempt-1/events.jsonl").relative_to(out)
        parts.append(
            f'<article><h2>{esc(r["condition"])} · {esc(r["arm"])}</h2><p>Offered to the {r["hand"]} hand. Expected {r["expected"]}. {"Correct" if r["correct"] else "Incorrect"}.</p><p>{esc(r["reason"])}</p><video preload="none" controls src="{r["clip"]}"></video><p><a href="{r["image"]}">Initial camera</a> · <a href="{r["transcript"]}">Decision transcript</a> · <a href="{source}">Exact request</a> · <a href="{raw}">Raw response events</a></p></article>'
        )
    (out / "index.html").write_text("\n".join(parts) + "</main></html>\n")
    print(json.dumps(rows, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--render", nargs=2)
    args = parser.parse_args()
    if args.render:
        render(args.root, *args.render)
    else:
        run(args.root.resolve())
