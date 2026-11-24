"""Regression for shelf approach clipping and loss of loose pieces."""

import json
import unittest

from visual_prefs.assets import asset_dir
from visual_prefs.contact import audit_contact, audit_robot_clearance


class ContactAuditTest(unittest.TestCase):
    def test_mirrored_shelves_and_clip_assignments(self):
        for seed, marked in ((0, "near"), (1, "far")):
            with self.subTest(seed=seed):
                report = audit_contact(seed)
                json.dumps(report, allow_nan=False)
                for trial in report["trials"]:
                    self.assertTrue(trial["passed"], trial)
                self.assertEqual(report["trials"][-1]["item"], marked)
                self.assertTrue(report["negative_control"]["detected"])
                self.assertFalse(report["negative_control"]["trial"]["passed"])
                self.assertTrue(report["additional_controls"]["overhang"]["detected"])
                self.assertTrue(report["additional_controls"]["low_arc"]["detected"])
                self.assertTrue(report["passed"])

    @unittest.skipUnless((asset_dir() / "panda.xml").is_file(), "Panda assets required")
    def test_moving_panda_links_clear_bench_and_shelf(self):
        for seed in (0, 1):
            report = audit_robot_clearance(seed)
            self.assertTrue(report["passed"], report)
            self.assertGreater(report["sampled_trajectories"][0]["collision_geoms"], 0)
