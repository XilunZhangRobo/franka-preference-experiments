"""Rendered robot-camera visibility QA for the standard paused-work stimulus.

Development criteria at 480x360: during start, end, and the teaching undo,
at least 65% of each isolated silhouette should remain visible, with at least
50 visible clip pixels and 500 visible mat pixels. During human grasp/transport
the clip and moved mat may fall to 35% and half the footprint. Robot approach
and grasp are diagnostic only. These thresholds describe selected rendered
frames; they do not establish physical calibration or human recognizability.
"""

import mujoco
import numpy as np

from . import paused
from .playback import Playback
from .scene import Scene


def _label_clip(scene, active):
    parts = scene.mat_parts[active].clip
    for i, geom in enumerate(parts):
        geom.set("name", f"visibility_clip_{i}")
    return len(parts)


def _snapshots(play, case, phase):
    data = play.data
    states = {}
    steps = play.play(case, case.default, correct=True) if phase == "teach" else play.pause(0.01)
    for sample in steps:
        key = (
            {"reach": "robot_approach", "grasp": "robot_grasp"}.get(sample.action)
            if sample.actor == "robot"
            else None
        )
        if sample.actor.startswith("human"):
            key = {"grasp": "human_contact", "transport": "human_undo"}.get(sample.action)
        if sample.index == 0:
            key = "start"
        elif sample.actor == "idle" and "human_undo" in states:
            key = "end"
        if key:
            states.setdefault(key, []).append(
                (sample, data.qpos.copy(), data.mocap_pos.copy(), data.mocap_quat.copy())
            )
    return {
        key: samples[-1 if key in ("end", "human_contact", "robot_grasp") else len(samples) // 2]
        for key, samples in states.items()
    }


def _audit_phase(seed, phase, camera_pose):
    scene = Scene("sewing" if phase == "transfer" else "workroom")
    case = paused.build(scene, phase, seed)
    if camera_pose:
        scene.world.remove(scene.world.find("camera[@name='agent']"))
        scene.camera("agent", *camera_pose)
    active = case.default
    clip_parts = _label_clip(scene, active)
    play = Playback(scene, fps=18)
    model = play.model
    masks = {
        name: np.flatnonzero((model.geom_bodyid == model.body(name).id) & (model.geom_group != 3))
        for name in ("near", "far")
    }
    masks["clip"] = np.array([model.geom(f"visibility_clip_{i}").id for i in range(clip_parts)])
    # Assign three private render groups on this audit-only copy of the model.
    # Group 3 is the invisible Panda collision geometry in normal recording.
    model.geom_group[model.geom_group != 3] = 0
    for group, name in ((1, "near"), (2, "far"), (4, "clip")):
        model.geom_group[masks[name]] = group
    robot_ids = np.flatnonzero(model.body_rootid[model.geom_bodyid] == model.body("link0").id)
    width, height = 480, 360
    frames = {}
    with mujoco.Renderer(model, height=height, width=width) as renderer:
        renderer.enable_segmentation_rendering()

        def raster(groups, skins):
            options = mujoco.MjvOption()
            options.geomgroup[:] = 0
            options.geomgroup[groups] = 1
            options.flags[mujoco.mjtVisFlag.mjVIS_SKIN] = skins
            renderer.update_scene(play.data, camera="agent", scene_option=options)
            return renderer.render()

        for key, (sample, qpos, pos, quat) in _snapshots(play, case, phase).items():
            play.data.qpos[:] = qpos
            play.data.mocap_pos[:] = pos
            play.data.mocap_quat[:] = quat
            mujoco.mj_forward(model, play.data)
            full = raster([0, 1, 2, 4], True)
            objects = {}
            for name, ids in masks.items():
                whole = name in ("near", "far")
                groups = [1 if name == "near" else 2] if whole else []
                if name in (active, "clip"):
                    groups.append(4)
                alone = raster(groups, False)
                geom = int(mujoco.mjtObj.mjOBJ_GEOM)
                silhouette = (alone[..., 1] == geom) & np.isin(alone[..., 0], ids)
                inside = full[silhouette]
                is_geom = inside[:, 1] == geom
                visible = int(np.count_nonzero(is_geom & np.isin(inside[:, 0], ids)))
                area = len(inside)
                robot = int(np.count_nonzero(is_geom & np.isin(inside[:, 0], robot_ids)))
                skin = int(np.count_nonzero(inside[:, 1] == int(mujoco.mjtObj.mjOBJ_SKIN)))
                same_mat = (
                    0
                    if whole
                    else int(
                        np.count_nonzero(
                            is_geom & np.isin(inside[:, 0], np.setdiff1d(masks[active], ids))
                        )
                    )
                )
                ratio = visible / area if area else 0.0
                min_pixels, min_ratio = (500 if whole else 50), 0.65
                if key.startswith("human") and name in (active, "clip"):
                    min_pixels //= 2
                    min_ratio = 0.35
                tested = not key.startswith("robot")
                objects[name] = {
                    "visible_px": visible,
                    "isolated_px": area,
                    "visible_fraction": round(ratio, 4),
                    "occluded_px": {
                        "robot": robot,
                        "human_skin": skin,
                        "same_mat": same_mat,
                        "other": area - visible - robot - skin - same_mat,
                    },
                    "minimum_px": min_pixels if tested else None,
                    "minimum_fraction": min_ratio if tested else None,
                    "passed": visible >= min_pixels and ratio >= min_ratio if tested else None,
                }
            frames[key] = {"frame": sample.index, "objects": objects}
    return {"layout_seed": seed, "active_mat": active, "frames": frames}


def audit_visibility(seed, *, camera_pose=None):
    """Return teach + transfer masks/criteria from the same layout seeds as record().

    camera_pose optionally replaces the source camera with (eye, look_at, fovy)
    for controlled comparisons. Transfer consists only of its decision frame.
    """
    phases = {
        p: _audit_phase(seed + offset, p, camera_pose)
        for p, offset in (("teach", 0), ("transfer", 103))
    }
    passed = all(
        obj["passed"] is not False
        for phase in phases.values()
        for frame in phase["frames"].values()
        for obj in frame["objects"].values()
    )
    return {"seed": seed, "size": [480, 360], "passed": passed, "phases": phases}
