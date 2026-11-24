"""Dynamic contact QA for the kinematically rendered paused-work stimulus.

Reuses the builder's collision envelopes and Playback.move transport profile. A compliant
weld prescribes the mat pose, not the individual cargo poses. It is disabled
for settling. This companion model does not measure video forces or validate
grasp closure, human strength, or Panda link collision clearance.
"""

import copy
import xml.etree.ElementTree as ET

import mujoco
import numpy as np

from . import paused
from .episode import carry_clearance
from .playback import ease
from .scene import Scene, fmt


class _Fixture(Scene):
    """Run the visual builder without loading render meshes or the avatar."""

    def __init__(self):
        self.world = ET.Element("worldbody")
        self.props, self.grasps, self.human_grasps = {}, {}, {}

    def rest_hand(self, side, xyz):
        pass

    def person(self):
        pass


LIMITS = {
    "max_cargo_slip_m": 0.008,
    "max_table_penetration_m": 0.0015,
    "max_shelf_penetration_m": 0.002,
    "max_landing_xy_error_m": 0.008,
    "max_settled_linear_speed_m_s": 0.01,
    "max_settled_angular_speed_rad_s": 0.10,
    "min_footprint_support_fraction": 0.98,
}


def _collider(geom, name=None):
    geom = copy.deepcopy(geom)
    geom.attrib.update(contype="1", conaffinity="1")
    if name:
        geom.set("name", name)
    return geom


def _arr(element, key):
    return np.fromstring(element.get(key), sep=" ")


def _assemble(seed, phase, item, reverse):
    scene = _Fixture()
    case = paused.build(scene, phase, seed)
    root = ET.Element("mujoco")
    ET.SubElement(
        root,
        "option",
        timestep=".001",
        gravity="0 0 -9.81",
        integrator="implicitfast",
        iterations="80",
    )
    default = ET.SubElement(root, "default")
    ET.SubElement(
        default,
        "geom",
        friction=".60 .004 .0001",
        density="650",
        solref=".006 1",
        solimp=".95 .99 .001",
        condim="4",
    )
    world = ET.SubElement(root, "worldbody")
    # Same finite tabletop dimensions and offset as Scene.__init__.
    ET.SubElement(
        world,
        "geom",
        name="table",
        type="box",
        pos=fmt(scene.tabletop_center),
        size=fmt(np.asarray(scene.tabletop_size) / 2),
    )
    ET.SubElement(world, "geom", name="floor", type="plane", size="2 2 .02")
    static = scene.world.findall("geom")
    for i, geom in enumerate(static):
        world.append(_collider(geom, "shelf" if i == 0 else f"support{i}"))
    origin = _arr(scene.props[item], "pos")
    shelf = np.array(case.robot[item][0].target)
    start, goal = (shelf, origin) if reverse else (origin, shelf)
    for key, prop in scene.props.items():
        if key != item:
            fixed = ET.SubElement(world, "body", pos=prop.get("pos"))
            if key in scene.mat_parts:
                other = scene.mat_parts[key]
                geoms = [other.base, *other.attached, *(g for group in other.loose for g in group)]
            else:
                geoms = prop.findall("geom")
            for geom in geoms:
                fixed.append(_collider(geom))
    mat = ET.SubElement(world, "body", name="mat", pos=fmt(start))
    ET.SubElement(mat, "freejoint")
    parts = scene.mat_parts[item]
    mat.append(_collider(parts.base, "base"))
    half_size = _arr(parts.base, "size")[:2]
    groups = parts.loose
    for geom in parts.attached:
        mat.append(_collider(geom))
    for i, group in enumerate(groups):
        center = _arr(group[0], "pos")
        cargo = ET.SubElement(world, "body", name=f"cargo{i}", pos=fmt(start + center))
        ET.SubElement(cargo, "freejoint")
        for g in group:
            geom = _collider(g)
            geom.set("pos", fmt(_arr(g, "pos") - center))
            cargo.append(geom)
    ET.SubElement(world, "body", name="carrier", mocap="true", pos=fmt(start))
    weld = ET.SubElement(root, "equality")
    ET.SubElement(
        weld,
        "weld",
        body1="carrier",
        body2="mat",
        solref=".003 1",
        solimp=".97 .995 .001",
        torquescale=".12",
    )
    return (
        mujoco.MjModel.from_xml_string(ET.tostring(root, encoding="unicode")),
        start,
        goal,
        half_size,
        _arr(static[0], "size")[:2],
        len(groups),
    )


def _trial(seed, phase, item, reverse=False, duration_scale=1.0, arc_override=None, offset_x=0.0):
    model, start, goal, mat_size, _, n = _assemble(seed, phase, item, reverse)
    goal = goal.copy()
    goal[0] += offset_x
    arc = carry_clearance(item, goal - start) if arc_override is None else arc_override
    data = mujoco.MjData(model)
    mat = model.body("mat").id
    ids = [model.body(f"cargo{i}").id for i in range(n)]
    base = model.geom("base").id
    receivers = {model.geom("shelf").id: "shelf", model.geom("table").id: "table"}
    depth = {"shelf": 0.0, "table": 0.0}
    for _ in range(200):
        mujoco.mj_step(model, data)

    def relative():
        return (data.xpos[ids] - data.xpos[mat]) @ data.xmat[mat].reshape(3, 3)

    rest = relative()
    slip = 0.0
    duration = duration_scale * (0.42 + 1.7 * np.linalg.norm(goal - start))
    seconds = model.opt.timestep
    steps = int(np.ceil(duration / seconds))
    receiver = "table" if reverse else "shelf"
    last_support = set()
    supported_cargo = set()
    for i in range(steps + 850):
        if i < steps:
            t = ease((i + 1) / steps)
            pos = start + t * (goal - start)
            pos[2] += arc * 4 * t * (1 - t)
            data.mocap_pos[0] = pos
        elif i == steps + 180:
            data.eq_active[0] = False
        mujoco.mj_step(model, data)
        slip = max(slip, float(np.linalg.norm((relative() - rest)[:, :2], axis=1).max()))
        last_support = set()
        supported_cargo = set()
        for c in data.contact:
            a, b = c.geom
            for g, other in ((a, b), (b, a)):
                if g == base and model.geom_bodyid[other] in ids and c.dist <= 0.0002:
                    supported_cargo.add(model.geom_bodyid[other])
                if g in receivers and model.geom_bodyid[other] in [mat, *ids]:
                    surface = receivers[g]
                    depth[surface] = max(depth[surface], float(-c.dist))
                    if other == base and c.dist <= 0.0002:
                        last_support.add(surface)
    delta = abs(data.xpos[mat, :2] - goal[:2])
    # Report projected overlap for the level shelf. Model also needs physical
    # base/surface contact at rest; on the table the support plane is continuous.
    edges = np.array(
        [[x, y, 0.0] for x in (-mat_size[0], mat_size[0]) for y in (-mat_size[1], mat_size[1])]
    )
    corners = (edges @ data.xmat[mat].reshape(3, 3).T + data.xpos[mat])[:, :2]
    low, high = corners.min(0), corners.max(0)
    surface = model.geom(receiver).id
    center = data.geom_xpos[surface, :2]
    surface_size = model.geom_size[surface, :2]
    overlap = np.maximum(
        0, np.minimum(high, center + surface_size) - np.maximum(low, center - surface_size)
    )
    support = float(np.prod(overlap) / np.prod(high - low))
    vel = data.qvel.reshape(-1, 6)
    speed = float(np.linalg.norm(vel[:, :3], axis=1).max())
    angular = float(np.linalg.norm(vel[:, 3:], axis=1).max())
    relative_final = relative()
    inside = bool(
        np.all(np.abs(relative_final[:, :2]) <= mat_size) and np.all(relative_final[:, 2] > 0)
    )
    checks = {
        "correct_surface_in_contact": receiver in last_support,
        "cargo_centers_remain_on_mat": inside,
        "all_cargo_in_contact_with_mat_at_rest": len(supported_cargo) == n,
        "slip_within_limit": slip <= LIMITS["max_cargo_slip_m"],
        "table_penetration_within_limit": depth["table"] <= LIMITS["max_table_penetration_m"],
        "shelf_penetration_within_limit": depth["shelf"] <= LIMITS["max_shelf_penetration_m"],
        "adequate_support": support >= LIMITS["min_footprint_support_fraction"],
        "landing_on_target": float(np.linalg.norm(delta)) <= LIMITS["max_landing_xy_error_m"],
        "settled": speed <= LIMITS["max_settled_linear_speed_m_s"]
        and angular <= LIMITS["max_settled_angular_speed_rad_s"],
    }
    return {
        "phase": phase,
        "item": item,
        "target_surface": receiver,
        "duration_s": duration,
        "cargo_count": n,
        "peak_horizontal_cargo_slip_m": slip,
        "peak_penetration_m": depth,
        "landing_xy_error_m": float(np.linalg.norm(delta)),
        "footprint_support_fraction": support,
        "final_peak_linear_speed_m_s": speed,
        "final_peak_angular_speed_rad_s": angular,
        "checks": checks,
        "passed": all(checks.values()),
    }


def audit_contact(seed):
    trials = [
        _trial(seed, phase, item) for phase in ("teach", "transfer") for item in ("near", "far")
    ]
    fixture = _Fixture()
    marked = paused.build(fixture, "teach", seed).default
    trials.append(_trial(seed, "teach", marked, reverse=True))
    negative = _trial(seed, "transfer", "far", duration_scale=0.22)
    short_arc = _trial(seed, "teach", "near", arc_override=0.045)
    overhang = _trial(seed, "transfer", "far", offset_x=0.073)
    controls = {
        "low_arc": {
            "intervention": "45 mm arc",
            "trial": short_arc,
            "detected": not short_arc["checks"]["shelf_penetration_within_limit"],
        },
        "overhang": {
            "intervention": "place 73 mm off shelf center",
            "trial": overhang,
            "detected": not overhang["checks"]["adequate_support"],
        },
    }
    return {
        "seed": seed,
        "engine": "MuJoCo " + mujoco.__version__,
        "thresholds": dict(LIMITS),
        "scope": "Dynamic gravity, collision, friction and settling for transported mats and loose cargo. "
        "The carrier follows the continuous playback arc; its weld substitutes for the grasp. "
        "This companion simulation does not measure video contact forces or robot-link clearance.",
        "parameters": {
            "timestep_s": 0.001,
            "uniform_density_kg_m3": 650,
            "sliding_friction": 0.6,
            "release_hold_s": 0.18,
            "free_settling_s": 0.67,
        },
        "trials": trials,
        "negative_control": {
            "intervention": "22% of normal carry duration",
            "trial": negative,
            "detected": not negative["checks"]["slip_within_limit"],
        },
        "additional_controls": controls,
        "passed": all(t["passed"] for t in trials)
        and not negative["checks"]["slip_within_limit"]
        and all(c["detected"] for c in controls.values()),
    }


def audit_robot_clearance(seed, phase="teach", fps=24):
    """Measure signed collision-geometry distances at the original playback frames.

    Requires installed Panda assets. Checks moving Panda links against the
    tabletop, shelf top and legs. Excludes fixed base, intentionally grasped
    props, other scene geometry, and unsampled between-frame configurations.
    """
    from .playback import Playback

    scene = Scene()
    tabletop = scene.world.find("geom[@material='grain']")
    tabletop.set("name", "audit_table")
    before = len(scene.world.findall("geom"))
    case = paused.build(scene, phase, seed)
    added = scene.world.findall("geom")[before:]
    # person() also draws a chair; shelf and two supports are added last.
    for g, label in zip(added[-3:], ("top", "leg0", "leg1")):
        g.set("name", f"audit_shelf_{label}")
    rows = []
    for item in ("near", "far"):
        player = Playback(scene, fps=fps)
        m, d = player.model, player.data
        robot = [
            i
            for i in range(m.ngeom)
            if m.geom_contype[i]
            and m.body(m.geom_bodyid[i]).name
            in {
                "link1",
                "link2",
                "link3",
                "link4",
                "link5",
                "link6",
                "link7",
                "hand",
                "left_finger",
                "right_finger",
            }
        ]
        surfaces = [
            m.geom(f"audit_{s}").id for s in ("table", "shelf_top", "shelf_leg0", "shelf_leg1")
        ]
        minima = {m.geom(i).name: {"signed_distance_m": 0.20} for i in surfaces}
        frame_count = 0
        for sample in player.play(case, item, correct=(phase == "teach")):
            frame_count += 1
            for surface in surfaces:
                row = minima[m.geom(surface).name]
                for g in robot:
                    distance = mujoco.mj_geomDistance(m, d, g, surface, 0.20, None)
                    if distance < row["signed_distance_m"]:
                        row.update(
                            signed_distance_m=float(distance),
                            moving_link=m.body(m.geom_bodyid[g]).name,
                            frame=sample.index,
                            action=sample.action,
                        )
        rows.append(
            {
                "item": item,
                "frames": frame_count,
                "collision_geoms": len(robot),
                "minimum_distances": minima,
            }
        )
    minimum = min(m["signed_distance_m"] for r in rows for m in r["minimum_distances"].values())
    return {
        "seed": seed,
        "phase": phase,
        "fps": fps,
        "sampled_trajectories": rows,
        "minimum_signed_distance_m": minimum,
        "passed": minimum >= 0.001,
        "threshold_m": 0.001,
    }
