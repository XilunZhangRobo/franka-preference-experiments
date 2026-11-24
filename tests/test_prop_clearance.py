"""The clearance audit must detect an obstruction on a real manipulator trajectory."""

import unittest

from visual_prefs.assets import asset_dir
from visual_prefs.prop_clearance import trial


@unittest.skipUnless((asset_dir() / "panda.xml").is_file(), "Panda assets required")
class PropClearanceTest(unittest.TestCase):
    def test_paused_work_obstruction(self):
        row = trial(0, "teach", "near", 18, misplaced=True)
        self.assertTrue(row["passed"], row)
        self.assertEqual(set(row["panda"]), {"cargo", "clip", "ticket", "control"})
        self.assertLess(row["panda"]["control"]["gap_m"], -0.01)
        for group in (row["hands"], row["panda"]):
            for name, sample in group.items():
                if name != "control":
                    self.assertGreater(sample["gap_m"], 0, sample)
