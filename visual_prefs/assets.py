"""Acquire only the Panda subtree of a known Menagerie revision."""

import os
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

REVISION = "eea4c7431b63da8278b0ff31638e0b0e941cec0e"
REMOTE = "https://github.com/google-deepmind/mujoco_menagerie.git"


def asset_dir() -> Path:
    override = os.getenv("FRANKA_PANDA_DIR")
    if override:
        return Path(override).expanduser()
    cache = Path(os.getenv("XDG_CACHE_HOME", Path.home() / ".cache"))
    return cache / "franka-visual-prefs" / REVISION / "franka_emika_panda"


def fetch():
    target = asset_dir()
    if (target / "panda.xml").is_file() and (target / "assets/link0.stl").is_file():
        return target
    if os.getenv("FRANKA_PANDA_DIR"):
        raise ValueError(f"FRANKA_PANDA_DIR must contain panda.xml and assets/: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=target.parent) as work:

        def git(*args):
            subprocess.run(["git", "-C", work, *args], check=True)

        git("init", "-q")
        git("remote", "add", "origin", REMOTE)
        git("sparse-checkout", "init", "--cone")
        git("sparse-checkout", "set", "franka_emika_panda")
        git("fetch", "--filter=blob:none", "--depth=1", "origin", REVISION)
        git("checkout", "--detach", "FETCH_HEAD")
        source = Path(work) / "franka_emika_panda"
        try:
            source.rename(target)
        except OSError:
            if not (target / "panda.xml").is_file():
                raise
    return target
