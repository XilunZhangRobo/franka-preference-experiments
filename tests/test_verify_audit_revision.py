import hashlib
import json
import unittest
from unittest.mock import patch

import test_audit_replay as fixtures

from tools.verify_audit_revision import Audit, check_freeze_sources, check_links
from visual_prefs.audit_replay import evaluate_episode


class VerifyAuditRevision(unittest.TestCase):
    def setUp(self):
        fixture = fixtures.AuditReplayTest()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.fixture = fixture
        self.root = fixture.root
        (self.root / "plan.json").write_text("{}")
        self.policy = fixture.policy
        self.case = fixture.case

    def test_optional_freeze_sources(self):
        plan = {"dev": ["one", "two"]}
        self.root.joinpath("plan.json").write_text(json.dumps(plan))
        dev = self.root / "dev"
        dev.mkdir()
        policies = ["legacy", "revision"]
        (dev / "completed.json").write_text(json.dumps({"policies": policies}))
        hashes = {}
        for label in policies:
            for case in plan["dev"]:
                rel = f"dev/{label}/cases/{case}/result.json"
                path = self.root / rel
                path.parent.mkdir(parents=True)
                path.write_text(json.dumps({"case": case, "policy": label}))
                hashes[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
        freeze = {
            "source_plan_sha256": hashlib.sha256(
                (self.root / "plan.json").read_bytes()
            ).hexdigest(),
            "dev_result_sha256": hashes,
        }
        check_freeze_sources(self.root, plan, {})
        check_freeze_sources(self.root, plan, freeze)
        with self.assertRaisesRegex(ValueError, "source plan hash"):
            check_freeze_sources(self.root, plan, freeze | {"source_plan_sha256": "incorrect"})
        missing = dict(hashes)
        missing.pop(rel)
        with self.assertRaisesRegex(ValueError, "case coverage"):
            check_freeze_sources(self.root, plan, {"dev_result_sha256": missing})
        with self.assertRaisesRegex(ValueError, "case coverage"):
            check_freeze_sources(
                self.root, plan, {"dev_result_sha256": hashes | {"extra": "unexpected"}}
            )
        path.write_text("{}")
        with self.assertRaisesRegex(ValueError, "development result hash"):
            check_freeze_sources(self.root, plan, freeze)

    def run_fake(self, id, case, stage, **kw):
        root = self.root / stage / "fake"
        with patch("visual_prefs.interaction_astra._run_cli", side_effect=self.fixture.respond):
            result = evaluate_episode(root, id, case, self.policy, input_seed=stage, **kw)
        return result, root / "cases" / id

    def test_scores_and_ordered_attachment_faults(self):
        result, folder = self.run_fake("one", self.case, "dev")
        Audit(self.root).case(folder, self.case, self.policy, "dev", "one")
        result["probes"]["transfer"]["draft"]["correct"] = not result["probes"]["transfer"][
            "draft"
        ]["correct"]
        (folder / "result.json").write_text(json.dumps(result))
        with self.assertRaisesRegex(ValueError, "forced probe score"):
            Audit(self.root).case(folder, self.case, self.policy, "dev", "one")
        attachment = next((folder / "sessions/writer").glob("*/image-000.jpg"))
        attachment.write_bytes(b"different")
        with self.assertRaisesRegex(ValueError, "attachment hash"):
            Audit(self.root).case(folder, self.case, self.policy, "dev", "one")

    def test_observationally_identical_ambiguous_branches(self):
        self.fixture.audit_question = False
        donor, one = self.run_fake("color", self.case, "challenge", branch_selective=True)
        other = self.case | {
            "private_brief": "A different preference.",
            "probes": {"transfer": self.case["probes"]["transfer"] | {"expected": "B"}},
        }
        _, two = self.run_fake(
            "location",
            other,
            "challenge",
            shared_draft=donor["draft_receipt"],
            shared_selective={
                "transfer": donor["probes"]["transfer"]["selective"]["tentative_receipt"]
            },
            branch_selective=True,
        )
        checker = Audit(self.root)
        checker.case(one, self.case, self.policy, "challenge", "color")
        checker.case(two, other, self.policy, "challenge", "location")

    def test_links(self):
        page = self.root / "index.html"
        page.write_text('<a href="#existing">Go</a><article id="existing"></article>')
        self.assertEqual(check_links(page), 1)
        page.write_text('<a href="missing.txt">Go</a>')
        with self.assertRaisesRegex(ValueError, "broken link"):
            check_links(page)
