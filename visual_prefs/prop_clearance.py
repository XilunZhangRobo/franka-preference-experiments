"""Sample paused-work playback against Panda colliders and the skinned hands.

Run with python -m visual_prefs.prop_clearance. Mesh distances use MuJoCo's
convex hull for each individual geom. Hand tests use a conservative oriented
box around each geom. Both can flag gaps within hollow objects. Positive
separation is required; an unreported pair is outside the 70 mm robot or
15 mm hand broad-phase window. These are sampled poses, not continuous
collision or grasp force measurements.
"""

import argparse
import json

import mujoco
import numpy as np

from .avatar import _load
from .human_qa import _triangle_box_gaps
from .playback import Playback
from .study import scene_for


def _parts(scene):
    labels = {}
    for mat, parts in scene.mat_parts.items():
        index = {geom: i for i, geom in enumerate(scene.props[mat].findall("geom"))}
        for category, geoms in (
            ("cargo", parts.cargo_visuals),
            ("ticket", parts.ticket),
            ("clip", parts.clip),
        ):
            for geom in geoms:
                n = index[geom]
                name = f"clearance_{mat}_{n}"
                geom.set("name", name)
                labels[name] = (category, f"{mat}/{geom.get('mesh', geom.get('type'))}/{n}")
    return labels


def _record(records, category, distance, frame, obstacle, effector):
    if category not in records or distance < records[category]["gap_m"]:
        records[category] = dict(
            gap_m=float(distance),
            frame=frame.index,
            actor=frame.actor,
            action=frame.action,
            obstacle=obstacle,
            effector=effector,
        )


def trial(seed, phase, choice, fps, *, misplaced=False):
    scene, case = scene_for("paused-work", phase, seed, None)
    choice = choice or case.default
    labels = _parts(scene)
    if misplaced:
        # Put a solid cargo part directly in the robot's route to the pinch point.
        geom = scene.box(scene.props[choice], (0, -0.061, 0.064), (0.04, 0.04, 0.055), "#8e7361")
        geom.set("name", "control")
        labels["control"] = ("control", f"{choice}/misplaced-block")
    pb = Playback(scene, fps)
    m, d = pb.model, pb.data
    panda = np.flatnonzero(m.geom_contype)
    objects = np.array([m.geom(name).id for name in labels])
    categories, names = zip(*labels.values())
    skin = mujoco.MjvScene(m, maxgeom=m.ngeom + 50)
    camera, opts = mujoco.MjvCamera(), mujoco.MjvOption()
    rig = _load()[0]
    bones = np.concatenate(
        [scene.avatar.family[scene.avatar.joints[k + "_hand"]] for k in ("right", "left")]
    )
    hand_faces = rig["triangles"][np.isin(rig["joints"][:, 0], bones)[rig["triangles"]].any(axis=1)]
    robot, hands = {}, {}
    for frame in pb.play(case, choice, correct=True, visible=True):
        delta = d.geom_xpos[panda, None, :] - d.geom_xpos[objects][None, :, :]
        lower = np.linalg.norm(delta, axis=2) - m.geom_rbound[panda, None] - m.geom_rbound[objects]
        for i, j in zip(*np.where(lower < 0.07)):
            gid = panda[i]
            value = mujoco.mj_geomDistance(m, d, gid, objects[j], 0.07, None)
            _record(
                robot,
                categories[j],
                value,
                frame,
                names[j],
                f"{m.body(m.geom_bodyid[gid]).name}/geom{gid}",
            )
        mujoco.mjv_updateScene(m, d, opts, None, camera, mujoco.mjtCatBit.mjCAT_ALL, skin)
        triangles = skin.skinvert.reshape(-1, 3)[hand_faces]
        low, high = triangles.min(axis=1), triangles.max(axis=1)
        for j, gid in enumerate(objects):
            center, half = m.geom_aabb[gid, :3], m.geom_aabb[gid, 3:]
            rotation = d.geom_xmat[gid].reshape(3, 3)
            origin = d.geom_xpos[gid] + rotation @ center
            extent = np.abs(rotation) @ half
            margin = 0.015
            nearby = ((low <= origin + extent + margin) & (high >= origin - extent - margin)).all(
                axis=1
            )
            if nearby.any():
                local = (triangles[nearby] - origin) @ rotation
                gap = _triangle_box_gaps(local, half).min()
                _record(hands, categories[j], gap, frame, names[j], "hand triangles")
    nominal = [
        value["gap_m"]
        for group in (robot, hands)
        for key, value in group.items()
        if key != "control"
    ]
    passed = all(gap > 0 for gap in nominal)
    if misplaced:
        passed = passed and robot.get("control", {}).get("gap_m", 0) < 0
    return dict(
        passed=passed,
        misplaced=misplaced,
        seed=seed,
        phase=phase,
        choice=choice,
        fps=fps,
        frames=frame.index + 1,
        panda=robot,
        hands=hands,
    )


def layout_trials(seed, fps, *, bundle=False):
    """Exercise both action choices through the teaching, transfer and exception scenes."""
    for phase, offset, choices in (
        ("teach", 0, ("near", "far")),
        ("transfer", 103, ("near", "far")),
        ("exception", 206, ("organizer", "case")),
    ):
        for choice in choices:
            row = trial(seed + offset if bundle else seed, phase, choice, fps)
            if bundle:
                row["bundle_seed"] = seed
            yield row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fps", type=int, default=24)
    parser.add_argument("--seeds", nargs="+", type=int, default=[0, 1])
    parser.add_argument(
        "--bundle-seeds",
        action="store_true",
        help="apply record()'s +103 per phase layout-seed offset",
    )
    parser.add_argument("--control", action="store_true")
    args = parser.parse_args()
    passed = True
    for seed in args.seeds:
        for row in layout_trials(seed, args.fps, bundle=args.bundle_seeds):
            print(json.dumps(row), flush=True)
            passed &= row["passed"]
    if args.control:
        row = trial(0, "teach", "near", args.fps, misplaced=True)
        print(json.dumps(row), flush=True)
        passed &= row["passed"]
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
