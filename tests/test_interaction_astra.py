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
        with patch("visual_prefs.interaction_astra._run_cli", side_effect=self.emit) as run:
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
        with patch("visual_prefs.interaction_astra._run_cli", side_effect=self.emit):
            session.ask("Choose", {}, [self.image])
        with patch(
            "visual_prefs.interaction_astra._run_cli",
            side_effect=subprocess.TimeoutExpired("codex", 1),
        ) as run:
            with self.assertRaisesRegex(RuntimeError, "recovery"):
                session.ask("Choose", {}, [self.image])
            with self.assertRaisesRegex(RuntimeError, "recovery"):
                session.ask("Choose", {}, [self.image])
            self.assertEqual(run.call_count, 1)

    def test_cold_retry(self):
        def eventually(args, **kwargs):
            if len(list(self.log.glob("*/attempt-*"))) == 1:
                raise subprocess.TimeoutExpired("codex", 1)
            self.emit(args, **kwargs)

        with patch("visual_prefs.interaction_astra._run_cli", side_effect=eventually) as run:
            session = AstraSession(self.log)
            session.ask("Choose", {}, [self.image])
            self.assertEqual(run.call_count, 2)
            self.assertIn("--ephemeral", run.call_args.args[0])
            self.assertTrue(list(self.log.glob("*/attempt-1/error.json")))

    def test_exact_journal_recovery_uses_final_without_model_call(self):
        import base64
        import os

        session = AstraSession(self.log, persistent=True)
        with patch("visual_prefs.interaction_astra._run_cli", side_effect=self.emit):
            session.ask("Choose", {}, [self.image])
        with patch(
            "visual_prefs.interaction_astra._run_cli",
            side_effect=subprocess.TimeoutExpired("codex", 1),
        ):
            with self.assertRaisesRegex(RuntimeError, "recovery"):
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
            {
                "timestamp": "2099-01-01T00:00:00Z",
                "type": "event_msg",
                "payload": {"type": "task_started", "turn_id": "turn"},
            },
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
            patch("visual_prefs.interaction_astra._run_cli") as run,
        ):
            with self.assertRaisesRegex(RuntimeError, "identical"):
                session.ask("Other", {}, [self.image])
            self.assertEqual(session.ask("Next", {}, [self.image]), {"action": "done"})
            run.assert_not_called()
        recovery = json.loads((call / "attempt-2/recovery.json").read_text())
        self.assertEqual(recovery["mode"], "journal-final")
        self.assertFalse((self.log / "pending.json").exists())

    def test_timeout_kills_only_isolated_process_group(self):
        import signal

        from visual_prefs.interaction_astra import _run_cli

        with patch("subprocess.Popen") as popen, patch("os.killpg") as kill:
            child = popen.return_value.__enter__.return_value
            child.pid = 12345
            child.communicate.side_effect = subprocess.TimeoutExpired("codex", 480)
            with self.assertRaises(subprocess.TimeoutExpired):
                _run_cli(
                    ["codex"],
                    cwd=self.root,
                    input=b"hello",
                    stdout=None,
                    stderr=None,
                    timeout=480,
                    pass_fds=(),
                )
            self.assertTrue(popen.call_args.kwargs["start_new_session"])
            kill.assert_called_once_with(12345, signal.SIGKILL)
            child.wait.assert_called_once()

    def test_timeout_verifies_original_and_sends_single_empty_image_continuation(self):
        import os

        from visual_prefs.interaction_astra import CONTINUE

        for succeed in (True, False):
            work = self.root / str(succeed)
            session = AstraSession(work / "logs", persistent=True)
            home = work / "codex"
            sessions = home / "sessions"
            sessions.mkdir(parents=True)
            journal = sessions / f"rollout-{self.thread}.jsonl"
            calls = []

            def cli(args, *, input, stdout, **kwargs):
                calls.append(input.decode())
                self.assertNotIn("-i", args)
                if len(calls) == 1:
                    stdout.write(
                        json.dumps({"type": "thread.started", "thread_id": self.thread}).encode()
                        + b"\n"
                    )
                    journal.write_text(
                        "\n".join(
                            json.dumps(e)
                            for e in [
                                {
                                    "timestamp": "2099-01-01T00:00:00Z",
                                    "type": "event_msg",
                                    "payload": {"type": "task_started", "turn_id": "current"},
                                },
                                {
                                    "type": "response_item",
                                    "payload": {
                                        "type": "message",
                                        "role": "user",
                                        "content": [{"type": "input_text", "text": input.decode()}],
                                    },
                                },
                            ]
                        )
                        + "\n"
                    )
                    raise subprocess.TimeoutExpired(args, 480)
                self.assertEqual(calls[-1], CONTINUE)
                self.assertEqual(args[args.index("resume") + 1], self.thread)
                if not succeed:
                    raise subprocess.TimeoutExpired(args, 480)
                for e in (
                    {"type": "thread.started", "thread_id": self.thread},
                    {
                        "type": "item.completed",
                        "item": {"type": "agent_message", "text": '{"ok":true}'},
                    },
                    {"type": "turn.completed"},
                ):
                    stdout.write(json.dumps(e).encode() + b"\n")

            with (
                patch.dict(os.environ, {"CODEX_HOME": str(home)}),
                patch("visual_prefs.interaction_astra._run_cli", side_effect=cli),
            ):
                if succeed:
                    self.assertEqual(session.ask("Choose", {}, []), {"ok": True})
                else:
                    with self.assertRaises(subprocess.TimeoutExpired):
                        session.ask("Choose", {}, [])
                    with self.assertRaisesRegex(RuntimeError, "one continuation"):
                        session.ask("Choose", {}, [])
                self.assertEqual(len(calls), 2)
                self.assertEqual(len(list(session.log_dir.glob("*/attempt-2/recovery.json"))), 1)
                self.assertTrue(next(session.log_dir.glob("*/attempt-1/events.jsonl")).read_bytes())

    def test_identical_older_turn_cannot_be_recovered(self):
        import os

        from visual_prefs.interaction_astra import _audit_journal

        sessions = self.root / "sessions"
        sessions.mkdir()
        (sessions / f"rollout-{self.thread}.jsonl").write_text(
            "\n".join(
                json.dumps(e)
                for e in [
                    {
                        "timestamp": "2000-01-01T00:00:00Z",
                        "type": "event_msg",
                        "payload": {"type": "task_started", "turn_id": "old"},
                    },
                    {
                        "type": "response_item",
                        "payload": {
                            "type": "message",
                            "role": "user",
                            "content": [{"type": "input_text", "text": "identical"}],
                        },
                    },
                ]
            )
            + "\n"
        )
        with (
            patch.dict(os.environ, {"CODEX_HOME": str(self.root)}),
            self.assertRaisesRegex(RuntimeError, "Cannot verify"),
        ):
            _audit_journal(self.thread, "identical", [], 0, 1_700_000_000_000_000_000)
