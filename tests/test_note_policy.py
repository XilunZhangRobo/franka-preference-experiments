import json
import tempfile
import unittest
from hashlib import sha256
from pathlib import Path
from unittest.mock import Mock, patch

from visual_prefs import interaction_study as study
from visual_prefs import protocol


class NotePolicyTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.path = self.root / "policy.json"
        self.prompts = {
            k: "exact " + k + "\n" for k in ("audit", "refine", "selective", "answer", "decide")
        }
        self.path.write_text(json.dumps(self.prompts))

    def test_plan_only_changes_when_opted_in(self):
        plans = []
        for args in ([], ["--note-policy", str(self.path)]):
            with (
                patch("sys.argv", ["study", str(self.root), *args]),
                patch.object(study, "snapshot", side_effect=StopIteration) as snapshot,
            ):
                with self.assertRaises(StopIteration):
                    study.main()
                plans.append(snapshot.call_args.args[1])
        pin = plans[1].pop("note_policy")
        self.assertEqual(plans[0], plans[1])
        self.assertNotIn("note_policy", plans[0])
        self.assertEqual(
            pin, {"sha256": sha256(self.path.read_bytes()).hexdigest(), "prompts": self.prompts}
        )
        self.assertEqual(
            study.Study(self.root, 1).prompts,
            dict(
                audit=study.AUDIT,
                refine=study.REFINE,
                selective=study.DECIDE_ASK,
                answer=study.ANSWER,
                decide=study.DECIDE,
            ),
        )

    def test_verifier_uses_the_pinned_plan(self):
        from tools.verify_interactions import Validator

        pin = study.Study(self.root, 1, self.path).note_policy
        (self.root / "plan.json").write_text(json.dumps({"note_policy": pin}))
        self.assertEqual(Validator(self.root, False).prompts, self.prompts)
        (self.root / "plan.json").write_text("{}")
        self.assertEqual(Validator(self.root, False).prompts, study.LEGACY_PROMPTS)

    def test_live_entry_dispatch(self):
        for question in ("", "Clarify?"):
            folder = self.root / ("asked" if question else "blank")
            s = study.Study(folder, 1, self.path)
            trial = Mock()
            trial.case.command = "Move an item."
            trial.options = {"A": "Move it", "B": "Leave it"}
            trial.expected.return_value = "A"
            trial.person_menu.return_value = {"accept": "Accept it"}
            trial.expected_response.return_value = "accept"
            trial.persona.return_value = "Private brief"
            s.initial = Mock(return_value=(trial, folder / "frame.jpg"))
            s.media = Mock(return_value=(trial, folder))
            ep = study.Episode(s, "isolated", "lighting")
            seen = []

            def ask(key, session, prompt, context, images=()):
                seen.append((key, prompt))
                if key == "person-response":
                    return {"response": "A"}
                if prompt == self.prompts["answer"]:
                    return {"answer": "Move it."}
                if prompt in (self.prompts["audit"], self.prompts["refine"]):
                    return dict(
                        title="Rule",
                        note="Move it.",
                        observation="Moved.",
                        interpretation="May prefer.",
                        question=question,
                    )
                return dict(choice="A", reason="Fixture", question=question)

            ep.ask = ask
            with patch.object(study, "sample", return_value=({"seconds": [], "heard": []}, [])):
                ep.run()
            calls = dict(seen)
            self.assertEqual(calls["audit"], self.prompts["audit"])
            self.assertEqual(calls["first-choice"], self.prompts["decide"])
            self.assertEqual(calls["transfer-learner"], self.prompts["selective"])
            self.assertEqual(calls["exception-note"], self.prompts["decide"])
            if question:
                self.assertEqual(calls["updated-note"], self.prompts["refine"])
                self.assertEqual(calls["exception-answer"], self.prompts["answer"])
                self.assertEqual(calls["transfer-act"], self.prompts["decide"])
            else:
                self.assertFalse(any(k.endswith(("-answer", "-act", "-refine")) for k in calls))
                self.assertNotIn("updated-note", calls)

    def test_bundle_refine_dispatch_preserves_existing_gates(self):
        packet = dict(command="Arrange.", speech_transcript=[], frames=[{"t": 0}])
        for prompts in (None, self.prompts):
            for question in ("", "Clarify?"):
                model = Mock(
                    side_effect=[
                        {"window": [0, 0]},
                        dict(observation="", interpretation="", note="Draft", question=question),
                        {"note": "Revised"},
                    ]
                )
                note, _ = protocol.audited_note(
                    model, self.root, packet, answer="Yes", prompts=prompts
                )
                got = [c.args[0] for c in model.call_args_list]
                want = [protocol.DETECT, self.prompts["audit"] if prompts else protocol.AUDIT]
                if question:
                    want.append(self.prompts["refine"] if prompts else protocol.AUDIT)
                self.assertEqual(got, want)
                self.assertEqual(note, "Revised" if question else "Draft")
