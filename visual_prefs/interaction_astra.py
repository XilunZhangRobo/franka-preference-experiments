"""Audited image turns through an isolated Codex CLI, optionally sharing a thread."""

import base64
import fcntl
import hashlib
import json
import os
import shutil
import subprocess
import time
import uuid
from pathlib import Path
from tempfile import TemporaryDirectory


def _write_json(path, value):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")
    temporary.replace(path)


CONTINUE = "Please finish the preceding unanswered request using the information already supplied. Return its requested JSON object."


def _audit_journal(thread, prompt, hashes, allowed_continuations):
    home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
    paths = list((home / "sessions").rglob(f"*{thread}.jsonl"))
    if len(paths) != 1:
        raise RuntimeError("Persistent turn recovery requires an unambiguous local session journal")
    # Keep exact journal records for the matching turn. Do not export system or account metadata.
    turns = []
    current = None
    with paths[0].open() as journal:
        for line in journal:
            event = json.loads(line)
            body = event["payload"]
            typ = body.get("type")
            if event["type"] == "event_msg" and typ == "task_started":
                current = {
                    "id": body["turn_id"],
                    "records": [line],
                    "users": [],
                    "final": None,
                    "completed": None,
                    "tools": False,
                }
                turns.append(current)
            elif current is not None and event["type"] == "response_item":
                if typ == "message" and body.get("role") == "user":
                    content = body["content"]
                    texts = [v["text"] for v in content if v["type"] == "input_text"]
                    if len(texts) == 1 and texts[0].startswith("<environment_context>"):
                        continue
                    current["users"].append(content)
                    current["records"].append(line)
                elif (
                    typ == "message"
                    and body.get("role") == "assistant"
                    and body.get("phase") == "final_answer"
                ):
                    current["final"] = "".join(
                        v["text"] for v in body["content"] if v["type"] == "output_text"
                    )
                    current["records"].append(line)
                elif typ.endswith(("_call", "_call_output")):
                    current["tools"] = True
            elif current is not None and event["type"] == "event_msg" and typ == "task_complete":
                current["completed"] = body.get("last_agent_message")
                current["records"].append(line)

    def matches(turn, text, expected_images):
        if len(turn["users"]) != 1:
            return False
        content = turn["users"][0]
        if not content or content[-1] != {"type": "input_text", "text": text}:
            return False
        if len(content) != 3 * len(expected_images) + 1:
            return False
        for index, expected_hash in enumerate(expected_images):
            opening, image, closing = content[3 * index : 3 * index + 3]
            if image["type"] != "input_image" or closing != {
                "type": "input_text",
                "text": "</image>",
            }:
                return False
            data = base64.b64decode(image["image_url"].split(",", 1)[1], validate=True)
            suffix = ".png" if data.startswith(b"\x89PNG\r\n\x1a\n") else ".jpg"
            tag = f'<image name=[Image #{index + 1}] path="image-{index:03d}{suffix}">'
            if (
                opening != {"type": "input_text", "text": tag}
                or hashlib.sha256(data).hexdigest() != expected_hash
            ):
                return False
        return True

    candidates = [i for i, t in enumerate(turns) if matches(t, prompt, hashes)]
    if not candidates:
        raise RuntimeError(
            "Cannot verify the original prompt and ordered images for pending turn recovery"
        )
    tail = turns[candidates[-1] :]
    if (
        len(tail) > 1 + allowed_continuations
        or any(t["tools"] for t in tail)
        or any(not matches(t, CONTINUE, []) for t in tail[1:])
    ):
        raise RuntimeError("Unexpected later activity in pending recovery thread")
    for t in tail:
        if t["completed"] and t["final"] and t["completed"] != t["final"]:
            raise RuntimeError("Journal completion and assistant message disagree")
    return tail


class AstraSession:
    def __init__(self, log_dir, *, persistent=False, timeout=480, retries=1, model="gpt-6.2-astra"):
        self.log_dir = Path(log_dir).resolve()
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.persistent = persistent
        self.model = model
        self.timeout = timeout
        self.retries = retries
        self._last_id = None

    @property
    def session_id(self):
        state = self.log_dir / "session.json"
        if self.persistent and state.exists():
            return json.loads(state.read_text())["thread_id"]
        return self._last_id

    def ask(self, instruction, context, images):
        """Submit attached images in order. Return the model's JSON object."""
        with (self.log_dir / ".lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            self._lock_fd = lock.fileno()
            return self._ask_locked(instruction, context, images)

    def _ask_locked(self, instruction, context, images):
        pending = self.log_dir / "pending.json"
        if self.persistent and pending.exists():
            return self._recover(pending, instruction, context, images)
        previous = self.session_id if self.persistent else None
        call = self.log_dir / f"{time.time_ns()}-{uuid.uuid4().hex[:8]}"
        call.mkdir()
        prompt = (
            "Use only the supplied images, conversation, and text. Do not use tools. "
            "Reply only with the requested JSON object.\n"
            + instruction
            + "\n"
            + json.dumps(context, ensure_ascii=False)
        )
        (call / "prompt.txt").write_text(prompt)
        manifest = []
        for index, source in enumerate(images):
            data = Path(source).read_bytes()
            suffix = ".png" if data.startswith(b"\x89PNG\r\n\x1a\n") else ".jpg"
            name = f"image-{index:03d}{suffix}"
            (call / name).write_bytes(data)
            manifest.append({"file": name, "sha256": hashlib.sha256(data).hexdigest()})
        _write_json(
            call / "request.json",
            {
                "model": self.model,
                "instruction": instruction,
                "context": context,
                "images": manifest,
                "persistent": self.persistent,
                "previous_thread_id": previous,
            },
        )
        for attempt in range(self.retries + 1):
            run = call / f"attempt-{attempt + 1}"
            run.mkdir()
            if self.persistent:
                _write_json(
                    pending,
                    {"attempt": str(run.relative_to(self.log_dir)), "previous_thread_id": previous},
                )
            started = time.monotonic()
            try:
                reply, thread_id = self._invoke(prompt, manifest, previous, run)
            except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
                _write_json(
                    run / "error.json",
                    {
                        "type": type(error).__name__,
                        "message": str(error),
                        "elapsed_s": time.monotonic() - started,
                    },
                )
                # An established thread may have accepted a timed-out or malformed turn.
                # Never send the same observation twice on that thread.
                if self.persistent:
                    # Even a first turn may have reached the service before the connection failed.
                    # An absent CLI executable is the one case known to precede model submission.
                    if isinstance(error, FileNotFoundError):
                        pending.unlink(missing_ok=True)
                    raise
                if attempt >= self.retries:
                    raise
                continue
            _write_json(
                run / "result.json",
                {"thread_id": thread_id, "reply": reply, "elapsed_s": time.monotonic() - started},
            )
            if self.persistent:
                _write_json(self.log_dir / "session.json", {"thread_id": thread_id})
                pending.unlink()
            self._last_id = thread_id
            return reply

    def _recover(self, pending, instruction, context, images):
        state = json.loads(pending.read_text())
        original = self.log_dir / state["attempt"]
        call = original.parent
        req = json.loads((call / "request.json").read_text())
        hashes = [hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in images]
        expected = [i["sha256"] for i in req["images"]]
        if (instruction, context, self.model, hashes) != (
            req["instruction"],
            req["context"],
            req["model"],
            expected,
        ):
            raise RuntimeError("Persistent turn recovery requires the identical original request")
        if any(
            hashlib.sha256((call / i["file"]).read_bytes()).hexdigest() != i["sha256"]
            for i in req["images"]
        ):
            raise RuntimeError("Archived recovery images do not match the pending request")
        events = original / "events.jsonl"
        thread = state["previous_thread_id"]
        if events.exists():
            for line in events.read_text().splitlines():
                if '"thread.started"' in line:
                    started = str(uuid.UUID(json.loads(line)["thread_id"]))
                    if thread and started != thread:
                        raise RuntimeError("Unexpected pending thread identifier")
                    thread = started
                    break
        if not thread:
            raise RuntimeError("Persistent turn recovery requires the original thread identifier")
        prompt = (call / "prompt.txt").read_text()
        expected_prompt = (
            "Use only the supplied images, conversation, and text. Do not use tools. "
            "Reply only with the requested JSON object.\n"
            + instruction
            + "\n"
            + json.dumps(context, ensure_ascii=False)
        )
        if prompt != expected_prompt:
            raise RuntimeError("Archived prompt differs from pending recovery request")
        # A process may die between writing its durable result and clearing its pending marker.
        for result_path in call.glob("attempt-*/result.json"):
            prior_result = json.loads(result_path.read_text())
            if prior_result["thread_id"] != thread:
                raise RuntimeError("Pending result belongs to a different thread")
            reply, _ = self._parse(result_path.parent, thread)
            if reply != prior_result["reply"]:
                raise RuntimeError("Saved result differs from its raw model output")
            _write_json(self.log_dir / "session.json", {"thread_id": thread})
            pending.unlink()
            self._last_id = thread
            return reply
        earlier = list(call.glob("attempt-*/recovery.json"))
        tail = _audit_journal(thread, prompt, hashes, len(earlier))
        start = time.monotonic()
        n = max(int(p.name.split("-")[-1]) for p in call.glob("attempt-*")) + 1
        run = call / f"attempt-{n}"
        run.mkdir()
        journal = run / "journal-evidence.jsonl"
        journal.write_text("".join(line for turn in tail for line in turn["records"]))
        final = tail[-1]["completed"] or tail[-1]["final"]
        _write_json(
            run / "recovery.json",
            {
                "original_attempt": original.name,
                "thread_id": thread,
                "original_turn_id": tail[0]["id"],
                "journal_turn_ids": [t["id"] for t in tail],
                "journal_evidence_sha256": hashlib.sha256(journal.read_bytes()).hexdigest(),
                "original_image_hashes": hashes,
                "original_prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
                "mode": "journal-final" if final else "same-thread-continuation",
                "continuation_prompt": None if final else CONTINUE,
                "continuation_images": [],
            },
        )
        try:
            if final:
                # Preserve the raw journal above. Explicitly normalize its already-existing final
                # message into the adapter event format consumed by all study readers.
                normalized = [
                    {"type": "thread.started", "thread_id": thread},
                    {"type": "item.completed", "item": {"type": "agent_message", "text": final}},
                    {"type": "turn.completed"},
                ]
                (run / "events.jsonl").write_text("".join(json.dumps(e) + "\n" for e in normalized))
                reply, _ = self._parse(run, thread)
            else:
                reply, _ = self._invoke(CONTINUE, [], thread, run)
        except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
            _write_json(
                run / "error.json",
                {
                    "type": type(error).__name__,
                    "message": str(error),
                    "elapsed_s": time.monotonic() - start,
                },
            )
            raise
        _write_json(
            run / "result.json",
            {"thread_id": thread, "reply": reply, "elapsed_s": time.monotonic() - start},
        )
        _write_json(self.log_dir / "session.json", {"thread_id": thread})
        pending.unlink()
        self._last_id = thread
        return reply

    def _invoke(self, prompt, manifest, previous, run):
        with TemporaryDirectory() as temporary:
            work = Path(temporary)
            args = [
                "codex",
                "exec",
                "-s",
                "read-only",
                "--ignore-user-config",
                "--skip-git-repo-check",
                "--json",
                "-m",
                self.model,
                "-c",
                'model_reasoning_effort="low"',
                "-c",
                'web_search="disabled"',
                "-c",
                "project_doc_max_bytes=0",
                "-c",
                "suppress_unstable_features_warning=true",
            ]
            for feature in (
                "shell_tool",
                "unified_exec",
                "view_image",
                "plugins",
                "multi_agent",
                "multi_agent_v2",
                "skill_search",
                "memories",
                "workspace_dependencies",
            ):
                args.extend(["--disable", feature])
            args.extend(
                ["--enable", "skip_host_skill_discovery", "--enable", "omit_skill_descriptions"]
            )
            if previous:
                args.extend(["resume", previous])
            elif not self.persistent:
                args.append("--ephemeral")
            for image in manifest:
                name = image["file"]
                shutil.copyfile(run.parent / name, work / name)
                args.extend(["-i", name])
            args.append("-")
            _write_json(run / "argv.json", args)
            events = run / "events.jsonl"
            with events.open("wb") as stdout, (run / "stderr.txt").open("wb") as stderr:
                subprocess.run(
                    args,
                    cwd=work,
                    input=prompt.encode(),
                    stdout=stdout,
                    stderr=stderr,
                    timeout=self.timeout,
                    check=True,
                    pass_fds=(self._lock_fd,),
                )
        return self._parse(run, previous)

    @staticmethod
    def _parse(run, previous):
        events = run / "events.jsonl"
        messages = []
        thread_id = None
        completed = False
        for line in events.read_text().splitlines():
            event = json.loads(line)
            if event["type"] == "thread.started":
                thread_id = str(uuid.UUID(event["thread_id"]))
            if event["type"] == "turn.completed":
                completed = True
            item = event.get("item", {})
            if item and item.get("type") not in {"agent_message", "reasoning", "error"}:
                raise RuntimeError(f"Unexpected model activity: {item.get('type')}")
            if event["type"] == "item.completed" and item.get("type") == "agent_message":
                messages.append(item["text"])
        if not completed or not messages or not thread_id or (previous and previous != thread_id):
            raise RuntimeError("CLI returned an incomplete turn or unexpected session identifier")
        raw = messages[-1].strip()
        (run / "reply.txt").write_text(messages[-1])
        parsed = json.loads(raw.removeprefix("```json").removesuffix("```").strip())
        if not isinstance(parsed, dict):
            raise ValueError("Expected a JSON object")
        return parsed, thread_id
