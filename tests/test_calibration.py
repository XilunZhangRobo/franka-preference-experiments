"""Synthetic camera and marker regressions, with no physical calibration data."""

import copy
import json
import os
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

import numpy as np
from PIL import Image

from visual_prefs.calibration import CalibratedCamera

# Deliberately anisotropic and off-center. Pose uses an optical-to-world rotation.
PROFILE = {
    "image_size": [320, 240],
    "image_space": "undistorted",
    "intrinsics": {"fx": 250, "fy": 175, "cx": 143, "cy": 130},
    "world_from_camera": [[0, 0, 1, 1], [1, 0, 0, 2], [0, 1, 0, 3], [0, 0, 0, 1]],
    "fit_image_ids": ["synthetic-fit"],
}
POINTS = [[2, 1.8, 2.8], [2, 2.2, 2.8], [2, 2.2, 3.2], [2, 1.8, 3.2]]
PIXELS = [[93, 95], [193, 95], [193, 165], [93, 165]]


def observations():
    return {
        "image_id": "synthetic-held-out",
        "corners": [
            {"label": str(i), "pixel": list(pixel), "world_m": xyz}
            for i, (pixel, xyz) in enumerate(zip(PIXELS, POINTS))
        ],
    }


class TestCamera(unittest.TestCase):
    def test_residuals(self):
        with TemporaryDirectory() as directory:
            path = Path(directory, "camera.json")
            path.write_text(json.dumps(PROFILE))
            camera = CalibratedCamera.from_file(path)
        points = observations()
        points["corners"][1]["pixel"] = [196, 99]
        report = camera.validate(points)
        self.assertAlmostEqual(report["rms_px"], 2.5)
        self.assertAlmostEqual(report["max_px"], 5)
        self.assertAlmostEqual(report["errors_px"]["1"], 5)
        points["image_id"] = "synthetic-fit"
        with self.assertRaisesRegex(ValueError, "held-out"):
            camera.validate(points)

    def test_invalid_transform_and_negative_depth(self):
        for row, col, value in [(0, 2, -1), (1, 0, 2), (3, 0, 0.2), (0, 3, float("inf"))]:
            profile = copy.deepcopy(PROFILE)
            profile["world_from_camera"][row][col] = value
            with self.assertRaises(ValueError):
                CalibratedCamera(profile)
        with self.assertRaisesRegex(ValueError, "optical plane"):
            CalibratedCamera(PROFILE).project([[0, 2, 3]])

    def test_reject_aspect_change(self):
        with self.assertRaisesRegex(ValueError, "aspect ratio"):
            CalibratedCamera(PROFILE).configure(None, 640, 360)

    def test_rendered_marker_centers(self):
        os.environ.setdefault("MUJOCO_GL", "egl")
        import mujoco

        root = ET.fromstring(
            '<mujoco><visual><global offwidth="640" offheight="480"/>'
            '</visual><asset><material name="marker" rgba="1 0 0 1" '
            'emission="1"/></asset><worldbody><camera name="agent"/>'
            "</worldbody></mujoco>"
        )
        scene = SimpleNamespace(world=root.find("worldbody"))
        for coord in POINTS:
            ET.SubElement(
                scene.world,
                "geom",
                type="sphere",
                size=".012",
                pos=" ".join(map(str, coord)),
                material="marker",
            )
        for scale in [1, 2]:
            width, height = 320 * scale, 240 * scale
            camera = CalibratedCamera(PROFILE)
            camera.configure(scene, width, height)
            model = mujoco.MjModel.from_xml_string(ET.tostring(root, encoding="unicode"))
            data = mujoco.MjData(model)
            mujoco.mj_forward(model, data)
            with mujoco.Renderer(model, height=height, width=width) as renderer:
                renderer.update_scene(data, camera="agent")
                image = np.asarray(camera.warp(Image.fromarray(renderer.render())))
            ys, xs = np.where((image[:, :, 0] > 150) & (image[:, :, 1] < 60))
            for pixel in PIXELS:
                cx, cy = (np.array(pixel) + 0.5) * scale - 0.5
                nearby = (np.abs(xs - cx) < 12 * scale) & (np.abs(ys - cy) < 12 * scale)
                self.assertTrue(nearby.any())
                np.testing.assert_allclose(
                    [xs[nearby].mean(), ys[nearby].mean()], [cx, cy], rtol=0, atol=0.6
                )
