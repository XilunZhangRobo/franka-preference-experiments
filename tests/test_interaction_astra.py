import json
import subprocess
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from visual_prefs.interaction_astra import AstraSession


class TestAstraSession(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.image = self.root / "private-phase-name.jpg"
        self.image.write_bytes(b"test image")
        self.log = self.root / "logs"
        self.thread = str(uuid.uuid4())

    def emit(self, args, *, cwd, input, stdout, **kwargs):
        self.assertNotIn("private-phase-name", str(args))
        self.assertNotIn(str(self.log), str(args))
        self.assertEqual([p.name for p in cwd.iterdir()], ["image-000.jpg"])
        events = [
            {"type": "thread.started", "thread_id": self.thread},
            {
                "type": "item.completed",
                "item": {"type": "agent_message", "text": '{"action":"wait"}'},
            },
            {"type": "turn.completed"},
        ]
        for event in events:
            stdout.write(json.dumps(event).encode() + b"\n")

    def test_resume_and_audit(self):
        with patch("subprocess.run", side_effect=self.emit) as run:
            for i in range(2):
                session = AstraSession(self.log, persistent=True)
                self.assertEqual(session.ask("Choose", {"t": i}, [self.image]), {"action": "wait"})
                self.assertEqual(session.session_id, self.thread)
            self.assertIn(self.thread, run.call_args.args[0])
        for request in self.log.glob("*/request.json"):
            image = json.loads(request.read_text())["images"][0]
            self.assertEqual((request.parent / image["file"]).read_bytes(), self.image.read_bytes())
            self.assertTrue((request.parent / "attempt-1/events.jsonl").is_file())

    def test_no_replay_after_uncertain_resumed_turn(self):
        session = AstraSession(self.log, persistent=True)
        with patch("subprocess.run", side_effect=self.emit):
            session.ask("Choose", {}, [self.image])
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("codex", 1)) as run:
            with self.assertRaises(subprocess.TimeoutExpired):
                session.ask("Choose", {}, [self.image])
            with self.assertRaisesRegex(RuntimeError, "recovery"):
                session.ask("Choose", {}, [self.image])
            self.assertEqual(run.call_count, 1)

    def test_cold_retry(self):
        def eventually(args, **kwargs):
            if len(list(self.log.glob("*/attempt-*"))) == 1:
                raise subprocess.TimeoutExpired("codex", 1)
            self.emit(args, **kwargs)

        with patch("subprocess.run", side_effect=eventually) as run:
            session = AstraSession(self.log)
            session.ask("Choose", {}, [self.image])
            self.assertEqual(run.call_count, 2)
            self.assertIn("--ephemeral", run.call_args.args[0])
            self.assertTrue(list(self.log.glob("*/attempt-1/error.json")))

    def test_exact_journal_recovery_uses_final_without_model_call(self):
        import base64
        import os

        session = AstraSession(self.log, persistent=True)
        with patch("subprocess.run", side_effect=self.emit):
            session.ask("Choose", {}, [self.image])
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("codex", 1)):
            with self.assertRaises(subprocess.TimeoutExpired):
                session.ask("Next", {}, [self.image])
        state = json.loads((self.log / "pending.json").read_text())
        call = (self.log / state["attempt"]).parent
        prompt = (call / "prompt.txt").read_text()
        journal_dir = self.root / "codex" / "sessions"
        journal_dir.mkdir(parents=True)
        content = [
            {"type": "input_text", "text": '<image name=[Image #1] path="image-000.jpg">'},
            {
                "type": "input_image",
                "image_url": "data:image/jpeg;base64,"
                + base64.b64encode(self.image.read_bytes()).decode(),
            },
            {"type": "input_text", "text": "</image>"},
            {"type": "input_text", "text": prompt},
        ]
        events = [
            {"type": "event_msg", "payload": {"type": "task_started", "turn_id": "turn"}},
            {
                "type": "response_item",
                "payload": {"type": "message", "role": "user", "content": content},
            },
            {
                "type": "event_msg",
                "payload": {"type": "task_complete", "last_agent_message": '{"action":"done"}'},
            },
        ]
        (journal_dir / f"rollout-{self.thread}.jsonl").write_text(
            "".join(json.dumps(e) + "\n" for e in events)
        )
        with (
            patch.dict(os.environ, {"CODEX_HOME": str(journal_dir.parent)}),
            patch("subprocess.run") as run,
        ):
            with self.assertRaisesRegex(RuntimeError, "identical"):
                session.ask("Other", {}, [self.image])
            self.assertEqual(session.ask("Next", {}, [self.image]), {"action": "done"})
            run.assert_not_called()
        recovery = json.loads((call / "attempt-2/recovery.json").read_text())
        self.assertEqual(recovery["mode"], "journal-final")
        self.assertFalse((self.log / "pending.json").exists())
