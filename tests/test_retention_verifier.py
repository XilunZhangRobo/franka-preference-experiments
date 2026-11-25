import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.verify_interactions import Validator
from visual_prefs.interaction_astra import AstraSession


class RetentionVerifierTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        (self.root / "plan.json").write_text("{}")
        self.stage = self.root / "retention" / "fixture-transfer" / "cold"
        self.frame = self.root / "frame.jpg"
        self.frame.write_bytes(b"camera")
        self.context = {"task": "Choose", "notes": []}
        self.reply = {"choice": "A"}

        def respond(argv, *, stdout, **kwargs):
            events = [
                {"type": "thread.started", "thread_id": "11111111-1111-4111-a111-111111111111"},
                {
                    "type": "item.completed",
                    "item": {"type": "agent_message", "text": json.dumps(self.reply)},
                },
                {"type": "turn.completed"},
            ]
            stdout.write("".join(json.dumps(row) + "\n" for row in events).encode())

        with patch("visual_prefs.interaction_astra._run_cli", side_effect=respond):
            AstraSession(self.stage).ask("Decide", self.context, [self.frame])
        (self.stage / "receipt.json").write_text(json.dumps(self.reply))
        self.good = next(self.stage.glob("*/request.json")).parent
        self.failed = self.stage / "0000000000000000000-aaaaaaaa"
        shutil.copytree(self.good, self.failed, ignore=shutil.ignore_patterns("attempt-*"))
        self.attempt = self.failed / "attempt-1"
        self.attempt.mkdir()
        for name in ("argv.json", "stderr.txt"):
            shutil.copyfile(self.good / "attempt-1" / name, self.attempt / name)
        self.events = self.attempt / "events.jsonl"
        self.events.write_text(
            '{"type":"thread.started","thread_id":"interrupted"}\n{"type":"turn.started"}\n'
        )

    def verify(self):
        v = Validator(self.root, False)
        self.assertEqual(
            v.retention_reply(self.stage, "Decide", self.context, self.frame), self.reply
        )
        return v

    def test_interrupted_unscored_and_timeout_accounting(self):
        v = self.verify()
        self.assertEqual((v.calls, len(v.requests), len(v.unscored), len(v.retries)), (1, 2, 1, 0))
        self.assertIs(v.unscored[0]["scored"], False)
        (self.attempt / "error.json").write_text('{"type":"TimeoutExpired","elapsed_s":180}')
        self.assertEqual(len(self.verify().retries), 1)

    def test_failed_input_must_be_identical(self):
        (self.failed / "image-000.jpg").write_bytes(b"other frame")
        with self.assertRaisesRegex(ValueError, "superseded image differs"):
            self.verify()

    def test_completed_failure_cannot_be_excluded(self):
        with self.events.open("a") as out:
            out.write('{"type":"turn.completed"}\n')
        with self.assertRaisesRegex(ValueError, "unexpected event"):
            self.verify()
        shutil.copyfile(self.good / "attempt-1" / "result.json", self.attempt / "result.json")
        with self.assertRaisesRegex(ValueError, "one final successful"):
            self.verify()
