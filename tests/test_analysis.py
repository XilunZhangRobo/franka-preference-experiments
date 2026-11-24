import tempfile
import unittest
from pathlib import Path

from visual_prefs.analysis import summarize
from visual_prefs.evidence import fingerprint
from visual_prefs.study import read_json, write_json


class AnalysisTest(unittest.TestCase):
    def test_missing_runs_remain_in_the_paired_denominator(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "b/examiner").mkdir(parents=True)
            (d / "e").mkdir()
            phases = ("transfer", "exception")
            write_json(
                d / "b/examiner/run.json",
                {
                    "family": "paused-work",
                    "phases": {
                        p: {"answer": "A", "choices": {"A": "near", "B": "far"}} for p in phases
                    },
                },
            )
            (d / "b/sensor").mkdir()
            write_json(d / "b/examiner/sensor-sha256.json", {})
            identity, _, _ = fingerprint(d / "b")
            write_json(
                d / "e/results.json",
                {
                    "bundle": identity,
                    "status": "failed",
                    "decisions": [
                        {"phase": p, "condition": c, "choice": a}
                        for p in ["transfer"]
                        for c, a in (("cold", "B"), ("matched", "A"))
                    ],
                },
            )
            rows = [
                {
                    "id": i,
                    "family": "paused-work",
                    "bundle": "b",
                    "evaluation": e,
                    "conditions": ["cold", "matched"],
                }
                for i, e in (("dev1", "e"), ("dev2", "failed"))
            ]
            write_json(d / "plan.json", rows)
            summarize(d / "plan.json", d / "report")
            report = read_json(d / "report/summary.json")
            self.assertEqual(len(report["rows"]), 8)
            for pair in report["paired"]:
                expected = (1, 1) if pair["phase"] == "transfer" else (0, 2)
                self.assertEqual((pair["gain"], pair["missing"]), expected)
            self.assertEqual(report["rows"][0]["evaluation_status"], "failed")
            rows[1]["evaluation"] = "./e"
            write_json(d / "plan.json", rows)
            with self.assertRaisesRegex(ValueError, "distinct evaluation"):
                summarize(d / "plan.json", d / "duplicate")
            # Same family and letters, different seed/key.
            write_json(d / "plan.json", rows[:1])
            key = d / "b/examiner/run.json"
            write_json(key, read_json(key) | {"seed": 17})
            with self.assertRaisesRegex(ValueError, "identity mismatch"):
                summarize(d / "plan.json", d / "wrong-bundle")
