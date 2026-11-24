"""EGL-rendered development QA for the paused-work observation camera."""

import os
import unittest

os.environ.setdefault("MUJOCO_GL", "egl")

from visual_prefs.visibility import audit_visibility


class TestVisibility(unittest.TestCase):
    def test_both_clip_assignments(self):
        for seed in (0, 1):
            with self.subTest(seed=seed):
                report = audit_visibility(seed)
                self.assertTrue(report["passed"], report)
                teach, transfer = [report["phases"][p] for p in ("teach", "transfer")]
                self.assertNotEqual(teach["active_mat"], transfer["active_mat"])
                self.assertEqual(set(transfer["frames"]), {"start"})
                self.assertEqual(
                    set(teach["frames"]),
                    {
                        "start",
                        "robot_approach",
                        "robot_grasp",
                        "human_contact",
                        "human_undo",
                        "end",
                    },
                )
                for phase in (teach, transfer):
                    for frame in phase["frames"].values():
                        for obj in frame["objects"].values():
                            self.assertEqual(
                                obj["visible_px"] + sum(obj["occluded_px"].values()),
                                obj["isolated_px"],
                            )
                            self.assertGreaterEqual(min(obj["occluded_px"].values()), 0)

    def test_camera_looking_away_fails(self):
        outside = ((0.76, -0.78, 1.59), (1.45, -1.50, 1.49), 46)
        report = audit_visibility(0, camera_pose=outside)
        self.assertFalse(report["passed"])
        for phase in report["phases"].values():
            for obj in phase["frames"]["start"]["objects"].values():
                self.assertEqual(obj["isolated_px"], 0)
                self.assertEqual(obj["visible_px"], 0)
                self.assertFalse(obj["passed"])
