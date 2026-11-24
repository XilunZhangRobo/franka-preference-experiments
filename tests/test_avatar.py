"""Rendered mesh penetration, negative controls, and distinct correction semantics."""

import json
import unittest

import numpy as np

from visual_prefs.assets import asset_dir
from visual_prefs.human_qa import MAX_PENETRATION_M, _triangle_box_gaps, audit_human


class TriangleBoxTest(unittest.TestCase):
    def test_face_span_with_all_vertices_outside(self):
        face = np.array([[[-0.1, -0.1, 0.0], [0.1, -0.1, 0.0], [0.0, 0.1, 0.0]]])
        half = np.array([0.02, 0.02, 0.01])
        self.assertFalse((np.abs(face[0]) <= half).all(axis=1).any())
        self.assertLess(_triangle_box_gaps(face, half)[0], 0.0)
        self.assertAlmostEqual(_triangle_box_gaps(face + (0.0, 0.0, 0.03), half)[0], 0.02)


@unittest.skipUnless((asset_dir() / "panda.xml").is_file(), "Panda assets required")
class AvatarAuditTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Opposite shelf positions and opposite clipped-mat assignments.
        cls.reports = [audit_human(seed, fps=24) for seed in (0, 1)]

    def test_initial_whole_body_and_active_hand_mesh(self):
        for report in self.reports:
            with self.subTest(seed=report["flagship"]["seed"]):
                json.dumps(report, allow_nan=False)
                flagship = report["flagship"]
                self.assertGreater(
                    flagship["initial_idle_human_triangle_to_robot_clearance_lower_bound_m"], 0.0
                )
                self.assertGreater(flagship["body_vertices"], flagship["hand_vertices"])
                self.assertGreater(flagship["hand_vertices"], 500)
                for group in flagship["measurements"].values():
                    self.assertEqual(
                        set(group),
                        {
                            "tabletop",
                            "shelf",
                            "shelf_foot_1",
                            "shelf_foot_2",
                            "near_mat",
                            "far_mat",
                        },
                    )
                    for row in group.values():
                        self.assertGreater(row["frames"], 1)
                        self.assertEqual(row["frames_over_limit"], 0, row)
                        self.assertLessEqual(row["max_m"], MAX_PENETRATION_M)
                gap = flagship["grasp_and_transport_closest_hand_to_mat_m"]
                self.assertLessEqual(gap["median_m"], 0.002)
                self.assertLessEqual(gap["max_m"], 0.012)
                self.assertTrue(report["passed"])

    def test_whole_body_triangles_clear_shelf_and_mats(self):
        for report in self.reports:
            flagship = report["flagship"]
            self.assertGreater(flagship["forearm_triangles"], 50)
            self.assertGreater(flagship["body_triangles"], 10000)
            for name, row in flagship["triangle_box_all_frames_whole_body"].items():
                self.assertEqual(row["intersection_frames"], 0, (name, row))
                self.assertGreater(row["forearm_minimum_clearance_lower_bound_m"], 0.0, (name, row))

    def test_reviewed_cycles_frame_104(self):
        row = audit_human(0, fps=18)["flagship"]["reviewed_cycles_frame"]
        self.assertEqual(row["action"], "transport")
        self.assertEqual(row["whole_body_intersecting_triangles"], 0)
        self.assertGreater(row["forearm_clearance_lower_bound_m"], 0.010)

    def test_lowered_neutral_hand_fails_table_clearance(self):
        for report in self.reports:
            control = report["flagship"]["negative_control"]
            self.assertTrue(control["detected"])
            self.assertGreater(control["max_table_penetration_m"], 0.020)

    def test_two_hand_custody_and_stationary_pointing_target(self):
        for report in self.reports:
            rows = report["handover_teaching"]
            self.assertEqual(
                rows["receiving-hand"]["holders_after_actions"], ["robot", "human", "human-left"]
            )
            gesture = rows["approach-side"]
            self.assertEqual(gesture["holders_after_actions"], ["robot", "robot", "robot"])
            self.assertGreater(gesture["point_frames"], 3)
            self.assertLessEqual(gesture["point_item_displacement_m"], 1e-6)
