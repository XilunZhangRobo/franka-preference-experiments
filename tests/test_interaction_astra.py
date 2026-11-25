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
        events = [{"type": "thread.started", "thread_id": self.thread},
                  {"type": "item.completed", "item": {"type": "agent_message",
                                                       "text": '{"action":"wait"}'}},
                  {"type": "turn.completed"}]
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
