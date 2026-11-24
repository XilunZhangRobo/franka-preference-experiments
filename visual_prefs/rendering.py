"""RGB backends for a single simulation clock and experiment camera."""

import os
import shutil
import subprocess
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from hashlib import sha256
from importlib.util import find_spec
from pathlib import Path

import mujoco
from PIL import Image

from .assets import avatar_blend

CLASSIC = "mujoco-classic"
CYCLES = "blender-cycles"
DEFAULT_SAMPLES = 64
DEVICES = ("CPU", "CUDA", "OPTIX", "HIP", "METAL", "ONEAPI")


@dataclass(frozen=True)
class RenderSettings:
    camera: str
    size: tuple[int, int]
    samples: int = DEFAULT_SAMPLES
    device: str = "CPU"
    threads: int = min(12, os.cpu_count() or 1)


def use_blender_runtime(arguments):
    """Re-enter the CLI in the pinned Blender environment if this Python lacks bpy."""
    if find_spec("bpy") is not None:
        return
    uv = shutil.which("uv")
    if uv is None:
        raise SystemExit("Cycles recording requires uv or a Python environment with bpy installed.")
    root = Path(__file__).resolve().parents[1]
    command = [
        uv,
        "run",
        "--no-project",
        "--python",
        "3.11",
        "--with",
        "bpy==4.3.0",
        "--with",
        "numpy<2",
        "--with",
        "mujoco==4.0.1",
        "--with",
        "pillow",
        "--with",
        "imageio-ffmpeg",
        "python",
        "-I",
        "-c",
        # An installed package may live next to extensions for another Python.
        # Keep the Blender interpreter's own dependency paths first.
        "import sys; sys.path.append(sys.argv.pop(1)); from visual_prefs.cli import main; main()",
        str(root),
        *arguments,
    ]
    raise SystemExit(subprocess.run(command).returncode)


def cycles_provenance(samples, device):
    import bpy

    from . import cycles

    return {
        "name": "Blender Cycles",
        "blender": bpy.app.version_string,
        "samples": samples,
        "device": device,
        "denoising": True,
        "color_transform": "AgX",
        "sample_policy": "every simulation frame; packet and film share RGB",
        "source_blend_sha256": sha256(avatar_blend().read_bytes()).hexdigest(),
        "renderer_code_sha256": sha256(Path(cycles.__file__).read_bytes()).hexdigest(),
    }


@contextmanager
def frame_reader(backend, scene, playback, settings):
    """Yield a callable returning display-referred RGB for the current MuJoCo state."""
    if backend == CLASSIC:
        width, height = settings.size
        options = mujoco.MjvOption()
        options.geomgroup[3] = 0
        with mujoco.Renderer(playback.model, height=height, width=width) as renderer:

            def read():
                renderer.update_scene(playback.data, camera=settings.camera, scene_option=options)
                return Image.fromarray(renderer.render())

            yield read
    elif backend == CYCLES:
        from .cycles import Cycles

        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            renderer = Cycles(scene, playback, settings, temp)
            renderer.scene.render.use_persistent_data = True
            # Use Blender's output transform for both video and learner frames.
            # The raw Render Result buffer is linear, unlike a displayed image.
            path = temp / "current.png"
            renderer.scene.render.image_settings.color_mode = "RGB"
            renderer.scene.render.image_settings.compression = 2

            def read():
                # A canceled render must never reuse the preceding state's pixels.
                path.unlink(missing_ok=True)
                renderer.frame(path)
                with Image.open(path) as image:
                    if image.size != tuple(settings.size):
                        raise ValueError(f"Unexpected Cycles frame size {image.size}")
                    return image.convert("RGB")

            yield read
    else:
        raise ValueError(f"Unknown renderer {backend!r}")
