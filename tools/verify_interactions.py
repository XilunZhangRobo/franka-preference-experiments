"""Independently replay the scoring and audit the recorded experiment (read only)."""

import argparse
import base64
import hashlib
import json
import random
import re
import subprocess
import sys
from pathlib import Path

import imageio_ffmpeg

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from visual_prefs import interaction_retention as retention
from visual_prefs import interaction_study as study
from visual_prefs.interaction_sim import prepare


def read(path):
    return json.loads(path.read_text())


def sha(data):
    return hashlib.sha256(data).hexdigest()


def digest(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def require(ok, message):
    if not ok:
        raise ValueError(message)


class Validator:
    def __init__(self, root, videos):
        self.root = root.resolve()
        policy = read(self.root / "plan.json").get("note_policy")
        self.prompts = study.LEGACY_PROMPTS
        if policy is not None:
            require(bool(re.fullmatch(r"[0-9a-f]{64}", policy["sha256"])), "note policy digest")
            require(
                set(policy["prompts"]) == set(self.prompts)
                and all(isinstance(p, str) and p.strip() for p in policy["prompts"].values()),
                "note policy prompts",
            )
            self.prompts = policy["prompts"]
        self.videos = videos
        self.threads = {}
        self.last = {}
        self.calls = 0
        self.media = {}
        self.episodes = []
        self.library = {}
        self.retained = []
        self.requests = set()
        self.retries = []
        self.recoveries = []
        self.films = {}
        self.trials = {}

    def path(self, raw):
        p = (self.root / raw).resolve()
        require(p.is_relative_to(self.root), f"path escapes run: {raw}")
        return p

    def rel(self, p):
        return str(p.relative_to(self.root))

    def recovery(self, attempt, request):
        evidence = read(attempt / "recovery.json")
        call = attempt.parent
        original = call / evidence["original_attempt"]
        thread = evidence["thread_id"]
        require(
            original.parent == call
            and re.fullmatch(r"attempt-\d+", original.name)
            and original != attempt,
            "recovery original attempt",
        )
        original_events = [
            json.loads(line) for line in (original / "events.jsonl").read_text().splitlines()
        ]
        require(
            [e["thread_id"] for e in original_events if e["type"] == "thread.started"] == [thread]
            and all(e["type"] != "turn.completed" for e in original_events),
            "original interruption",
        )
        hashes = [r["sha256"] for r in request["images"]]
        raw_prompt = (call / "prompt.txt").read_text()
        require(
            evidence["original_prompt_sha256"] == sha(raw_prompt.encode())
            and evidence["original_image_hashes"] == hashes,
            "original recovery request",
        )
        journal = attempt / "journal-evidence.jsonl"
        require(digest(journal) == evidence["journal_evidence_sha256"], "recovery journal digest")
        turns = []
        for line in journal.read_text().splitlines():
            record = json.loads(line)
            payload = record["payload"]
            typ = payload["type"]
            if record["type"] == "event_msg" and typ == "task_started":
                turns.append(dict(id=payload["turn_id"], users=[], answers=[]))
            elif (
                record["type"] == "response_item" and typ == "message" and payload["role"] == "user"
            ):
                turns[-1]["users"].append(payload["content"])
            elif (
                record["type"] == "response_item"
                and typ == "message"
                and payload["role"] == "assistant"
                and payload["phase"] == "final_answer"
            ):
                turns[-1]["answers"].append(
                    "".join(c["text"] for c in payload["content"] if c["type"] == "output_text")
                )
            elif record["type"] == "event_msg" and typ == "task_complete":
                if payload.get("last_agent_message"):
                    turns[-1]["answers"].append(payload["last_agent_message"])
            else:
                raise ValueError("unexpected event in recovery journal")
        require(
            turns
            and [t["id"] for t in turns] == evidence["journal_turn_ids"]
            and turns[0]["id"] == evidence["original_turn_id"],
            "recovery turn identity",
        )
        continuation = "Please finish the preceding unanswered request using the information already supplied. Return its requested JSON object."
        for index, turn in enumerate(turns):
            require(len(turn["users"]) == 1, "recovery user messages")
            content = turn["users"][0]
            expected = request["images"] if index == 0 else []
            require(len(content) == len(expected) * 3 + 1, "unexpected journal content count")
            require(
                content[-1]
                == dict(type="input_text", text=raw_prompt if index == 0 else continuation),
                "journal prompt",
            )
            for j, image in enumerate(expected):
                opening, upload, closing = content[j * 3 : j * 3 + 3]
                require(
                    opening
                    == dict(
                        type="input_text",
                        text=f'<image name=[Image #{j + 1}] path="{image["file"]}">',
                    )
                    and closing == dict(type="input_text", text="</image>")
                    and upload["type"] == "input_image",
                    "journal image framing",
                )
                require(
                    sha(base64.b64decode(upload["image_url"].split(",", 1)[1], validate=True))
                    == image["sha256"],
                    "journal image bytes",
                )
        original_argv = read(original / "argv.json")
        require(
            request["previous_thread_id"] == thread and evidence["continuation_images"] == [],
            "recovery thread/image policy",
        )
        prior_args = [
            arg
            for i, arg in enumerate(original_argv)
            if arg != "-i" and (i == 0 or original_argv[i - 1] != "-i")
        ]
        mode = evidence["mode"]
        if mode == "same-thread-continuation":
            require(
                not any(t["answers"] for t in turns)
                and evidence["continuation_prompt"] == continuation
                and read(attempt / "argv.json") == prior_args
                and prior_args[-3:] == ["resume", thread, "-"],
                "text-only recovery invocation",
            )
        elif mode == "journal-final":
            require(
                evidence["continuation_prompt"] is None
                and not (attempt / "argv.json").exists()
                and turns[-1]["answers"]
                and all(a == (attempt / "reply.txt").read_text() for a in turns[-1]["answers"]),
                "recovered journal final",
            )
        else:
            raise ValueError(f"unrecognized transport recovery {mode}")
        self.recoveries.append(
            dict(
                request=self.rel(call / "request.json"),
                mode=mode,
                original_attempt=self.rel(original),
                successful_attempt=self.rel(attempt),
                thread=thread,
                original_image_count=len(hashes),
                original_turn=turns[0]["id"],
                continuation_images=0,
                journal_sha256=digest(journal),
            )
        )
        return original_argv

    def raw(
        self, request_path, instruction, context, images, group, receipt=None, persistent=False
    ):
        call = request_path.parent
        req = read(request_path)
        require(req["model"] == "gpt-6.2-astra", "model")
        require(
            req["instruction"] == instruction and req["context"] == context,
            f"unexpected prompt or context in {call}",
        )
        require(req["persistent"] is persistent, "wrong persistence mode")
        prefix = "Use only the supplied images, conversation, and text. Do not use tools. Reply only with the requested JSON object.\n"
        require(
            (call / "prompt.txt").read_text()
            == prefix + instruction + "\n" + json.dumps(context, ensure_ascii=False),
            "serialized prompt differs",
        )
        records = req["images"]
        require(len(records) == len(images), "attached image count differs")
        names = []
        for i, (entry, source) in enumerate(zip(records, images)):
            name = entry["file"]
            require(re.fullmatch(f"image-{i:03d}\\.(jpg|png)", name), "nonopaque attachment name")
            copy = self.path(call / name)
            require(
                digest(copy) == entry["sha256"] == digest(source),
                f"attachment hash differs: {source}",
            )
            names.append(name)
        successes = sorted(call.glob("attempt-*/result.json"))
        require(len(successes) == 1, "expected one successful attempt")
        result = read(successes[0])
        attempt = successes[0].parent
        argv = (
            self.recovery(attempt, req)
            if (attempt / "recovery.json").exists()
            else read(attempt / "argv.json")
        )
        require(
            [argv[i + 1] for i, arg in enumerate(argv) if arg == "-i"] == names,
            "CLI attachment order",
        )
        require(
            argv[-1] == "-" and argv[argv.index("-m") + 1] == req["model"],
            "CLI model or prompt input",
        )
        require(
            argv[argv.index("-s") + 1] == "read-only" and "--ignore-user-config" in argv,
            "CLI isolation",
        )
        require(
            all(
                flag in argv and argv[argv.index(flag) - 1] == "--disable"
                for flag in (
                    "shell_tool",
                    "unified_exec",
                    "view_image",
                    "plugins",
                    "multi_agent",
                    "memories",
                )
            ),
            "tools enabled",
        )
        events = [json.loads(line) for line in (attempt / "events.jsonl").read_text().splitlines()]
        ids = [e["thread_id"] for e in events if e["type"] == "thread.started"]
        require(
            ids == [result["thread_id"]] and any(e["type"] == "turn.completed" for e in events),
            "raw thread/completion",
        )
        for e in events:
            if "item" in e:
                require(e["item"]["type"] in ("agent_message", "reasoning", "error"), "tools used")
        messages = [
            e["item"]["text"]
            for e in events
            if e["type"] == "item.completed" and e["item"]["type"] == "agent_message"
        ]
        require(
            messages and messages[-1] == (attempt / "reply.txt").read_text(), "raw message differs"
        )
        reply = json.loads(messages[-1].strip().removeprefix("```json").removesuffix("```").strip())
        require(reply == result["reply"], "parsed raw response differs")
        tid = ids[0]
        previous = self.last.get(group)
        require(req["previous_thread_id"] == previous, f"broken conversation chain {group}")
        if previous:
            require(
                tid == previous and "resume" in argv and argv[argv.index("resume") + 1] == previous,
                "wrong resume",
            )
        else:
            require(
                "resume" not in argv and ("--ephemeral" in argv) == (not persistent),
                "wrong fresh session",
            )
            require(tid not in self.threads, f"reused fresh identity {group}")
        self.threads[tid] = group
        self.last[group] = tid
        if receipt is not None:
            require(
                receipt["reply"] == reply and receipt["thread"] == tid, "receipt result differs"
            )
            payload = [instruction, context, [record["sha256"] for record in records]]
            require(
                receipt["input_sha256"] == sha(json.dumps(payload, sort_keys=True).encode()),
                "receipt input digest",
            )
            require(
                receipt["images"] == [self.rel(p) for p in images], "receipt image source differs"
            )
        require(request_path not in self.requests, "a raw turn was used twice")
        self.requests.add(request_path)
        self.retries.extend(self.rel(p) for p in sorted(call.glob("attempt-*/error.json")))
        self.calls += 1
        return reply

    def video(self, path, decode):
        args = [
            imageio_ffmpeg.get_ffmpeg_exe(),
            "-v",
            "error",
            "-nostdin",
            "-xerror",
            "-i",
            str(path),
            "-map",
            "0:v:0",
        ]
        if not decode:
            args.extend(["-c:v", "copy"])
        cmd = subprocess.run(
            args + ["-f", "null", "-", "-progress", "pipe:1"],
            capture_output=True,
            text=True,
            check=True,
        )
        counts = re.findall(r"^frame=(\d+)$", cmd.stdout, re.M)
        require(counts and int(counts[-1]) > 0, f"empty video {path}")
        return dict(sha256=digest(path), frames=int(counts[-1]))

    def view(self, family, phase, letter="initial", response="none", retained=False):
        seed = (
            37
            + 11 * study.FAMILIES.index(family)
            + 103 * study.PHASES.index(phase)
            + 1701 * retained
        )
        key = (family, phase, seed)
        if key not in self.trials:
            if len(self.trials) >= 3:
                self.trials.pop(next(iter(self.trials)))
            self.trials[key] = prepare(*key)
        trial = self.trials[key]
        folder = self.root / "media" / family / f"{phase}-{seed}" / f"{letter}-{response}"
        packet = read(folder / "view" / "packet.json")
        config = read(folder / "render.json")
        require(
            (
                config["family"],
                config["phase"],
                config["seed"],
                config["choice"],
                config["response"],
            )
            == (*key, letter, response),
            "wrong render",
        )
        require(
            config["renderer"] == "blender-cycles"
            and config["camera"] == "agent"
            and config["fps"] == 6
            and config["samples"] == 12
            and config["size"] == [640, 480],
            "wrong render settings",
        )
        require(
            packet["options"] == trial.options and packet["command"] == trial.case.command,
            "rendered scene and task differ",
        )
        view = folder / "view"
        if letter != "initial" and self.rel(view) not in self.media:
            events = read(folder / "measurement.json")["events"]
            content = self.video(view / "view.mp4", self.videos)
            require(
                content["frames"] == len(events)
                and all(e["index"] == i for i, e in enumerate(events)),
                f"frame count mismatch in {view}",
            )
            for f in packet["frames"]:
                index = round(f["t"] * config["fps"])
                require(
                    f["file"] == f"frame-{index:05d}.jpg" and (view / f["file"]).is_file(),
                    "sample timestamp",
                )
            self.media[self.rel(view)] = content
        return trial, view

    def episode(self, epath):
        ep = read(epath)
        directory = epath.parent
        mode, f = directory.parent.name, directory.name
        require(ep["scenario"] == f and ep["mode"] == mode, "episode identity")
        require(ep["turns"] == read(directory / "transcript.json"), "transcript differs")
        calls = read(directory / "calls.json")
        visited = set()

        def ask(key, side, instruction, ctx, images=()):
            visited.add(key)
            recpath = self.path(calls[key])
            require(recpath == directory / "receipts" / (key + ".json"), "receipt outside episode")
            r = read(recpath)
            request = self.path(r["request"])
            if side == "independent":
                group = self.rel(directory / "independent" / key)
            else:
                group = (
                    "sessions/"
                    + ("continuous" if mode == "continuous" else f"{mode}/{f}")
                    + "/"
                    + side
                )
            require(
                request.name == "request.json" and request.parent.parent == self.path(group),
                "wrong request directory",
            )
            return self.raw(request, instruction, ctx, images, group, r, side != "independent")

        trial, view = self.view(f, "teach")
        first = view / "frame-00000.jpg"
        before = read(directory / "library-before.json")
        require(before == (self.library if mode == "continuous" else {}), "library before")
        key = "first-choice"
        cold = ask(
            key,
            "robot",
            self.prompts["decide"],
            dict(task=trial.case.command, options=trial.options, written_library=before),
            [first],
        )["choice"]
        profile = (
            "reverse" if mode == "contrast" and cold == trial.expected("standard") else "standard"
        )
        require(ep["profile"] == profile, "profile assignment")
        scores = {"teaching_miss": cold != trial.expected(profile)}
        _, view = self.view(f, "teach", cold)
        obs, frames = study.sample(view, 6)
        menu = list(trial.person_menu(cold).items())
        random.Random(f"person-choice/{f}").shuffle(menu)
        keys = {chr(65 + i): k for i, (k, v) in enumerate(menu)}
        public = {chr(65 + i): v for i, (k, v) in enumerate(menu)}
        person = ask(
            "person-response",
            "person",
            study.PERSON,
            dict(
                private_brief=trial.persona(profile),
                task=trial.case.command,
                observed_robot_action=trial.options[cold],
                motion_options=public,
                **obs,
            ),
            frames,
        )
        move = keys[person["response"]]
        scores["feedback_matches_persona"] = move == trial.expected_response(profile, cold)
        expected_clips = [self.rel(view / "view.mp4")]
        _, view = self.view(f, "teach", cold, move)
        expected_clips.append(self.rel(view / "view.mp4"))
        obs, frames = study.sample(view, 16)
        audit = ask(
            "audit",
            "robot",
            self.prompts["audit"],
            dict(task=trial.case.command, your_action=trial.options[cold], **obs),
            frames,
        )
        latest = study.note_text(audit)
        require(latest == (directory / "visual-only.md").read_text(), "visual-only note")

        def answer(prefix, q, t, images=()):
            return ask(
                prefix + "-answer",
                "person",
                self.prompts["answer"],
                dict(question=q, task=t.case.command, private_brief=t.persona(profile)),
                images,
            )["answer"]

        if audit.get("question", "").strip():
            q = audit["question"]
            a = answer("audit", q, trial)
            latest = study.note_text(
                ask(
                    "updated-note",
                    "robot",
                    self.prompts["refine"],
                    dict(draft=latest, question=q, person_answer=a),
                )
            )
        memory = latest
        require(memory == (directory / "memory.md").read_text(), "first-probe note")
        for phase, prefix in (("transfer", "transfer"), ("exception", "control")):
            t, v = self.view(f, phase)
            obs = [v / "frame-00000.jpg"]
            held = dict(task=t.case.command, options=t.options)
            expected = t.expected(profile)
            for condition, note in (("cold", ""), ("note", memory)):
                r = ask(
                    f"{phase}-{condition}",
                    "independent",
                    self.prompts["decide"],
                    held | {"memory": note},
                    obs,
                )
                require(r["choice"] in t.options, "invalid comparator choice")
                scores[prefix + "_" + condition] = r["choice"] == expected
            r = ask(
                phase + "-learner",
                "robot",
                self.prompts["selective"],
                held | dict(current_note=latest, previous_notes=before),
                obs,
            )
            require(r["choice"] in t.options, "invalid learner choice")
            scores[prefix + "_before_question"] = r["choice"] == expected
            if r.get("question", "").strip():
                q = r["question"]
                a = answer(phase, q, t, obs)
                r = ask(
                    phase + "-act",
                    "robot",
                    self.prompts["decide"],
                    held | dict(question=q, person_answer=a),
                )
                latest = study.note_text(
                    ask(
                        phase + "-refine",
                        "robot",
                        self.prompts["refine"],
                        dict(current_note=latest, person_answer=a),
                    )
                )
            scores[prefix + "_learner"] = r["choice"] == expected
            _, v = self.view(f, phase, r["choice"])
            expected_clips.append(self.rel(v / "view.mp4"))
        require(
            [turn["clip"] for turn in ep["turns"] if "clip" in turn] == expected_clips,
            "transcript links wrong action video",
        )
        require(
            set(calls) == visited
            and {p.stem for p in (directory / "receipts").glob("*.json")} == visited,
            "extra or missing calls",
        )
        require(scores == ep["scores"], "recomputed scores disagree")
        require(latest == (directory / "final-note.md").read_text(), "final note")
        if mode == "continuous":
            if latest.strip():
                self.library[f"{study.FAMILIES.index(f) + 1:02}"] = latest
            require(
                read(directory / "library-after.json")
                == {k + ".md": sha(v.encode()) for k, v in self.library.items()},
                "library after",
            )
        for role in ("robot", "person"):
            g = "sessions/" + ("continuous" if mode == "continuous" else f"{mode}/{f}") + "/" + role
            require(
                ep[role + "_thread"]
                == self.last[g]
                == read(self.path(g) / "session.json")["thread_id"],
                "stored session pointer",
            )
        self.episodes.append(dict(mode=mode, family=f, profile=profile, scores=scores))

    def check_retention(self):
        directory = self.root / "retention"
        results = read(directory / "results.json")
        notes = retention.library(self.root)
        require(
            results["library"]
            == {
                k: {field: n[field] for field in ("title", "file", "sha256")}
                for k, n in notes.items()
            },
            "retention library index",
        )
        for f in study.FAMILIES:
            for phase in ("transfer", "exception"):
                folder = directory / f"{f}-{phase}"
                t, v = self.view(f, phase, retained=True)
                held = dict(task=t.case.command, options=t.options)
                frame = folder / "first.jpg"
                require(digest(frame) == digest(v / "frame-00000.jpg"), "retention observation")
                ident = read(folder / "identity.json")
                require(
                    ident
                    == dict(
                        family=f,
                        phase=phase,
                        visible=held,
                        expected=t.expected("standard"),
                        image_sha256=digest(frame),
                        notes={k: n["sha256"] for k, n in notes.items()},
                        selection_instruction=retention.SELECT,
                        decision_instruction=retention.DECIDE,
                    ),
                    "retention identity",
                )

                def ask(key, prompt, ctx):
                    stage = folder / key
                    requests = list(stage.glob("*/request.json"))
                    require(len(requests) == 1, "wrong retention request count")
                    reply = self.raw(requests[0], prompt, ctx, [frame], self.rel(stage))
                    require(read(stage / "receipt.json") == reply, "retention receipt differs")
                    return reply

                expected = t.expected("standard")
                row = dict(
                    family=f,
                    phase=phase,
                    task=t.case.command,
                    expected=expected,
                    folder=folder.name,
                    options=t.options,
                    selected=[],
                )
                cold = ask("cold", retention.DECIDE, held | {"notes": []})
                row["cold"] = retention.choice(cold, t.options, expected)
                ids = ask(
                    "retrieve",
                    retention.SELECT,
                    held | {"catalog": [dict(id=k, title=n["title"]) for k, n in notes.items()]},
                )["ids"]
                if (
                    isinstance(ids, list)
                    and len(ids) <= 3
                    and all(isinstance(k, str) and k in notes for k in ids)
                    and len(set(ids)) == len(ids)
                ):
                    row["selected"] = ids
                    reply = ask(
                        "decision",
                        retention.DECIDE,
                        held | {"notes": [notes[k]["text"] for k in ids]},
                    )
                    row["library"] = retention.choice(reply, t.options, expected)
                else:
                    row["library"] = dict(choice=None, correct=None, status="invalid retrieval")
                require(row == read(folder / "result.json"), "retention score mismatch")
                self.retained.append(row)
        require(
            results["scenes"] == self.retained
            and results["summary"] == retention.summary(self.retained),
            "retention aggregates",
        )

    def lighting_recovery(self):
        directory = self.root / "episodes/isolated/lighting/receipts"
        cold = read(directory / "first-choice.json")
        group = "sessions/isolated/lighting/robot"
        trial, v = self.view("lighting", "teach")
        reply = self.raw(
            self.path(cold["request"]),
            self.prompts["decide"],
            dict(task=trial.case.command, options=trial.options, written_library={}),
            [v / "frame-00000.jpg"],
            group,
            cold,
            True,
        )
        letter = reply["choice"]
        r = read(directory / "person-response.json")
        _, v = self.view("lighting", "teach", letter)
        obs, frames = study.sample(v, 6)
        menu = list(trial.person_menu(letter).items())
        random.Random("person-choice/lighting").shuffle(menu)
        public = {chr(65 + i): v for i, (k, v) in enumerate(menu)}
        reply = self.raw(
            self.path(r["request"]),
            study.PERSON,
            dict(
                private_brief=trial.persona("standard"),
                task=trial.case.command,
                observed_robot_action=trial.options[letter],
                motion_options=public,
                **obs,
            ),
            frames,
            "sessions/isolated/lighting/person",
            r,
            True,
        )
        move = dict(zip(public, [k for k, v in menu]))[reply["response"]]
        _, v = self.view("lighting", "teach", letter, move)
        obs, frames = study.sample(v, 16)
        audit = read(directory / "audit.json")
        path = self.path(audit["request"])
        require(path.parent.parent == self.path(group), "recovered audit directory")
        self.raw(
            path,
            self.prompts["audit"],
            dict(task=trial.case.command, your_action=trial.options[letter], **obs),
            frames,
            group,
            audit,
            True,
        )
        require(len(self.recoveries) == 1, "expected exactly one recovered audit")
        return dict(
            verified_calls=self.calls,
            transport_recoveries=self.recoveries,
            action_videos=self.media,
        )

    def run(self, partial):
        plan = read(self.root / "plan.json")
        require(tuple(plan["families"]) == study.FAMILIES, "plan families")
        originals = {}
        eps = []
        for mode in ("isolated", "contrast", "continuous"):
            families = [
                f
                for f in study.FAMILIES
                if mode != "contrast" or (f in originals and not originals[f])
            ]
            for family in families:
                file = self.root / "episodes" / mode / family / "episode.json"
                if partial and not file.exists():
                    continue
                self.episode(file)
                eps.append(read(file))
                if mode == "isolated":
                    originals[family] = self.episodes[-1]["scores"]["teaching_miss"]
        discovered = set((self.root / "episodes").glob("*/*/episode.json"))
        require(
            discovered
            == {
                self.root / "episodes" / e["mode"] / e["family"] / "episode.json"
                for e in self.episodes
            },
            "unexpected episodes",
        )
        if not partial or (self.root / "report_manifest.json").exists():
            require(
                read(self.root / "report_manifest.json")["episodes"] == eps,
                "report episode set/order",
            )
            require(
                {p.stem: p.read_text() for p in (self.root / "library").glob("*.md")}
                == self.library,
                "final library",
            )
            self.check_retention()
            namespaces = ("sessions", "episodes", "retention")
            raw_requests = {
                p for name in namespaces for p in (self.root / name).rglob("request.json")
            }
            require(
                self.requests == raw_requests,
                "unaccounted raw model requests: " + str(raw_requests ^ self.requests),
            )
            if self.videos:
                films = list((self.root / "report-media").glob("episode-*.mp4"))
                require(len(films) == len(eps), "wrong count of chart films")
                from tools import interaction_report as chart

                for i, ep in enumerate(eps, 1):
                    turns = ep["turns"]
                    source_hash = hashlib.sha256(
                        (chart.VERSION + json.dumps(turns, sort_keys=True)).encode()
                    )
                    for turn in turns:
                        for _, raw in chart.media(turn):
                            source_hash.update(bytes.fromhex(digest(self.path(raw))))
                    film = (
                        self.root
                        / "report-media"
                        / f"episode-{i}-{source_hash.hexdigest()[:16]}.mp4"
                    )
                    require(film in films, f"film inputs differ for episode {i}")
                    self.films[self.rel(film)] = self.video(film, True)
        return dict(
            episodes=self.episodes,
            verified_request_namespaces=["sessions", "episodes", "retention"],
            session_count=len(self.threads),
            verified_calls=self.calls,
            recorded_failed_attempts=self.retries,
            transport_recoveries=self.recoveries,
            action_videos=self.media,
            report_films=self.films,
            retention_scenes=len(self.retained),
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument(
        "--videos",
        action="store_true",
        help="Fully decode action clips and all report films using ffmpeg.",
    )
    parser.add_argument(
        "--partial", action="store_true", help="Check finalized episodes in a still-running study."
    )
    parser.add_argument(
        "--lighting-recovery",
        action="store_true",
        help="Audit the isolated lighting upload and recovery plus its prerequisite turns.",
    )
    args = parser.parse_args()
    validator = Validator(args.run, args.videos)
    try:
        result = (
            validator.lighting_recovery() if args.lighting_recovery else validator.run(args.partial)
        )
    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
        IndexError,
        subprocess.SubprocessError,
    ) as err:
        print(
            json.dumps(
                dict(status="failed", error=str(err), verified_calls=validator.calls), indent=2
            )
        )
        return 1
    print(
        json.dumps(
            dict(
                status="lighting-recovery-passed"
                if args.lighting_recovery
                else ("partial" if args.partial else "passed"),
                **result,
            ),
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
