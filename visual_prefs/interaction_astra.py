"""Audited image turns through an isolated Codex CLI, optionally sharing a thread."""

import fcntl
import hashlib
import json
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


class AstraSession:
    def __init__(self, log_dir, *, persistent=False, timeout=180, retries=1,
                 model="gpt-6.2-astra"):
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
            return self._ask_locked(instruction, context, images)

    def _ask_locked(self, instruction, context, images):
        pending = self.log_dir / "pending.json"
        if self.persistent and pending.exists():
            raise RuntimeError(f"Persistent turn outcome requires recovery: {pending}")
        previous = self.session_id if self.persistent else None
        call = self.log_dir / f"{time.time_ns()}-{uuid.uuid4().hex[:8]}"
        call.mkdir()
        prompt = (
            "Use only the supplied images, conversation, and text. Do not use tools. "
            "Reply only with the requested JSON object.\n" + instruction
            + "\n" + json.dumps(context, ensure_ascii=False)
        )
        (call / "prompt.txt").write_text(prompt)
        manifest = []
        for index, source in enumerate(images):
            data = Path(source).read_bytes()
            suffix = ".png" if data.startswith(b"\x89PNG\r\n\x1a\n") else ".jpg"
            name = f"image-{index:03d}{suffix}"
            (call / name).write_bytes(data)
            manifest.append({"file": name, "sha256": hashlib.sha256(data).hexdigest()})
        _write_json(call / "request.json", {"model": self.model, "instruction": instruction,
                    "context": context, "images": manifest, "persistent": self.persistent,
                    "previous_thread_id": previous})
        for attempt in range(self.retries + 1):
            run = call / f"attempt-{attempt + 1}"
            run.mkdir()
            if self.persistent:
                _write_json(pending, {"attempt": str(run.relative_to(self.log_dir)),
                                      "previous_thread_id": previous})
            started = time.monotonic()
            try:
                reply, thread_id = self._invoke(prompt, manifest, previous, run)
            except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
                _write_json(run / "error.json", {"type": type(error).__name__,
                            "message": str(error), "elapsed_s": time.monotonic() - started})
                # An established thread may have accepted a timed-out or malformed turn.
                # Never send the same observation twice on that thread.
                if previous or attempt >= self.retries:
                    if self.persistent and not previous:
                        pending.unlink(missing_ok=True)
                    raise
                continue
            _write_json(run / "result.json", {"thread_id": thread_id, "reply": reply,
                        "elapsed_s": time.monotonic() - started})
            if self.persistent:
                _write_json(self.log_dir / "session.json", {"thread_id": thread_id})
                pending.unlink()
            self._last_id = thread_id
            return reply

    def _invoke(self, prompt, manifest, previous, run):
        with TemporaryDirectory() as temporary:
            work = Path(temporary)
            args = ["codex", "exec", "-s", "read-only", "--ignore-user-config",
                    "--skip-git-repo-check", "--json", "-m", self.model,
                    "-c", 'model_reasoning_effort="low"', "-c", 'web_search="disabled"',
                    "-c", "project_doc_max_bytes=0", "-c", "suppress_unstable_features_warning=true"]
            for feature in ("shell_tool", "unified_exec", "view_image", "plugins",
                            "multi_agent", "multi_agent_v2", "skill_search", "memories",
                            "workspace_dependencies"):
                args.extend(["--disable", feature])
            args.extend(["--enable", "skip_host_skill_discovery", "--enable", "omit_skill_descriptions"])
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
                subprocess.run(args, cwd=work, input=prompt.encode(), stdout=stdout,
                               stderr=stderr, timeout=self.timeout, check=True)
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
