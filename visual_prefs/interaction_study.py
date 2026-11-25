"""Run the paired visual experiment and its longitudinal Astra learner on Virgo."""

import argparse
import hashlib
import json
import os
import random
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .interaction_astra import AstraSession
from .interaction_sim import prepare
from .study import PHASES, asset_hashes, revision

FAMILIES = (
    "paused-work",
    "gift-finishing",
    "receiving-hand",
    "material-order",
    "approach-side",
    "completion-update",
    "vegetable-texture",
    "private-storage",
    "lighting",
    "cleaning-scent",
)
DECIDE = (
    "You control a household robot. Choose one available action to perform now. "
    "Use the current task, camera and any personal knowledge supplied. "
    'Return {"choice":"<letter>","reason":"one short sentence"}.'
)
DECIDE_ASK = (
    DECIDE + " Before acting you may ask the person a focused question if its answer "
    'could change your choice. Include "question" (empty string to act immediately). '
    "Even when asking, record your tentative choice."
)
PERSON = (
    "Play the person in your private brief. Observe the result of the robot action. "
    'Select one physical response to enact. Return {"response":"<letter>"}. '
    "Your choice is sent privately to the simulator. The robot sees only your resulting motion."
)
AUDIT = (
    "You are the household robot viewing the interaction from your camera. Consider what happened, "
    "why the person might have acted, and what could be useful in a different task. "
    "Distinguish what you saw from an inference. Decide whether the observed behavior merits "
    "a personal note. Ask at most one focused question if the evidence leaves an important "
    "scope ambiguity. Return JSON with short string fields observation, interpretation, title, "
    "note and question. Use empty strings for an unwarranted note or question."
)
ANSWER = (
    "Reply as this person to the robot question in one short sentence. Answer only what was "
    "asked, using the private brief. If the brief does not specify, say so. "
    'Return {"answer":"your spoken reply"}.'
)
REFINE = (
    "Update your written preference note based on the exchange. Preserve uncertainty where "
    'appropriate. Return {"title":"a short searchable title","note":"a short reusable rule '
    'with relevant evidence and limits"}.'
)
RUNTIME = [
    "uv",
    "run",
    "--no-project",
    "--python",
    "3.11",
    "--with",
    "bpy==4.3.0",
    "--with",
    "numpy<2",
    "--with",
    "mujoco==4.0.1",
    "--with",
    "pillow",
    "--with",
    "imageio-ffmpeg",
    "python",
    "-m",
    "visual_prefs.interaction_media",
]
REPO = Path(__file__).resolve().parents[1]


def load(path):
    return json.loads(path.read_text())


def save(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".part")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n")
    tmp.replace(path)


def snapshot(path, obj):
    if path.exists() and load(path) != obj:
        raise ValueError(f"Stored experiment differs at {path}")
    if not path.exists():
        save(path, obj)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Study:
    def __init__(self, root, workers):
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.workers = workers
        self.renders = threading.Semaphore(workers)

    def rel(self, path):
        return str(path.relative_to(self.root))

    def media(self, family, phase, choice="initial", response="none", *, retained=False):
        seed = (
            37 + FAMILIES.index(family) * 11 + PHASES.index(phase) * 103 + (1701 if retained else 0)
        )
        folder = self.root / "media" / family / f"{phase}-{seed}" / f"{choice}-{response}"
        if not folder.exists():
            with self.renders:
                folder.parent.mkdir(parents=True, exist_ok=True)
                with folder.with_suffix(".log").open("a") as log:
                    subprocess.run(
                        RUNTIME
                        + [
                            str(folder),
                            family,
                            phase,
                            str(seed),
                            choice,
                            response,
                            "640",
                            "480",
                            "6",
                            "12",
                        ],
                        cwd=REPO,
                        env=os.environ | {"MUJOCO_GL": "egl", "OPENBLAS_NUM_THREADS": "1"},
                        stdout=log,
                        stderr=subprocess.STDOUT,
                        check=True,
                    )
        return prepare(family, phase, seed), folder / "view"

    def initial(self, family, phase, *, retained=False):
        trial, view = self.media(family, phase, retained=retained)
        return trial, view / load(view / "packet.json")["frames"][0]["file"]


def sample(view, count=12):
    packet = load(view / "packet.json")
    frames = packet["frames"]
    indices = {round(i * (len(frames) - 1) / max(1, count - 1)) for i in range(count)}
    indices.update(
        i
        for i, f in enumerate(frames)
        if any(abs(e["t"] - f["t"]) < 0.001 for e in packet["speech_transcript"])
    )
    picked = [frames[i] for i in sorted(indices)]
    return {"seconds": [f["t"] for f in picked], "heard": packet["speech_transcript"]}, [
        view / f["file"] for f in picked
    ]


def note_text(reply):
    text = reply["note"].strip()
    return f"# {reply['title'].strip()}\n\n{text}\n" if text else ""


class Episode:
    def __init__(self, study, mode, family):
        self.s, self.mode, self.family = study, mode, family
        self.path = study.root / "episodes" / mode / family
        self.path.mkdir(parents=True, exist_ok=True)
        sessions = (
            study.root / "sessions" / ("continuous" if mode == "continuous" else f"{mode}/{family}")
        )
        self.robot = AstraSession(sessions / "robot", persistent=True)
        self.person = AstraSession(sessions / "person", persistent=True)
        self.turns = []
        self.calls = {}
        self.scores = {}

    def ask(self, key, session, prompt, context, images=()):
        p = self.path / "receipts" / f"{key}.json"
        digest = hashlib.sha256(
            json.dumps([prompt, context, [sha(i) for i in images]], sort_keys=True).encode()
        ).hexdigest()
        if p.exists():
            data = load(p)
            if data["input_sha256"] != digest:
                raise ValueError(f"Cannot resume changed turn {p}")
        else:
            # A terminated orchestrator can leave a successful adapter call just
            # before its episode receipt. Bind that exact reply instead of asking twice.
            matching = []
            used = {load(self.s.root / link)["request"] for link in self.calls.values()}
            for request in session.log_dir.glob("*/request.json"):
                archived = load(request)
                if (
                    self.s.rel(request) in used
                    or archived["instruction"] != prompt
                    or archived["context"] != context
                    or [i["sha256"] for i in archived["images"]] != [sha(i) for i in images]
                ):
                    continue
                for result in sorted(request.parent.glob("attempt-*/result.json")):
                    matching.append((request, load(result)))
            if len(matching) > 1:
                raise ValueError(f"Ambiguous previous response for {p}")
            if matching:
                request, result = matching[0]
                reply, thread = result["reply"], result["thread_id"]
            else:
                reply = session.ask(prompt, context, images)
                actual = sorted(d for d in session.log_dir.iterdir() if d.is_dir())[-1]
                request, thread = actual / "request.json", session.session_id
            data = dict(
                input_sha256=digest,
                thread=thread,
                request=self.s.rel(request),
                reply=reply,
                images=[self.s.rel(i) for i in images],
            )
            save(p, data)
        self.calls[key] = self.s.rel(p)
        return data["reply"]

    def say(self, role, channel, text, **kwargs):
        self.turns.append(dict(role=role, channel=channel, text=text, **kwargs))

    def answer(self, key, question, trial, image=None):
        self.say("Robot Astra", "question to person", question)
        ctx = {
            "question": question,
            "task": trial.case.command,
            "private_brief": trial.persona(self.profile),
        }
        reply = self.ask(key + "-answer", self.person, ANSWER, ctx, [image] if image else [])[
            "answer"
        ]
        self.say("Person Astra", "spoken answer to robot", reply)
        return reply

    def run(self):
        done = self.path / "episode.json"
        if done.exists():
            return load(done)
        f = self.family
        trial, image = self.s.initial(f, "teach")
        library_dir = self.s.root / "library"
        before = self.path / "library-before.json"
        if not before.exists():
            save(
                before,
                {p.stem: p.read_text() for p in sorted(library_dir.glob("*.md"))}
                if self.mode == "continuous"
                else {},
            )
        prior = load(before)
        ctx = {"task": trial.case.command, "options": trial.options, "written_library": prior}
        cold = self.ask("first-choice", self.robot, DECIDE, ctx, [image])
        letter = cold["choice"]
        if letter not in trial.options:
            raise ValueError(cold)
        self.profile = (
            "reverse"
            if self.mode == "contrast" and letter == trial.expected("standard")
            else "standard"
        )
        self.scores["teaching_miss"] = letter != trial.expected(self.profile)
        self.say("Person", "task command", trial.case.command, image=self.s.rel(image))
        self.say("Robot Astra", "selected action", trial.options[letter] + " " + cold["reason"])
        _, action = self.s.media(f, "teach", letter)
        observed, frames = sample(action, 6)
        self.say(
            "Simulator",
            "visual evidence to person",
            "Camera sequence after the robot chose its action.",
            clip=self.s.rel(action / "view.mp4"),
        )
        menu = list(trial.person_menu(letter).items())
        random.Random(f"person-choice/{f}").shuffle(menu)
        moves = {chr(65 + i): k for i, (k, v) in enumerate(menu)}
        public = {chr(65 + i): v for i, (k, v) in enumerate(menu)}
        response = self.ask(
            "person-response",
            self.person,
            PERSON,
            {
                "private_brief": trial.persona(self.profile),
                "task": trial.case.command,
                "observed_robot_action": trial.options[letter],
                "motion_options": public,
                **observed,
            },
            frames,
        )
        move = moves[response["response"]]
        self.scores["feedback_matches_persona"] = move == trial.expected_response(
            self.profile, letter
        )
        self.say(
            "Person Astra", "private motion command to simulator", public[response["response"]]
        )
        _, interaction = self.s.media(f, "teach", letter, move)
        observed, frames = sample(interaction, 16)
        self.say(
            "Simulator",
            "visual feedback to robot",
            "Robot camera playback. Sample times in seconds: "
            + ", ".join(map(str, observed["seconds"])),
            clip=self.s.rel(interaction / "view.mp4"),
        )
        if observed["heard"]:
            for event in observed["heard"]:
                self.say(event["speaker"], "simulated utterance", event["text"], time=event["t"])
        audit = self.ask(
            "audit",
            self.robot,
            AUDIT,
            {"task": trial.case.command, "your_action": trial.options[letter], **observed},
            frames,
        )
        self.say(
            "Robot Astra",
            "private visual audit",
            audit["observation"] + " " + audit["interpretation"],
        )
        raw_note = note_text(audit)
        (self.path / "visual-only.md").write_text(raw_note)
        final_note = raw_note
        if audit.get("question", "").strip():
            answer = self.answer("audit", audit["question"], trial)
            update = self.ask(
                "updated-note",
                self.robot,
                REFINE,
                {"draft": raw_note, "question": audit["question"], "person_answer": answer},
            )
            final_note = note_text(update)
        (self.path / "memory.md").write_text(final_note)
        self.say(
            "Robot Astra", "writes personal note", final_note or "(No preference note written.)"
        )
        latest = final_note
        for phase in ("transfer", "exception"):
            next_trial, first = self.s.initial(f, phase)
            held = {"task": next_trial.case.command, "options": next_trial.options}
            self.say(
                "Person",
                "new task" if phase == "transfer" else "scope control",
                next_trial.case.command,
                image=self.s.rel(first),
            )
            expected = next_trial.expected(self.profile)
            prefix = "control" if phase == "exception" else phase
            for condition, note in (("cold", ""), ("note", final_note)):
                session = AstraSession(self.path / "independent" / f"{phase}-{condition}")
                result = self.ask(
                    f"{phase}-{condition}", session, DECIDE, held | {"memory": note}, [first]
                )
                if result["choice"] not in next_trial.options:
                    raise ValueError(result)
                self.scores[f"{prefix}_{condition}"] = result["choice"] == expected
                self.say(
                    "Fresh Astra",
                    condition + " comparison",
                    next_trial.options[result["choice"]] + " " + result["reason"],
                )
            reply = self.ask(
                phase + "-learner",
                self.robot,
                DECIDE_ASK,
                held | {"current_note": latest, "previous_notes": prior},
                [first],
            )
            selected = reply["choice"]
            if selected not in next_trial.options:
                raise ValueError(reply)
            self.scores[prefix + "_before_question"] = selected == expected
            if reply.get("question", "").strip():
                answer = self.answer(phase, reply["question"], next_trial, first)
                reply = self.ask(
                    phase + "-act",
                    self.robot,
                    DECIDE,
                    held | {"question": reply["question"], "person_answer": answer},
                )
                selected = reply["choice"]
                refined = self.ask(
                    phase + "-refine",
                    self.robot,
                    REFINE,
                    {"current_note": latest, "person_answer": answer},
                )
                latest = note_text(refined)
                self.say("Robot Astra", "refines personal note", latest)
            self.scores[prefix + "_learner"] = selected == expected
            _, actual = self.s.media(f, phase, selected)
            self.say(
                "Robot Astra",
                "executed probe action",
                next_trial.options[selected] + " " + reply["reason"],
                clip=self.s.rel(actual / "view.mp4"),
            )
        (self.path / "final-note.md").write_text(latest)
        if self.mode == "continuous":
            library_dir.mkdir(exist_ok=True)
            if latest.strip():
                (library_dir / f"{FAMILIES.index(f) + 1:02}.md").write_text(latest)
            save(
                self.path / "library-after.json",
                {p.name: sha(p) for p in sorted(library_dir.glob("*.md"))},
            )
        save(self.path / "calls.json", self.calls)
        save(self.path / "transcript.json", self.turns)
        ep = dict(
            mode=self.mode,
            scenario=f,
            title=f.replace("-", " ").title(),
            profile=self.profile,
            turns=self.turns,
            scores=self.scores,
            transcript=self.s.rel(self.path / "transcript.json"),
            robot_thread=self.robot.session_id,
            person_thread=self.person.session_id,
            artifacts={
                k: self.s.rel(self.path / v)
                for k, v in {
                    "Exact calls and model inputs": "calls.json",
                    "Visual-only draft": "visual-only.md",
                    "Note at first probe": "memory.md",
                    "Final note": "final-note.md",
                }.items()
            },
        )
        save(done, ep)
        print(f"Completed {self.mode} {f}: {self.scores}", flush=True)
        return ep


def main():
    p = argparse.ArgumentParser(__doc__)
    p.add_argument("root", type=Path)
    p.add_argument("--workers", type=int, default=3)
    args = p.parse_args()
    s = Study(args.root, args.workers)
    plan = dict(
        families=FAMILIES,
        model="gpt-6.2-astra",
        phase_order=list(PHASES),
        design="All original preferences run first. If a first action already matches the original person, add a separate diagnostic episode whose prewritten profile disagrees with its observed first action. Contrasts measure response to a correction conditional on a miss. Continuous uses only the ten original preferences in the listed order.",
        seeds="37+11*family_index+103*phase_index; retention adds 1701",
        size=[640, 480],
        fps=6,
        samples=12,
        renderer="Blender Cycles",
        clarification="At most one question during audit and one per probe. Fresh cold and written-note comparisons cannot ask. The same persistent learner and person continue across the ten continuous episodes.",
        outcome="All errors and null notes count. A successful scope choice can also reflect ordinary priors. A single development run per family estimates no population frequency.",
    )
    snapshot(s.root / "plan.json", json.loads(json.dumps(plan)))
    if not (s.root / "provenance.json").exists():
        save(
            s.root / "provenance.json",
            dict(
                revision=revision(),
                assets=asset_hashes(),
                source={
                    file.name: sha(file) for file in sorted((REPO / "visual_prefs").glob("*.py"))
                },
            ),
        )

    def run(mode, f):
        return Episode(s, mode, f).run()

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        original = list(pool.map(lambda f: run("isolated", f), FAMILIES))
        contrasts = list(
            pool.map(
                lambda f: run("contrast", f),
                [e["scenario"] for e in original if not e["scores"]["teaching_miss"]],
            )
        )
    chain = [run("continuous", f) for f in FAMILIES]
    from .interaction_retention import run_retention

    html, results = run_retention(
        s.root, FAMILIES, lambda f, p: s.initial(f, p, retained=True), readers=args.workers
    )
    save(
        s.root / "report_manifest.json",
        dict(
            episodes=original + contrasts + chain,
            artifacts={
                "Study design": "plan.json",
                "Software and assets": "provenance.json",
                "Final library on fresh layouts": str(html),
                "Retention scores": str(results),
            },
        ),
    )
    subprocess.run(
        [os.sys.executable, str(REPO / "tools" / "interaction_report.py"), str(s.root)], check=True
    )


if __name__ == "__main__":
    main()
