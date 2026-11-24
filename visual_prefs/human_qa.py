"""Frame-sampled rendered human mesh and handover checks for the teaching episodes."""

import mujoco
import numpy as np

from . import handover, paused
from .avatar import _load
from .playback import Playback
from .scene import Scene

# Millimeter-scale surface tolerance for the kinematic mesh reconstruction.
MAX_PENETRATION_M = 0.0015
MAX_MEDIAN_GRASP_GAP_M = 0.002
MAX_GRASP_GAP_M = 0.012


def _box_margins(vertices, model, data, geom):
    local = (vertices - data.geom_xpos[geom]) @ data.geom_xmat[geom].reshape(3, 3)
    return model.geom_size[geom] - np.abs(local)


def _triangle_box_gaps(triangles, half):
    """Per-triangle signed separation bounds on the 13 triangle/box SAT axes.

    Positive is a lower bound on clearance. A negative result means the triangle
    overlaps the box on every axis. Inputs are triangles in box-local meters.
    """
    low, high = triangles.min(axis=1), triangles.max(axis=1)
    gap = np.maximum(low - half, -half - high).max(axis=1)
    # Axis-aligned bounds already certify all distant faces as disjoint.
    close = np.flatnonzero(gap < 0.045)
    if not close.size:
        return gap
    t = triangles[close]
    edges = t - np.roll(t, 1, axis=1)
    normal = np.cross(edges[:, 0], edges[:, 1])[:, None, :]
    edge_axes = np.cross(edges[:, :, None, :], np.eye(3)[None, None, :, :])
    axes = np.concatenate((normal, edge_axes.reshape(-1, 9, 3)), axis=1)
    length = np.linalg.norm(axes, axis=2)
    axes /= np.maximum(length[:, :, None], 1e-14)
    projection = np.einsum("nvi,nai->nva", t, axes)
    radius = np.abs(axes) @ half
    separations = np.maximum(projection.min(axis=1) - radius, -radius - projection.max(axis=1))
    separations[length < 1e-12] = -np.inf
    gap[close] = np.maximum(gap[close], separations.max(axis=1))
    return gap


def _summarize(samples):
    frames = np.asarray(samples)
    return {
        "frames": len(samples),
        "median_m": float(np.median(frames)),
        "p95_m": float(np.quantile(frames, 0.95)),
        "p99_m": float(np.quantile(frames, 0.99)),
        "max_m": float(frames.max()),
        "frames_over_limit": int((frames > MAX_PENETRATION_M).sum()),
    }


def _flagship(seed, fps):
    scene = Scene()
    scene.world.find("geom[@material='grain']").set("name", "qa_tabletop")
    before = set(scene.world.findall("geom"))
    case = paused.build(scene, "teach", seed)
    added = [g for g in scene.world.findall("geom") if g not in before]
    for g, name in zip(added, ("shelf", "shelf_foot_1", "shelf_foot_2"), strict=True):
        g.set("name", "qa_" + name)
    player = Playback(scene, fps)
    model, data = player.model, player.data
    faces = mujoco.MjvScene(model, maxgeom=model.ngeom + 50)
    options, camera = mujoco.MjvOption(), mujoco.MjvCamera()
    rig = _load()[0]
    bones = np.concatenate(
        [scene.avatar.family[scene.avatar.joints[side + "_hand"]] for side in ("left", "right")]
    )
    hand = np.isin(rig["joints"][:, 0], bones)
    working_side = "left" if case.human[0].actor == "human-left" else "right"
    working_bones = scene.avatar.family[scene.avatar.joints[working_side + "_hand"]]
    working_hand = np.isin(rig["joints"][:, 0], working_bones)
    arm_bones = np.concatenate(
        [
            scene.avatar.family[scene.avatar.joints[side + "_upper_arm"]]
            for side in ("left", "right")
        ]
    )
    arm_vertices = np.isin(rig["joints"][:, 0], arm_bones)
    fore_bones = np.concatenate(
        [
            np.setdiff1d(
                scene.avatar.family[scene.avatar.joints[side + "_forearm"]],
                scene.avatar.family[scene.avatar.joints[side + "_hand"]],
            )
            for side in ("left", "right")
        ]
    )
    fore_vertices = np.isin(rig["joints"][:, 0], fore_bones)
    face_ids = rig["triangles"]
    fore_faces = fore_vertices[face_ids].any(axis=1)
    surfaces = {
        name: model.geom("qa_" + name).id
        for name in ("tabletop", "shelf", "shelf_foot_1", "shelf_foot_2")
    }
    for item in ("near", "far"):
        surfaces[item + "_mat"] = int(model.body(item).geomadr[0])
    rows = {
        "all_frames_hands": {name: [] for name in surfaces},
        "all_frames_forearms": {name: [] for name in surfaces},
        "all_frames_arms_including_hands": {name: [] for name in surfaces},
        "all_frames_whole_body": {name: [] for name in surfaces},
        "initial_idle_whole_body": {name: [] for name in surfaces},
    }
    sat_rows = {
        name: {
            "intersection_frames": 0,
            "peak_intersecting_triangles": 0,
            "forearm_minimum_clearance_lower_bound_m": float("inf"),
        }
        for name in surfaces
    }
    flagged_frame = None
    panda = np.flatnonzero(model.geom_contype)
    initial_robot_clearance = float("inf")
    initial = True
    control = 0.0
    grip_gaps = []
    for frame in player.play(case, case.default, correct=True):
        mujoco.mjv_updateScene(
            model, data, options, None, camera, mujoco.mjtCatBit.mjCAT_ALL, faces
        )
        vertices = faces.skinvert.reshape(-1, 3)
        if frame.actor != "idle":
            initial = False
        for name, geom in surfaces.items():
            margins = _box_margins(vertices, model, data, geom)
            depths = np.maximum(0.0, margins.min(axis=1))
            if (
                name == case.default + "_mat"
                and frame.actor.startswith("human")
                and frame.action in ("grasp", "transport")
            ):
                outside = np.maximum(-margins[working_hand], 0.0)
                grip_gaps.append(float(np.linalg.norm(outside, axis=1).min()))
            rows["all_frames_hands"][name].append(float(depths[hand].max()))
            rows["all_frames_forearms"][name].append(float(depths[fore_vertices].max()))
            rows["all_frames_arms_including_hands"][name].append(float(depths[arm_vertices].max()))
            rows["all_frames_whole_body"][name].append(float(depths.max()))
            local = (vertices - data.geom_xpos[geom]) @ data.geom_xmat[geom].reshape(3, 3)
            gaps = _triangle_box_gaps(local[face_ids], model.geom_size[geom])
            row = sat_rows[name]
            hits = int((gaps < -1e-6).sum())
            row["intersection_frames"] += int(hits > 0)
            row["peak_intersecting_triangles"] = max(row["peak_intersecting_triangles"], hits)
            forearm_gap = float(gaps[fore_faces].min())
            if forearm_gap < row["forearm_minimum_clearance_lower_bound_m"]:
                row["forearm_minimum_clearance_lower_bound_m"] = forearm_gap
                row["forearm_closest_frame"] = frame.index
            if seed == 0 and fps == 18 and frame.index == 104 and name == "shelf":
                flagged_frame = {
                    "index": frame.index,
                    "action": frame.action,
                    "actor": frame.actor,
                    "forearm_clearance_lower_bound_m": forearm_gap,
                    "whole_body_intersecting_triangles": hits,
                }
            if initial:
                rows["initial_idle_whole_body"][name].append(float(depths.max()))
        if initial:
            # A sphere enclosing each posed triangle and each Panda collision
            # geom gives a conservative clearance bound, also between vertices.
            triangles = vertices[rig["triangles"]]
            centers = triangles.mean(axis=1)
            radii = np.linalg.norm(triangles - centers[:, None], axis=2).max(axis=1)
            for geom in panda:
                distances = np.linalg.norm(centers - data.geom_xpos[geom], axis=1)
                bound = np.min(distances - radii - model.geom_rbound[geom])
                initial_robot_clearance = min(initial_robot_clearance, float(bound))
            # An intentionally lowered neutral hand should intersect the actual
            # solid bench on the identical mesh and scene used for the nominal run.
            margins = _box_margins(
                vertices[hand] - (0, 0, 0.025), model, data, surfaces["tabletop"]
            )
            control = max(control, float(margins.min(axis=1).max()))
    summaries = {
        group: {name: _summarize(values) for name, values in row.items()}
        for group, row in rows.items()
    }
    nominal = all(
        v["max_m"] <= MAX_PENETRATION_M for group in summaries.values() for v in group.values()
    )
    median_gap = float(np.median(grip_gaps))
    grip_within_limit = median_gap <= MAX_MEDIAN_GRASP_GAP_M and max(grip_gaps) <= MAX_GRASP_GAP_M
    return {
        "seed": seed,
        "fps": fps,
        "hand_vertices": int(hand.sum()),
        "body_vertices": int(hand.size),
        "grasp_and_transport_closest_hand_to_mat_m": {
            "frames": len(grip_gaps),
            "median_m": median_gap,
            "max_allowed_median_m": MAX_MEDIAN_GRASP_GAP_M,
            "max_allowed_m": MAX_GRASP_GAP_M,
            "p95_m": float(np.quantile(grip_gaps, 0.95)),
            "max_m": max(grip_gaps),
        },
        "initial_idle_human_triangle_to_robot_clearance_lower_bound_m": initial_robot_clearance,
        "triangle_box_all_frames_whole_body": sat_rows,
        "reviewed_cycles_frame": flagged_frame,
        "forearm_triangles": int(fore_faces.sum()),
        "body_triangles": int(len(face_ids)),
        "measurements": summaries,
        "max_allowed_penetration_m": MAX_PENETRATION_M,
        "negative_control": {
            "intervention": "lower neutral hand skin 25 mm",
            "max_table_penetration_m": control,
            "detected": control > MAX_PENETRATION_M,
        },
        "passed": bool(
            nominal
            and all(row["intersection_frames"] == 0 for row in sat_rows.values())
            and grip_within_limit
            and control > MAX_PENETRATION_M
            and initial_robot_clearance > 0
        ),
    }


def _handover(seed, fps):
    rows = {}
    for family, builder in handover.BUILDERS.items():
        scene = Scene()
        case = builder(scene, "teach", seed)
        player = Playback(scene, fps)
        choices = case.robot[case.default]
        item = choices[0].item
        custody = []
        points = []
        for motion in [*choices, *case.human]:
            for frame in player.move(motion):
                if frame.action == "point":
                    points.append(player.data.mocap_pos[player.ids[item]].copy())
            custody.append(player.holders.get(item))
        stationary = float(np.linalg.norm(np.ptp(points, axis=0))) if points else None
        if family == "receiving-hand":
            passed = custody == ["robot", "human", "human-left"]
        else:
            passed = custody == ["robot", "robot", "robot"] and bool(points) and stationary <= 1e-6
        rows[family] = {
            "item": item,
            "holders_after_actions": custody,
            "point_frames": len(points),
            "point_item_displacement_m": stationary,
            "peak_robot_ik_error_m": player.peak_error,
            "passed": passed,
        }
    return rows


def audit_human(seed=0, fps=24):
    """Return a JSON-serializable check from compiled MuJoCo skin vertices."""
    flagship = _flagship(seed, fps)
    transfers = _handover(seed, fps)
    return {
        "flagship": flagship,
        "handover_teaching": transfers,
        "method": "MuJoCo mjv_updateScene, vertex depth inside oriented solid boxes. "
        "Quantiles summarize each frame's deepest vertex. Initial idle samples use the "
        "whole body; all frames measure hands, forearms, full arms and the whole body. "
        "Separate triangle/box SAT tests cover every skinned triangle including faces crossing "
        "a box without an interior vertex; forearm triangles touch at least one dominant forearm vertex.",
        "exclusions": [
            "between-frame configurations and intersections shallower than one micrometer in SAT",
            "self-intersection, robot/human intersection during movement, chair, room cabinetry and loose cargo",
            "grip forces and friction, and non-flagship mesh clearance",
            "handover custody checks track controller state and the prop trajectory, not force closure",
        ],
        "passed": flagship["passed"] and all(row["passed"] for row in transfers.values()),
    }
