"""Versioned replay identity shared by the native recorder and Cycles backends."""

import xml.etree.ElementTree as ET
from copy import deepcopy
from hashlib import sha256

import numpy as np

VERSION = 2


def version_for(reference):
    version = reference.get("replay_identity_version", 1)
    if type(version) is not int or version not in (1, VERSION):
        raise ValueError(f"Unsupported replay identity version {version!r}")
    return version


def scene_digest(root, version=VERSION):
    """Normalize only the host-specific mesh search path, retaining all other XML."""
    version_for({"replay_identity_version": version})
    if version == 2:
        root = deepcopy(root)
        compiler = root.find("compiler")
        if compiler is not None and "meshdir" in compiler.attrib:
            compiler.set("meshdir", "{PANDA_ASSET_DIRECTORY}")
    return sha256(ET.tostring(root)).hexdigest()


class StateDigest:
    def __init__(self, version=VERSION):
        self.version = version_for({"replay_identity_version": version})
        self.hash = sha256()
        if version == 2:
            self.hash.update(b"franka-replay-state-v2\0")

    def update(self, data, model):
        for array in (data.qpos, data.mocap_pos, data.mocap_quat):
            self.hash.update(np.asarray(array, dtype="<f4").tobytes())
        if self.version == 2:
            self.hash.update(np.asarray(model.light_active, dtype="u1").tobytes())

    def hexdigest(self):
        return self.hash.hexdigest()


def verify_assets(recorded, current, version):
    if version == 2 and not recorded:
        raise ValueError("Version 2 replay requires a source asset content manifest")
    if recorded and recorded != current:
        raise ValueError("Recorded Panda or scene assets differ from the installed assets")


def verify_reference(reference, switches):
    """Refuse source verification where the old stream omits mutable lamp states."""
    version = version_for(reference)
    if switches and (version < 2 or not reference.get("state_sha256")):
        raise ValueError("Source has mutable lights but no verifiable lamp-state stream")
    if version == 2 and not reference.get("state_sha256"):
        raise ValueError("Version 2 replay requires a source state digest")
    return version
