"""Render public sensor packets and keep action keys and simulator traces private."""

import json
import subprocess
import tempfile
from contextlib import contextmanager
from dataclasses import asdict, replace
from hashlib import sha256
from importlib import metadata
from pathlib import Path
from random import Random

import imageio_ffmpeg

from . import contextual, handover, household, paused, workshop
from .assets import REVISION, asset_dir
from .episode import Motion
from .playback import Playback
from .rendering import (
    CLASSIC,
    CYCLES,
    DEFAULT_SAMPLES,
    DEVICES,
    RenderSettings,
    cycles_provenance,
    frame_reader,
)
from .replay_identity import VERSION, StateDigest, scene_digest
from .scene import Scene

BUILDERS = {
    **paused.BUILDERS,
    **workshop.BUILDERS,
    **handover.BUILDERS,
    **household.BUILDERS,
    **contextual.BUILDERS,
}
PHASES = ("teach", "transfer", "exception")


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


@contextmanager
def new_directory(destination, preserve_failures=False):
    """Publish a complete bundle atomically and refuse to reuse an existing run."""
    destination = Path(destination)
    if destination.exists():
        raise FileExistsError(f"Choose a fresh output directory: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destination.parent) as work:
        stage = Path(work) / "result"
        stage.mkdir()
        try:
            yield stage
        except Exception as exc:
            if preserve_failures:
                write_json(
                    stage / "failure.json", {"type": type(exc).__name__, "message": str(exc)}
                )
                stage.rename(destination)
            raise
        stage.rename(destination)


def public_choices(case, seed, phase):
    items = list(case.options)
    Random(f"option-order/{phase}/{seed}").shuffle(items)
    return {chr(65 + i): name for i, name in enumerate(items)}


def scene_for(family, phase, seed, profile):
    rooms = {
        "paused-work": ("workroom", "sewing", "sewing"),
        "gift-finishing": ("studio", "studio", "kitchen"),
        "material-order": ("workroom", "studio", "shared"),
        "receiving-hand": ("workroom", "studio", "studio"),
        "approach-side": ("kitchen", "studio", "studio"),
        "private-storage": ("workroom", "studio", "shared"),
        "cleaning-scent": ("kitchen", "sewing", "shared"),
        "lighting": ("studio", "sewing", "shared"),
        "vegetable-texture": ("kitchen", "kitchen", "kitchen"),
        "completion-update": ("workroom", "studio", "studio"),
    }
    scene = Scene(rooms[family][PHASES.index(phase)])
    case = BUILDERS[family](scene, phase, seed)
    if family == "private-storage" and phase == "exception":
        scene.guest(0.65, 0.16, -70)
    if profile == "reverse":
        if family != "paused-work":
            raise ValueError("The crossed opposite-person control is implemented for paused-work.")
        case = paused.reverse_preference(scene, case, phase)
    return scene, case


def correction(case, scene, feedback):
    if feedback == "none":
        return case, False, ""
    if feedback == "incidental":
        if "near" not in scene.props or "pencil" not in scene.props:
            raise ValueError("The incidental pencil control is specific to paused-work.")
        incidental = Motion("human", "pencil", (0.062, -0.169, scene.table_z))
        return replace(case, human=[incidental]), True, ""
    mode = feedback.removesuffix("-only")
    if mode not in case.utterances:
        raise ValueError(f"Unsupported feedback {feedback}. Choices here: {list(case.utterances)}")
    return case, not feedback.endswith("-only"), case.utterances[mode]


def render(
    scene,
    case,
    folder,
    *,
    fps,
    size,
    camera,
    profile,
    choice=None,
    visible=False,
    utterance="",
    teach=False,
    renderer=CLASSIC,
    samples=DEFAULT_SAMPLES,
    device="CPU",
):
    folder.mkdir()
    width, height = size
    scene.root.find("visual/global").attrib.update(offwidth=str(width), offheight=str(height))
    if profile:
        profile.configure(scene, width, height)
    playback = Playback(scene, fps)
    events, trace, frames = [], [], []
    state_hash = StateDigest()
    steps = (
        playback.play(case, choice, correct=teach, visible=visible, utterance=utterance)
        if choice is not None
        else playback.pause(0.01)
    )
    settings = RenderSettings(camera, size, samples, device)
    with frame_reader(renderer, scene, playback, settings) as read_rgb:
        writer = None
        if choice is not None:
            writer = imageio_ffmpeg.write_frames(
                str(folder / "view.mp4"),
                size,
                fps=fps,
                codec="libx264",
                quality=8,
                macro_block_size=1,
                ffmpeg_log_level="error",
                output_params=["-threads", "1", "-movflags", "+faststart"],
            )
            writer.send(None)
        try:
            for sample in steps:
                state_hash.update(playback.data, playback.model)
                img = read_rgb()
                if profile:
                    img = profile.warp(img)
                if writer:
                    writer.send(img.tobytes())
                # Uniform sensor samples; intervention timestamps remain hidden from the audit model.
                if sample.index % max(1, round(fps / 4)) == 0 or sample.utterance:
                    filename = f"frame-{sample.index:05d}.jpg"
                    img.save(folder / filename, quality=93)
                    frames.append({"t": round(sample.time, 4), "file": filename})
                if sample.utterance:
                    speaker = (
                        "person" if sample.actor in ("idle", "human", "human-left") else "robot"
                    )
                    if sample.action == "touch" and sample.utterance in scene.sounds.values():
                        speaker = "device"
                    events.append(
                        {"t": round(sample.time, 4), "speaker": speaker, "text": sample.utterance}
                    )
                trace.append(asdict(sample))
        finally:
            if writer:
                writer.close()
    capture = {"command": case.command, "frames": frames, "speech_transcript": events}
    measured = {
        "replay_identity_version": VERSION,
        "source_size": [width, height],
        "events": trace,
        "state_sha256": state_hash.hexdigest(),
        "max_robot_pinch_error_m": playback.peak_error,
        "final_positions_m": {
            n: playback.data.mocap_pos[i].tolist() for n, i in playback.ids.items()
        },
        "scene_sha256": scene_digest(scene.root),
    }
    return capture, measured


def revision():
    try:
        root = Path(__file__).resolve().parents[1]
        return {
            "commit": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=root, text=True, stderr=subprocess.DEVNULL
            ).strip(),
            "dirty": bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=root)),
        }
    except (OSError, subprocess.CalledProcessError):
        return {"commit": None, "dirty": None}


def asset_hashes():
    panda = asset_dir()
    directories = [("panda", panda, [panda / "panda.xml", *sorted((panda / "assets").glob("*"))])]
    data = Path(__file__).parent / "data"
    directories.append(("scene", data, sorted(data.rglob("*"))))
    result = {}
    for group, root, files in directories:
        digest = sha256()
        for file in files:
            if file.is_file():
                digest.update(file.relative_to(root).as_posix().encode() + b"\0")
                digest.update(sha256(file.read_bytes()).digest())
        result[group] = digest.hexdigest()
    return result


def record(
    family,
    output,
    *,
    seed=0,
    profile="standard",
    feedback="silent",
    fps=12,
    size=(960, 720),
    camera="agent",
    calibration=None,
    accepted=False,
    transfer_seed=None,
    order_seed=None,
    renderer=CLASSIC,
    samples=DEFAULT_SAMPLES,
    device="CPU",
):
    if renderer not in (CLASSIC, CYCLES) or samples < 1 or device not in DEVICES:
        raise ValueError("Invalid RGB backend, sample count or render device.")
    if fps < 4 or any(v < 64 or v % 2 for v in size):
        raise ValueError("Use at least 4 fps and even image dimensions of 64 pixels or larger.")
    if calibration and camera != "agent":
        raise ValueError("A rig calibration applies to the agent camera.")
    cal = None
    if calibration:
        from .calibration import CalibratedCamera

        cal = CalibratedCamera.from_file(calibration)
    with new_directory(output) as dest:
        public, private = dest / "sensor", dest / "examiner"
        public.mkdir()
        private.mkdir()
        keys = {}
        # A film can take minutes; identify the checkout used at startup.
        run_revision = revision()
        rendered_with = cycles_provenance(samples, device) if renderer == CYCLES else None
        for i, phase in enumerate(PHASES):
            # Independent scene layout per phase. Adjacent run seeds reverse clipped distance.
            phase_seed = seed + 103 * i
            if phase == "transfer" and transfer_seed is not None:
                phase_seed = transfer_seed
            scene, case = scene_for(family, phase, phase_seed, profile)
            order = public_choices(case, seed if order_seed is None else order_seed, phase)
            teaching = phase == "teach"
            visible, utterance = False, ""
            if teaching:
                case, visible, utterance = correction(case, scene, feedback)
            choice = (case.expected if accepted else case.default) if teaching else None
            packet, metrics = render(
                scene,
                case,
                public / phase,
                fps=fps,
                size=size,
                camera=camera,
                profile=cal,
                choice=choice,
                visible=visible,
                utterance=utterance,
                teach=teaching,
                renderer=renderer,
                samples=samples,
                device=device,
            )
            packet["options"] = {letter: case.options[name] for letter, name in order.items()}
            write_json(public / phase / "packet.json", packet)
            write_json(private / f"{phase}.json", metrics)
            keys[phase] = {
                "choices": order,
                "answer": next(k for k, v in order.items() if v == case.expected),
                "scripted_choice": choice,
                "layout_seed": phase_seed,
            }
        provenance = {
            "format": 1,
            "replay_identity_version": VERSION,
            "family": family,
            "seed": seed,
            "order_seed": order_seed,
            "profile": profile,
            "feedback": feedback,
            "accepted_teaching_action": accepted,
            "git": run_revision,
            "camera": camera,
            "calibration": read_json(Path(calibration)) if calibration else None,
            "size": size,
            "fps": fps,
            "menagerie_reference": REVISION,
            "asset_sha256": asset_hashes(),
            "renderer": renderer,
            "versions": {
                p: metadata.version(p) for p in ("mujoco", "numpy", "Pillow", "imageio-ffmpeg")
            },
        }
        if rendered_with is not None:
            provenance["renderer_provenance"] = rendered_with
        write_json(private / "run.json", provenance | {"phases": keys})
        files = {
            p.relative_to(public).as_posix(): sha256(p.read_bytes()).hexdigest()
            for p in sorted(public.rglob("*"))
            if p.is_file()
        }
        write_json(private / "sensor-sha256.json", files)


def execute(bundle, phase, letter, output, *, device=None):
    """Render an actual selected primitive in a reconstructed probe, with its measured endpoint."""
    config = read_json(Path(bundle) / "examiner/run.json")
    phase_info = config["phases"][phase]
    backend = config.get("renderer", CLASSIC)
    settings = config.get("renderer_provenance", {})
    render_device = device or settings.get("device", "CPU")
    samples = settings.get("samples", DEFAULT_SAMPLES)
    scene, case = scene_for(config["family"], phase, phase_info["layout_seed"], config["profile"])
    with new_directory(output) as dest:
        cal = None
        if config["calibration"]:
            from .calibration import CalibratedCamera

            write_json(dest / "calibration.json", config["calibration"])
            cal = CalibratedCamera.from_file(dest / "calibration.json")
        packet, measured = render(
            scene,
            case,
            dest / "view",
            fps=config["fps"],
            size=tuple(config["size"]),
            camera=config["camera"],
            profile=cal,
            choice=phase_info["choices"][letter],
            renderer=backend,
            samples=samples,
            device=render_device,
        )
        measured["renderer"] = backend
        if backend == CYCLES:
            measured["renderer_provenance"] = cycles_provenance(samples, render_device)
        write_json(dest / "view/packet.json", packet)
        write_json(
            dest / "measurement.json",
            measured | {"selected": letter, "matched": letter == phase_info["answer"]},
        )
