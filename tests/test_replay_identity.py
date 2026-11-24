import unittest
import xml.etree.ElementTree as ET
from hashlib import sha256
from types import SimpleNamespace

import numpy as np

from visual_prefs.replay_identity import StateDigest, scene_digest, verify_assets, verify_reference


class IdentityTests(unittest.TestCase):
    def setUp(self):
        self.data = SimpleNamespace(
            qpos=np.array([0.1, 0.2]),
            mocap_pos=np.arange(3),
            mocap_quat=np.array([1.0, 0.0, 0.0, 0.0]),
        )
        self.model = SimpleNamespace(light_active=np.array([True, False]))

    def state(self, version=2):
        digest = StateDigest(version)
        digest.update(self.data, self.model)
        return digest.hexdigest()

    def test_moving_joint_or_toggling_lamp_changes_identity(self):
        original = self.state()
        old = self.state(1)
        self.model.light_active[1] = True
        self.assertNotEqual(original, self.state())
        self.assertEqual(old, self.state(1))
        self.model.light_active[1] = False
        self.data.qpos[0] += 0.001
        self.assertNotEqual(original, self.state())
        self.assertNotEqual(old, self.state(1))

    def test_mesh_directory_relocation(self):
        root = ET.fromstring('<mujoco><compiler meshdir="/old/assets"/><worldbody/></mujoco>')
        old = sha256(ET.tostring(root)).hexdigest()
        portable = scene_digest(root)
        self.assertEqual(root.find("compiler").get("meshdir"), "/old/assets")
        self.assertEqual(scene_digest(root, 1), old)
        root.find("compiler").set("meshdir", "/new/assets")
        self.assertEqual(scene_digest(root), portable)
        self.assertNotEqual(scene_digest(root, 1), old)
        root.find("compiler").set("texturedir", "/new/textures")
        self.assertNotEqual(scene_digest(root), portable)
        with self.assertRaises(ValueError):
            verify_assets({"panda": "original"}, {"panda": "different"}, 2)

    def test_legacy_mutable_lights_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "mutable lights"):
            verify_reference({"state_sha256": "a"}, {"desk": "lamp"})
        self.assertEqual(verify_reference({"state_sha256": "a"}, {}), 1)
        self.assertEqual(
            verify_reference({"state_sha256": "a", "replay_identity_version": 2}, {"desk": "lamp"}),
            2,
        )
