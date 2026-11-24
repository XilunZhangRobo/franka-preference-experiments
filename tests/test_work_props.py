"""Regressions for shortcuts that made solid stand-ins look like task cues."""

import unittest
import xml.etree.ElementTree as ET

import mujoco
import numpy as np

from visual_prefs import paused
from visual_prefs.scene import Scene


def build_mat(clipped):
    source = Scene.__new__(Scene)
    root = ET.Element("mujoco")
    source.asset = ET.SubElement(root, "asset")
    source.world = ET.SubElement(root, "worldbody")
    source.props, source.grasps, source.human_grasps = {}, {}, {}
    source.mat_parts, source.files = {}, {}
    source.cargo_layout_side = 1
    source.cargo_layout_seed = 0
    paused.workmat(source, "near", (0, 0, 0), "#316f72", False, clipped)
    return source, root


class WorkPropsTest(unittest.TestCase):
    def test_ticket_and_cargo_do_not_reveal_status(self):
        marked, _ = build_mat(True)
        unmarked, _ = build_mat(False)
        body = marked.props["near"]
        self.assertGreater(len(marked.mat_parts["near"].clip), 0)
        for geom in marked.mat_parts["near"].clip:
            body.remove(geom)
        self.assertEqual(ET.tostring(body), ET.tostring(unmarked.props["near"]))
        self.assertEqual(marked.files, unmarked.files)

    def test_washer_has_a_real_through_hole(self):
        source, root = build_mat(True)
        part = source.props["near"].find("geom[@mesh='cargo_washer']")
        part.set("name", "washer_for_ray")
        model = mujoco.MjModel.from_xml_string(ET.tostring(root, encoding="unicode"), source.files)
        data = mujoco.MjData(model)
        mujoco.mj_forward(model, data)
        geom_id = model.geom("washer_for_ray").id
        # The collision proxy is a disc. The visual ray must pass through its
        # middle and hit the metal annulus 10 mm to one side.
        origin = np.fromstring(part.get("pos"), sep=" ") + [0, 0, 0.035]
        down = np.array((0.0, 0.0, -1.0))
        self.assertEqual(mujoco.mj_rayMesh(model, data, geom_id, origin, down), -1)
        self.assertGreater(
            mujoco.mj_rayMesh(model, data, geom_id, origin + [0.010, 0.00004, 0], down), 0
        )
