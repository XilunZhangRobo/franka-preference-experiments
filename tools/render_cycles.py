"""Re-render MuJoCo playback frames in Blender Cycles. See docs/cycles.md."""

# Blender's isolated Python environment needs the checkout on sys.path.
# ruff: noqa: E402
import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import bpy
import imageio_ffmpeg
import mujoco

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from visual_prefs.cycles import Cycles
from visual_prefs.playback import Playback
from visual_prefs.replay_identity import (
    VERSION,
    StateDigest,
    scene_digest,
    verify_assets,
    verify_reference,
)
from visual_prefs.study import BUILDERS, PHASES, asset_hashes, correction, scene_for


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--family", choices=BUILDERS, default="paused-work")
    p.add_argument("--phase", choices=PHASES, default="teach")
    p.add_argument("--seed", type=int, default=0, help="Bundle seed, before phase layout offset")
    p.add_argument("--frame", type=int, default=0)
    p.add_argument("--end-frame", type=int, help="Inclusive end of contiguous MP4 sequence")
    p.add_argument("--fps", type=int, default=18)
    p.add_argument("--camera", choices=("agent", "wide"), default="agent")
    p.add_argument(
        "--detail-at-prop",
        metavar="ID",
        help="Place a separate inspection camera at this prop's starting position",
    )
    p.add_argument("--samples", type=int, default=32)
    p.add_argument("--threads", type=int, default=min(12, os.cpu_count() or 1))
    p.add_argument("--size", nargs=2, type=int, default=(960, 720))
    p.add_argument(
        "--device", choices=("CPU", "CUDA", "OPTIX", "HIP", "METAL", "ONEAPI"), default="CPU"
    )
    p.add_argument("--feedback", default="retry")
    p.add_argument("--profile", choices=("standard", "reverse"), default="standard")
    p.add_argument("--choice", help="Internal option ID for an executed probe or teaching action")
    p.add_argument(
        "--verify-state", type=Path, help="Recorded private phase metrics with state_sha256"
    )
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    start = args.frame
    end = args.end_frame if args.end_frame is not None else start
    if start < 0 or end < start or min(args.size) < 1 or args.fps < 1 or args.samples < 1:
        p.error("Invalid frame range, dimensions, sample count or frame rate")
    dest = args.out.resolve()
    dest.mkdir(parents=True, exist_ok=True)
    source, case = scene_for(
        args.family, args.phase, args.seed + 103 * PHASES.index(args.phase), args.profile
    )
    if args.detail_at_prop:
        if args.verify_state:
            p.error("Use the original camera for source verification")
        if args.detail_at_prop not in source.props:
            p.error(f"Unknown inspection prop {args.detail_at_prop!r}")
        args.camera = "inspection"
        source.inspection_camera(args.detail_at_prop)
    player = Playback(source, args.fps)
    if args.phase == "teach":
        case, visible, words = correction(case, source, args.feedback)
        steps = player.play(
            case, args.choice or case.default, correct=True, visible=visible, utterance=words
        )
    elif args.choice:
        steps = player.play(case, args.choice)
    else:
        steps = player.pause(0.01)
    records = []
    version = VERSION
    expected_hash = None
    reference = {}
    if args.verify_state:
        reference = json.loads(args.verify_state.read_text())
        version = verify_reference(reference, source.switches)
        expected_hash = reference["state_sha256"]
        config_path = args.verify_state.parent / "run.json"
        config = json.loads(config_path.read_text()) if config_path.exists() else {}
        verify_assets(config.get("asset_sha256"), asset_hashes(), version)
        source_size = reference.get("source_size") or config.get("size")
        if source_size:
            source.root.find("visual/global").attrib.update(
                offwidth=str(source_size[0]), offheight=str(source_size[1])
            )
    state_hash = StateDigest(version)
    scene_hash = scene_digest(source.root, version)
    if reference and reference.get("scene_sha256") != scene_hash:
        raise ValueError("Scene XML differs from the source recording")
    with tempfile.TemporaryDirectory() as temp:
        renderer = Cycles(source, player, args, Path(temp))
        for sample in steps:
            state_hash.update(player.data, player.model)
            if sample.index < start or sample.index > end:
                continue
            path = dest / f"frame-{sample.index:05d}.png"
            error = renderer.frame(path)
            records.append(
                dict(
                    frame=sample.index,
                    seconds=sample.time,
                    peak_projection_disagreement_px=error,
                    file=path.name,
                )
            )
            if sample.index == end and not expected_hash:
                break
    if expected_hash and state_hash.hexdigest() != expected_hash:
        raise ValueError("Playback state stream differs from the source phase")
    if len(records) != end - start + 1:
        raise ValueError("Requested frame range extends past the selected playback")
    if args.end_frame is not None:
        subprocess.run(
            [
                imageio_ffmpeg.get_ffmpeg_exe(),
                "-y",
                "-loglevel",
                "error",
                "-framerate",
                str(args.fps),
                "-start_number",
                str(start),
                "-i",
                str(dest / "frame-%05d.png"),
                "-frames:v",
                str(len(records)),
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-movflags",
                "+faststart",
                str(dest / "view.mp4"),
            ],
            check=True,
        )
    report = {
        **vars(args),
        "out": str(dest),
        "verify_state": str(args.verify_state) if args.verify_state else None,
        "replay_identity_version": version,
        "dynamic_lights_verified": bool(expected_hash) and version == 2,
        "verified_source_state_sha256": expected_hash,
        "blender": bpy.app.version_string,
        "mujoco": mujoco.__version__,
        "scene_sha256": scene_hash,
        "frames": records,
    }
    (dest / "render.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
