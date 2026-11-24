"""Convert a recorded experiment into an independently evaluable Cycles sensor bundle."""

import argparse
import re
import tempfile
from dataclasses import asdict
from hashlib import sha256
from importlib import metadata
from pathlib import Path

import bpy
import mujoco
import numpy as np
from PIL import Image
from render_cycles import ROOT

from visual_prefs.cycles import Cycles
from visual_prefs.playback import Playback
from visual_prefs.replay_identity import (
    StateDigest,
    scene_digest,
    verify_assets,
    verify_reference,
    version_for,
)
from visual_prefs.study import (
    PHASES,
    asset_hashes,
    correction,
    new_directory,
    read_json,
    revision,
    scene_for,
    write_json,
)


def hashes(directory):
    return {
        p.relative_to(directory).as_posix(): sha256(p.read_bytes()).hexdigest()
        for p in sorted(directory.rglob("*"))
        if p.is_file()
    }


def packet_frames(packet, fps):
    wanted = {}
    for frame in packet["frames"]:
        match = re.fullmatch(r"frame-([0-9]+)\.jpg", frame["file"])
        if not match:
            raise ValueError(f"Unsupported packet image name {frame['file']!r}")
        index = int(match[1])
        if index in wanted or round(index / fps, 4) != frame["t"]:
            raise ValueError(f"Inconsistent sample time at {frame['file']}")
        wanted[index] = frame["file"]
    if not wanted or list(wanted) != sorted(wanted):
        raise ValueError("Expected chronological nonempty sensor samples")
    return wanted


def convert_phase(source, config, phase, dest, args, temp):
    phase_record = config["phases"][phase]
    scene, case = scene_for(config["family"], phase, phase_record["layout_seed"], config["profile"])
    scene.root.find("visual/global").attrib.update(
        offwidth=str(config["size"][0]), offheight=str(config["size"][1])
    )
    reference = read_json(source / "examiner" / f"{phase}.json")
    version = verify_reference(reference, scene.switches)
    if version != version_for(config):
        raise ValueError("Inconsistent run and phase replay identity versions")
    scene_hash = scene_digest(scene.root, version)
    if scene_hash != reference["scene_sha256"]:
        raise ValueError(
            f"{phase}: scene XML differs from the recorded experiment. "
            "Use the matching source revision, assets and FRANKA_PANDA_DIR."
        )
    packet = read_json(source / "sensor" / phase / "packet.json")
    expected_options = {k: case.options[v] for k, v in phase_record["choices"].items()}
    if packet["options"] != expected_options or packet["command"] != case.command:
        raise ValueError(f"{phase}: recorded task text or option mapping no longer matches")
    if phase_record["choices"][phase_record["answer"]] != case.expected:
        raise ValueError(f"{phase}: private answer differs from this replay")
    wanted = packet_frames(packet, config["fps"])
    output = dest / "sensor" / phase
    output.mkdir()
    player = Playback(scene, config["fps"])
    choice = phase_record["scripted_choice"]
    if phase == "teach":
        case, visible, words = correction(case, scene, config["feedback"])
        intended = case.expected if config["accepted_teaching_action"] else case.default
        if intended != choice:
            raise ValueError("Recorded teaching action does not match accepted/profile settings")
        samples = player.play(case, choice, correct=True, visible=visible, utterance=words)
    else:
        samples = player.play(case, choice) if choice is not None else player.pause(0.01)
    renderer = Cycles(scene, player, args, temp)
    renderer.scene.render.image_settings.file_format = "JPEG"
    renderer.scene.render.image_settings.quality = 93
    frames, events, words = [], [], []
    max_camera_error = 0.0
    state_hash = StateDigest(version)
    for step in samples:
        state_hash.update(player.data, player.model)
        trace = asdict(step)
        if step.index >= len(reference["events"]) or trace != reference["events"][step.index]:
            raise ValueError(f"{phase}: playback event differs at frame {step.index}")
        events.append(trace)
        if step.utterance:
            speaker = "person" if step.actor in ("idle", "human", "human-left") else "robot"
            words.append({"t": round(step.time, 4), "speaker": speaker, "text": step.utterance})
        if step.index in wanted:
            path = output / wanted[step.index]
            max_camera_error = max(max_camera_error, renderer.frame(path))
            with Image.open(path) as image:
                if image.format != "JPEG" or image.size != tuple(args.size):
                    raise ValueError(f"Invalid rendered sensor image {path.name}")
                image.verify()
            frames.append(step.index)
    if (
        frames != list(wanted)
        or events != reference["events"]
        or words != packet["speech_transcript"]
    ):
        raise ValueError(f"{phase}: replay frame list, event timeline or speech differs")
    if reference.get("state_sha256") and state_hash.hexdigest() != reference["state_sha256"]:
        raise ValueError(f"{phase}: playback state differs from the recorded stream")
    poses = {k: player.data.mocap_pos[idx].tolist() for k, idx in player.ids.items()}
    if poses.keys() != reference["final_positions_m"].keys() or any(
        not np.allclose(p, reference["final_positions_m"][k], atol=1e-7, rtol=0)
        for k, p in poses.items()
    ):
        raise ValueError(f"{phase}: final prop poses differ")
    # Keep the public protocol bit identical; render only its listed pictures.
    (output / "packet.json").write_bytes((source / "sensor" / phase / "packet.json").read_bytes())
    write_json(
        dest / "examiner" / f"{phase}.json",
        {
            "replay_identity_version": version,
            "dynamic_lights_verified": version == 2,
            "events": events,
            "final_positions_m": poses,
            "max_robot_pinch_error_m": player.peak_error,
            "scene_sha256": scene_hash,
            "state_sha256": state_hash.hexdigest(),
            "verified_source_state_digest": bool(reference.get("state_sha256")),
            "peak_camera_projection_disagreement_px": max_camera_error,
            "rendered_frame_indices": frames,
        },
    )


def convert(args):
    source = args.bundle.resolve()
    config = read_json(source / "examiner/run.json")
    if config.get("calibration") is not None:
        raise ValueError("The Cycles backend supports the built-in pinhole cameras only")
    if config.get("renderer", "mujoco-classic") != "mujoco-classic":
        raise ValueError("Provide the original recorded MuJoCo bundle")
    verify_assets(config.get("asset_sha256"), asset_hashes(), version_for(config))
    source_hashes = read_json(source / "examiner/sensor-sha256.json")
    if hashes(source / "sensor") != source_hashes:
        raise ValueError("Source sensor bytes differ from the examiner manifest")
    args.camera = config["camera"]
    args.size = args.size or config["size"]
    if (
        len(args.size) != 2
        or min(args.size) < 64
        or min(args.samples, args.threads) < 1
        or np.prod(args.size) <= 0
    ):
        raise ValueError("Invalid render dimensions, thread count or samples")
    if args.size[0] * config["size"][1] != args.size[1] * config["size"][0]:
        raise ValueError("Choose the recorded aspect ratio to preserve camera framing")
    with new_directory(args.out) as dest, tempfile.TemporaryDirectory() as temp:
        (dest / "sensor").mkdir()
        (dest / "examiner").mkdir()
        for phase in PHASES:
            convert_phase(source, config, phase, dest, args, Path(temp))
        provenance = {
            "name": "Blender Cycles",
            "blender": bpy.app.version_string,
            "mujoco": mujoco.__version__,
            "samples": args.samples,
            "device": args.device,
            "threads": args.threads,
            "git": revision(),
            "format": "JPEG",
            "quality": 93,
            "source_run_sha256": sha256((source / "examiner/run.json").read_bytes()).hexdigest(),
            "source_manifest_sha256": sha256(
                (source / "examiner/sensor-sha256.json").read_bytes()
            ).hexdigest(),
            "source_size": config["size"],
            "runtime_versions": {
                pkg: metadata.version(pkg) for pkg in ("bpy", "numpy", "mujoco", "Pillow")
            },
            "source_blend_sha256": sha256(
                (ROOT / "assets/human/avatar.blend").read_bytes()
            ).hexdigest(),
            "sample_policy": "exact source packet indices",
            "source_code_sha256": {
                p.name: sha256(p.read_bytes()).hexdigest()
                for p in (
                    Path(__file__),
                    ROOT / "tools/render_cycles.py",
                    ROOT / "visual_prefs/cycles.py",
                    ROOT / "visual_prefs/playback.py",
                    ROOT / "visual_prefs/avatar.py",
                    ROOT / "visual_prefs/replay_identity.py",
                )
            },
        }
        write_json(
            dest / "examiner/run.json",
            config
            | {
                "size": list(args.size),
                "renderer": "blender-cycles",
                "renderer_provenance": provenance,
            },
        )
        write_json(dest / "examiner/sensor-sha256.json", hashes(dest / "sensor"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--size", type=int, nargs=2, metavar=("WIDTH", "HEIGHT"))
    parser.add_argument("--samples", type=int, default=24)
    parser.add_argument("--threads", type=int, default=12)
    parser.add_argument(
        "--device", choices=("CPU", "CUDA", "OPTIX", "HIP", "METAL", "ONEAPI"), default="CPU"
    )
    convert(parser.parse_args())


if __name__ == "__main__":
    main()
