"""Generate one locked held-out crossed-tray challenge. Does not invoke a model."""

import argparse
import hashlib
import shlex
from contextlib import contextmanager
from dataclasses import asdict
from pathlib import Path

import imageio_ffmpeg
import numpy as np

from .episode import Case, Motion
from .household import _tray
from .playback import Playback
from .rendering import CYCLES, RenderSettings, cycles_provenance, frame_reader
from .scene import Scene
from .study import asset_hashes, new_directory, revision, write_json

FPS = 6
SIZE = (640, 480)
SETTINGS = RenderSettings("agent", SIZE, 12, "CPU")
OPTIONS = {"A": "Put the piece in the teal tray.", "B": "Put the piece in the amber tray."}
COLORS = {"teal": "#047f85", "amber": "#eaa125"}
TASK = "Put the finished piece away."
CONTROL = "For this piece, please use the amber tray."
BRIEFS = {
    "color": "My finished pieces go in the teal tray, wherever that tray sits. The tray's color matters to me. If I explicitly request a different tray for one piece, use the tray I request.",
    "location": "My finished pieces go in the tray on my own left, whichever color is there. Its position relative to my body matters to me. If I explicitly request a different tray for one piece, use the tray I request.",
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(swapped):
    scene = Scene("studio")
    z = scene.table_z
    scene.person(x=0, y=0.44)
    scene.rest_hand("right", (-0.205, 0.17, z + 0.060))
    scene.rest_hand("left", (0.205, 0.17, z + 0.060))
    destination = {}
    for color, x in (("teal", 0.148), ("amber", -0.148)):
        x = -x if swapped else x
        y = 0.035
        _tray(scene, scene.world, x, y, z, 0.182, 0.145, 0.020, COLORS[color])
        destination[color] = (x, y, z + 0.006)
    item = scene.prop("piece", (0, -0.138, z))
    scene.cyl(item, (0, 0, 0.012), 0.026, 0.024, "#f4efe2")
    scene.cyl(item, (0, 0, 0.025), 0.023, 0.003, "#e9e2d1")
    scene.grasp("piece", (0, 0, 0.013))
    robot = {color: [Motion("robot", "piece", point)] for color, point in destination.items()}
    correction = [Motion("human", "piece", destination["teal"])]
    case = Case(
        TASK, {"teal": OPTIONS["A"], "amber": OPTIONS["B"]}, "teal", "amber", robot, correction
    )
    return scene, case, destination


@contextmanager
def film(path):
    writer = imageio_ffmpeg.write_frames(
        str(path),
        SIZE,
        fps=FPS,
        codec="libx264",
        quality=8,
        macro_block_size=1,
        ffmpeg_log_level="error",
        output_params=["-threads", "1", "-movflags", "+faststart"],
    )
    writer.send(None)
    try:
        yield writer
    finally:
        writer.close()


def camera_xy(play, point):
    cid = play.model.camera("agent").id
    local = play.data.cam_xmat[cid].reshape(3, 3).T @ (np.asarray(point) - play.data.cam_xpos[cid])
    focal = 0.5 * SIZE[1] / np.tan(np.deg2rad(play.model.cam_fovy[cid] / 2))
    return [
        round(SIZE[0] / 2 + focal * local[0] / (-local[2])),
        round(SIZE[1] / 2 - focal * local[1] / (-local[2])),
    ]


def geometry_check(play, dest, image):
    pixels = np.array(image)
    centers = {k: camera_xy(play, v) for k, v in dest.items()}
    channels = {}
    for color, (x, y) in centers.items():
        patch = pixels[y - 4 : y + 5, x - 4 : x + 5]
        r, g, b = channels[color] = np.median(patch.reshape(-1, 3), axis=0).tolist()
        if color == "teal" and g - r < 20 or color == "amber" and r - b < 35:
            raise ValueError(
                f"Tray color or occlusion check failed: {color}, {(x, y)}, {(r, g, b)}"
            )
    separation = float(np.linalg.norm(np.subtract(centers["amber"], centers["teal"])))
    if separation < 70:
        raise ValueError(f"Projected center separation only {separation}px")
    return dict(centers_px=centers, separation_px=separation, visible_median_rgb=channels)


def packet(folder, task, frames, options=None, video=False):
    out = dict(task=task, options=options or {}, frames=frames, speech_transcript=[])
    if video:
        out["video"] = "v.mp4"
    write_json(folder / "packet.json", out)
    return out


def snapshot(folder, index, image):
    filename = f"i{index:03d}.jpg"
    image.save(folder / filename, quality=93)
    return dict(t=round(index / FPS, 4), file=filename)


def check_final(play, dest):
    pose = play.data.mocap_pos[play.ids["piece"]]
    if not np.allclose(pose, dest, atol=0.0001):
        raise ValueError(f"Unexpected final position {pose}")
    return pose.tolist()


def teaching(public, private):
    scene, case, dest = build(False)
    play = Playback(scene, FPS)
    views = {k: public / k for k in ("teach", "silence")}
    for path in views.values():
        path.mkdir()
    frames = {k: [] for k in views}
    trace = []
    with film(views["teach"] / "v.mp4") as active, film(views["silence"] / "v.mp4") as silent:
        with frame_reader(CYCLES, scene, play, SETTINGS) as read:

            def record(sample, shared):
                image = read()
                active.send(image.tobytes())
                frames["teach"].append(snapshot(views["teach"], sample.index, image))
                if shared:
                    silent.send(image.tobytes())
                    frames["silence"].append(snapshot(views["silence"], sample.index, image))
                trace.append(
                    asdict(sample) | {"piece_xyz": play.data.mocap_pos[play.ids["piece"]].tolist()}
                )
                return image

            for sample in play.play(case, "amber", correct=False):
                image = record(sample, True)
                if sample.index == 0:
                    visibility = geometry_check(play, dest, image)
            split = play.index
            placed = check_final(play, dest["amber"])
            for motion in case.human:
                for sample in play.move(motion):
                    record(sample, False)
            for sample in play.pause(0.7):
                record(sample, False)
            corrected = check_final(play, dest["teal"])
        idle_scene, idle_case, _ = build(False)
        idle = Playback(idle_scene, FPS)
        list(idle.play(idle_case, "amber", correct=False))
        if idle.index != split:
            raise ValueError("Silence and teaching clocks disagree")
        with frame_reader(CYCLES, idle_scene, idle, SETTINGS) as read:
            for sample in idle.pause((len(trace) - split) / FPS):
                image = read()
                silent.send(image.tobytes())
                frames["silence"].append(snapshot(views["silence"], sample.index, image))
                check_final(idle, dest["amber"])
        if len(frames["silence"]) != len(frames["teach"]):
            raise ValueError("Matched clip lengths disagree")
    for k in views:
        packet(views[k], TASK, frames[k], video=True)
    for i in range(split):
        if sha(views["teach"] / frames["teach"][i]["file"]) != sha(
            views["silence"] / frames["silence"][i]["file"]
        ):
            raise ValueError("Teaching and silence robot-prefix camera bytes differ")
    if sha(views["teach"] / frames["teach"][-1]["file"]) == sha(
        views["silence"] / frames["silence"][-1]["file"]
    ):
        raise ValueError("No observable final-state difference")
    write_json(private / "teaching-trace.json", trace)
    return dict(
        frame_count=len(trace),
        shared_rgb_prefix_frames=split,
        robot_final_xyz=placed,
        corrected_final_xyz=corrected,
        teaching_visibility=visibility,
        robot_peak_error_m=play.peak_error,
        silence_method="Render the same-length idle interval with natural breathing; both hands remain at their rest targets and the token stays in the amber tray.",
    )


def heldout(public):
    scene, case, dest = build(True)
    play = Playback(scene, FPS)
    with frame_reader(CYCLES, scene, play, SETTINGS) as read:
        next(play.pause(0.1))
        image = read()
    visibility = geometry_check(play, dest, image)
    for key, task in (("fork", case.command), ("control", CONTROL)):
        folder = public / key
        folder.mkdir()
        frames = [snapshot(folder, 0, image)]
        packet(folder, task, frames, OPTIONS)
    if sha(public / "fork/i000.jpg") != sha(public / "control/i000.jpg"):
        raise ValueError("Fork/control should use the same observation")
    return visibility


def generate(out):
    with new_directory(out) as stage:
        public, private = stage / "public", stage / "private"
        public.mkdir()
        private.mkdir()
        physical = teaching(public, private)
        physical["heldout_visibility"] = heldout(public)
        profiles = {
            key: dict(
                brief=brief,
                teaching="teach",
                no_reaction="silence",
                expected={"fork": "A" if key == "color" else "B", "control": "B"},
            )
            for key, brief in BRIEFS.items()
        }
        reproduction = (
            "MUJOCO_GL=egl uv run --no-project --python 3.11 --with 'bpy==4.3.0' "
            "--with 'numpy<2' --with 'mujoco==4.0.1' --with pillow --with imageio-ffmpeg "
            "python -m visual_prefs.locked_trays " + shlex.quote(str(out))
        )
        manifest = dict(
            version=1,
            profiles=profiles,
            feature_mapping={
                "teach": {"person_left": "teal", "person_right": "amber"},
                "fork_and_control": {"person_left": "amber", "person_right": "teal"},
            },
            design="Both private briefs reference the same immutable teaching packet. No actor inputs vary by profile. The person silently moves the single neutral token after the robot has withdrawn. The held-out fork crosses the two possible explanations. The control explicitly requests amber; the location rule and requested color coincide there.",
            packet_access="The experiment reader attaches only camera bytes, public task/options, times and transcript. Directory names, media names, private keys, render logs and manifest are evaluator metadata.",
            packet_sha256={
                str(p.relative_to(stage)): sha(p) for p in sorted(public.rglob("*")) if p.is_file()
            },
            physical_audit=physical,
            run=dict(
                reproduce=reproduction,
                fps=FPS,
                size=SIZE,
                renderer=cycles_provenance(12, "CPU"),
                assets=asset_hashes(),
                revision=revision(),
                module_sha256=sha(Path(__file__)),
            ),
        )
        write_json(private / "manifest.json", manifest)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    generate(parser.parse_args().destination.resolve())
