"""Render initial agent views and diagnostic close-ups for development review."""

import argparse
from pathlib import Path

import mujoco
from PIL import Image, ImageDraw, ImageFont

from visual_prefs.playback import Playback
from visual_prefs.study import PHASES, scene_for

# These are human-facing review selections. They never enter learner packets.
EXAMPLES = (
    ("paused-work", "teach", "near", "Workshop parts"),
    ("paused-work", "transfer", "far", "Sewing supplies"),
    ("receiving-hand", "teach", "flashlight", "Flashlight"),
    ("approach-side", "teach", "tumbler", "Tumbler"),
    ("gift-finishing", "transfer", "gift", "Wrapped parcel"),
    ("material-order", "transfer", "pot", "Plant pot"),
    ("private-storage", "transfer", "pen_case", "Zippered pen case"),
    ("cleaning-scent", "teach", "citrus", "Cleaner bottle"),
    ("vegetable-texture", "teach", "firm", "Broccoli"),
    ("lighting", "teach", "desk_switch", "Desk light switch"),
    ("completion-update", "teach", "speaker", "Completion speaker"),
    ("paused-work", "exception", "case", "Closed stitching kit"),
)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--out", required=True, type=Path)
    args = p.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    tw, th = 320, 240
    font = ImageFont.load_default(size=17)
    sheet = Image.new("RGB", (3 * tw, 4 * (th + 31)), "#f3f1eb")
    draw = ImageDraw.Draw(sheet)
    for i, (family, phase, prop, title) in enumerate(EXAMPLES):
        scene, case = scene_for(family, phase, args.seed + 103 * PHASES.index(phase), "standard")
        if family == "paused-work" and phase != "exception":
            prop = case.default
        scene.inspection_camera(prop)
        player = Playback(scene)
        next(player.pause(0.01))
        with mujoco.Renderer(player.model, height=480, width=640) as renderer:
            for camera in ("agent", "inspection"):
                renderer.update_scene(player.data, camera=camera)
                image = Image.fromarray(renderer.render())
                image.save(args.out / f"{family}-{phase}-{camera}.jpg", quality=94)
        x = (i % 3) * tw
        y = (i // 3) * (th + 31)
        sheet.paste(image.resize((tw, th), Image.Resampling.LANCZOS), (x, y))
        draw.text((x + 9, y + th + 6), title, fill="#222624", font=font)
    sheet.save(args.out / "prop-gallery.jpg", quality=93)


if __name__ == "__main__":
    main()
