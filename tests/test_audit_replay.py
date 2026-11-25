import json
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from visual_prefs.audit_replay import evaluate_episode


class AuditReplayTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        image = self.root / "PRIVATE-label.jpg"
        image.write_bytes(b"frame")
        self.case = {
            "task": "Arrange the items.",
            "action": "Move the first item.",
            "private_brief": "SECRET",
            "images": [image],
            "seconds": [0],
            "heard": [],
            "probes": {
                "transfer": {
                    "task": "Arrange these.",
                    "options": {"B": "Move it", "A": "Leave it"},
                    "expected": "A",
                    "images": [image],
                }
            },
        }
        self.policy = {k: k for k in ("audit", "refine", "decide", "selective", "answer")}
        self.audit_question = True
        self.audit_empty = False
        self.records = []

    def respond(self, argv, *, input, stdout, **kwargs):
        _, instruction, ctx = input.decode().split("\n", 2)
        ctx = json.loads(ctx)
        self.assertNotIn("PRIVATE-label", str(argv))
        self.assertNotIn("expected", ctx)
        if instruction != "answer":
            self.assertNotIn("SECRET", str(ctx))
        thread = argv[argv.index("resume") + 1] if "resume" in argv else str(uuid.uuid4())
        self.records.append((thread, instruction, ctx))
        if instruction == "audit":
            reply = {
                "observation": "Someone moved.",
                "interpretation": "Unclear.",
                "title": "Rule",
                "note": "" if self.audit_empty else "First rule.",
                "question": "Preference?" if self.audit_question else "",
            }
        elif instruction == "answer":
            reply = {"answer": "Leave it."}
        elif instruction == "refine":
            reply = {"title": "Rule", "note": "Leave it."}
        elif instruction == "selective":
            reply = {"choice": "B", "reason": "Needs clarification.", "question": "Leave it?"}
        else:
            choice = "A" if "person_answer" in ctx or "Leave it" in ctx.get("memory", "") else "B"
            reply = {"choice": choice, "reason": "I chose an option."}
        events = [
            {"type": "thread.started", "thread_id": thread},
            {
                "type": "item.completed",
                "item": {"type": "agent_message", "text": json.dumps(reply)},
            },
            {"type": "turn.completed"},
        ]
        stdout.write("".join(json.dumps(e) + "\n" for e in events).encode())

    def test_matched_arms_and_resume(self):
        with patch("visual_prefs.interaction_astra._run_cli", side_effect=self.respond) as cli:
            res = evaluate_episode(self.root, "one", self.case, self.policy)
            self.assertEqual(res["changes"]["audit"]["gains"], 1)
            self.assertEqual(res["changes"]["selective"]["gains"], 1)
            self.assertEqual(res["opportunities"]["control"], {"asked": 0, "available": 0})
            self.assertEqual(self.records[-1][0], self.records[-3][0])
            n = cli.call_count
            # Simulate a crash after the adapter committed the response, before receipt publication.
            (self.root / "cases/one/receipts/transfer-final.json").unlink()
            self.assertEqual(res, evaluate_episode(self.root, "one", self.case, self.policy))
            self.assertEqual(cli.call_count, n)
            altered = {**self.case, "action": "Change action."}
            with self.assertRaisesRegex(ValueError, "inputs or policy changed"):
                evaluate_episode(self.root, "one", altered, self.policy)

    def test_identical_note_and_donor(self):
        self.audit_question = False
        with patch("visual_prefs.interaction_astra._run_cli", side_effect=self.respond):
            original = evaluate_episode(self.root, "one", self.case, self.policy)
            self.assertTrue(original["probes"]["transfer"]["post_answer"]["reused"])
            n = len(self.records)
            fork = evaluate_episode(
                self.root,
                "other",
                self.case | {"private_brief": "A different brief."},
                self.policy,
                shared_draft=original["draft_receipt"],
            )
            self.assertNotIn("audit", [i for _, i, _ in self.records[n:]])
            self.assertEqual(fork["draft_reply"], original["draft_reply"])
            with self.assertRaisesRegex(ValueError, "differs"):
                evaluate_episode(
                    self.root,
                    "mismatched",
                    self.case | {"choice_reason": "Other reason."},
                    self.policy,
                    shared_draft=original["draft_receipt"],
                )

    def test_quiet_without_probes(self):
        self.audit_question = False
        self.audit_empty = True
        with patch("visual_prefs.interaction_astra._run_cli", side_effect=self.respond) as cli:
            result = evaluate_episode(
                self.root, "quiet", self.case | {"quiet": True, "probes": {}}, self.policy
            )
        self.assertEqual(cli.call_count, 1)
        self.assertFalse(any(result["quiet_checks"].values()))
        self.assertEqual(result["changes"]["audit"]["pairs"], 0)

    def test_shared_tentative_has_separate_answers_and_fresh_final_contexts(self):
        self.audit_question = False
        with patch("visual_prefs.interaction_astra._run_cli", side_effect=self.respond):
            one = evaluate_episode(self.root, "one", self.case, self.policy, branch_selective=True)
            prior = one["probes"]["transfer"]["selective"]["tentative_receipt"]
            n = len(self.records)
            two = evaluate_episode(
                self.root,
                "two",
                self.case | {"private_brief": "Other."},
                self.policy,
                shared_draft=one["draft_receipt"],
                shared_selective={"transfer": prior},
            )
            branch_calls = self.records[n:]
            self.assertNotIn("selective", [inst for _, inst, _ in branch_calls])
            self.assertTrue(
                any(
                    inst == "answer" and ctx["private_brief"] == "Other."
                    for _, inst, ctx in branch_calls
                )
            )
            final_ctx = branch_calls[-1][2]
            self.assertEqual(
                final_ctx["tentative_reply"], one["probes"]["transfer"]["selective"]["tentative"]
            )
            self.assertTrue(all(c[0] != branch_calls[-1][0] for c in self.records[:-1]))
            self.assertEqual(
                two["probes"]["transfer"]["selective"]["share_status"], "identical input"
            )
            self.assertEqual(
                two["probes"]["transfer"]["selective"]["final_context"], "fresh branch"
            )
            changed = dict(
                self.case,
                probes={"transfer": self.case["probes"]["transfer"] | {"task": "Another task."}},
            )
            three = evaluate_episode(
                self.root, "three", changed, self.policy, shared_selective={"transfer": prior}
            )
            self.assertEqual(
                three["probes"]["transfer"]["selective"]["share_status"], "inputs differ"
            )
