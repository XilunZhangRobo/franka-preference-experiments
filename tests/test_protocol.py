"""Probe the boundary between observable feedback, written memory and the private scorer."""

import json
import sys
import tempfile
import unittest
from hashlib import sha256
from pathlib import Path

from visual_prefs.protocol import audited_note, evaluate
from visual_prefs.study import read_json, write_json


class ProtocolTest(unittest.TestCase):
    def packet(self, speech):
        return {
            "command": "Clear a spot.",
            "frames": [{"file": "frame-0.jpg", "t": 0.0}],
            "speech_transcript": speech,
            "options": {"A": "Move one mat.", "B": "Move the other."},
        }

    def test_speech_can_trigger_review_without_visual_correction(self):
        seen = []

        def model(prompt, context, source, frames):
            seen.append(context)
            if len(seen) == 1:
                return {"window": None}
            return {
                "observation": "A rejection followed the move.",
                "interpretation": "Cause unclear.",
                "note": "The last move was rejected; confirm the criterion.",
                "question": "",
            }

        packet = self.packet([{"speaker": "person", "t": 0.3, "text": "Try again."}])
        note, _ = audited_note(model, Path("."), packet)
        self.assertIn("rejected", note)
        self.assertEqual(len(seen), 2)
        packet["speech_transcript"][0]["speaker"] = "robot"
        note, audit = audited_note(
            lambda *args: {"window": None}, Path("."), packet, "Existing note"
        )
        self.assertEqual((note, audit), ("Existing note", None))

    def test_blinded_calls_and_failed_response_retention(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sensor = root / "bundle/sensor"
            for phase in ("teach", "transfer", "exception"):
                folder = sensor / phase
                folder.mkdir(parents=True)
                (folder / "frame-0.jpg").write_bytes(b"synthetic test image")
                write_json(folder / "packet.json", self.packet([]))
            private = root / "bundle/examiner"
            private.mkdir()
            write_json(
                private / "run.json",
                {
                    "phases": {p: {"answer": "A"} for p in ("transfer", "exception")},
                    "family": "PRIVATE_DO_NOT_SEND",
                },
            )
            write_json(
                private / "sensor-sha256.json",
                {
                    p.relative_to(sensor).as_posix(): sha256(p.read_bytes()).hexdigest()
                    for p in sensor.rglob("*")
                    if p.is_file()
                },
            )
            adapter = root / "fixture.py"
            adapter.write_text(
                "import json, sys\n"
                "v = json.load(sys.stdin)\n"
                "assert set(v) == {'images','context','instruction'}\n"
                "assert 'PRIVATE_DO_NOT_SEND' not in str(v) and 'examiner' not in str(v)\n"
                "assert all(set(x)=={'t','mime','data'} for x in v['images'])\n"
                "if 'options' in v['context']:\n"
                "    print(json.dumps({'choice':'A' if v['context']['memory']=='Remember' else 'B','reason':'fixture'}))\n"
                "elif 'existing_note' in v['context']:\n"
                "    print(json.dumps(dict(observation='seen',interpretation='tentative',note='Remember',question='')))\n"
                "else:\n"
                "    print(json.dumps({'window':[0,0]}))\n"
            )
            other = root / "other.md"
            other.write_text("Other")
            command = f'"{sys.executable}" "{adapter}"'
            evaluate(root / "bundle", root / "result", command, shuffled=other)
            results = read_json(root / "result/results.json")["decisions"]
            self.assertEqual(len(results), 6)
            self.assertTrue(
                all(r["matched_answer"] == (r["condition"] == "matched") for r in results)
            )
            self.assertEqual((root / "result/memory.md").read_text(), "Remember\n")
            self.assertEqual(len(list((root / "result").glob("call-*.json"))), 8)
            policy = root / "policy.json"
            prompts = {
                k: f"exact {k}" for k in ("audit", "refine", "selective", "decide", "answer")
            }
            write_json(policy, prompts)
            from visual_prefs.cli import main

            main(
                [
                    "evaluate",
                    str(root / "bundle"),
                    "--out",
                    str(root / "opt"),
                    "--adapter",
                    command,
                    "--shuffled",
                    str(other),
                    "--note-policy",
                    str(policy),
                    "--answer",
                    "unused",
                ]
            )
            opt = read_json(root / "opt/results.json")
            self.assertEqual(opt["decisions"], results)
            self.assertEqual(
                opt["note_policy"],
                {"sha256": sha256(policy.read_bytes()).hexdigest(), "prompts": prompts},
            )
            self.assertNotIn("note_policy", read_json(root / "result/results.json"))
            for old in sorted((root / "result").glob("call-*.json")):
                a = read_json(old)["request"]
                b = read_json(root / "opt" / old.name)["request"]
                self.assertEqual((a["context"], a["images"]), (b["context"], b["images"]))
                if "options" in a["context"]:
                    self.assertEqual(b["instruction"], prompts["decide"])
            # Fail only once the two transfer decisions have completed.
            code = adapter.read_text()
            (sensor / "exception/frame-0.jpg").write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "Sensor bytes"):
                evaluate(root / "bundle", root / "corrupt", command)
            self.assertFalse(list((root / "corrupt").glob("call-*.json")))
            (sensor / "exception/frame-0.jpg").write_bytes(b"synthetic test image")
            counter = root / "counter"
            adapter.write_text(
                "from pathlib import Path\n"
                f"p = Path({str(counter)!r})\n"
                "n = int(p.read_text()) if p.exists() else 0\n"
                "p.write_text(str(n + 1))\n"
                "if n == 4: raise RuntimeError('fixture failure')\n" + code
            )
            with self.assertRaises(RuntimeError):
                evaluate(root / "bundle", root / "late", command)
            partial = read_json(root / "late/results.json")
            self.assertEqual(partial["status"], "failed")
            self.assertEqual([row["phase"] for row in partial["decisions"]], ["transfer"] * 2)
            adapter.write_text("print('invalid output')\n")
            with self.assertRaises(json.JSONDecodeError):
                evaluate(root / "bundle", root / "failure", command)
            self.assertEqual(
                read_json(root / "failure/call-01.json")["raw_reply"], "invalid output\n"
            )
            self.assertTrue((root / "failure/failure.json").exists())
