"""An undone robot action can teach a preference without demonstrating its replacement."""

from dataclasses import dataclass, replace
from random import Random

from .episode import Case, Motion

METAL = "#b7c1c5"


@dataclass
class MatParts:
    base: object
    loose: list
    clip: list


def binder_clip(s, b, x=0.064, y=-0.049):
    # Spring body and the two bent wire handles of a foldback binder clip.
    s.box(b, (x, y, 0.017), (0.044, 0.022, 0.019), "#23292c")
    for side in (-1, 1):
        by = y + side * 0.010
        tip = by + side * 0.008
        for sign in (-1, 1):
            s.rod(b, (x + sign * 0.018, by, 0.023), (x + sign * 0.013, tip, 0.052), 0.0024, METAL)
        s.rod(b, (x - 0.013, tip, 0.052), (x + 0.013, tip, 0.052), 0.0024, METAL)


def workmat(s, name, pos, color, sewing, clipped):
    b = s.prop(name, pos)
    base = s.box(b, (0, 0, 0.003), (0.185, 0.141, 0.006), color)
    loose = []
    if sewing:
        for i in range(-7, 8):
            s.box(b, (i * 0.012, 0, 0.0063), (0.0008, 0.133, 0.0005), "#bdc9b1")
        for i in range(-5, 6):
            s.box(b, (0, i * 0.012, 0.0063), (0.177, 0.0008, 0.0005), "#bdc9b1")
        for x in (-0.036, 0.021):
            spool = [s.cyl(b, (x, 0.015, 0.018), 0.013, 0.023, "#d5aa83")]
            for z in (0.008, 0.030):
                spool.append(s.cyl(b, (x, 0.015, z), 0.017, 0.004, "#e7dabd"))
            loose.append(spool)
        loose.append([s.box(b, (-0.021, -0.03, 0.0095), (0.071, 0.039, 0.006), "#a2637a")])
    else:
        loose.append(
            [
                s.box(b, (-0.012, 0.012, 0.012), (0.085, 0.052, 0.013), "#d0ba97"),
                s.box(b, (-0.026, 0.022, 0.029), (0.052, 0.012, 0.022), "#4a6170"),
            ]
        )
        for x, y in ((-0.058, -0.035), (0.012, -0.027), (0.048, 0.038)):
            loose.append(
                [
                    s.cyl(b, (x, y, 0.011), 0.009, 0.010, METAL),
                    s.box(b, (x, y, 0.0164), (0.012, 0.002, 0.0008), "#33424b"),
                ]
            )
    start_clip = len(b)
    if clipped:
        binder_clip(s, b)
    s.mat_parts[name] = MatParts(base, loose, list(b)[start_clip:])
    s.grasp(name, (0, -0.061, 0.014))
    s.human_grasps[name] = (0, 0.045, 0.025)


def build(s, phase, seed):
    s.mat_parts = {}
    s.person()
    rng = Random(seed)
    side = rng.choice((-1, 1))
    colors = [("teal", "#316f72"), ("rust", "#a35e49")]
    rng.shuffle(colors)
    z = s.table_z
    shelf = (side * 0.137, 0.182, z + 0.082)
    s.box(s.world, (shelf[0], shelf[1], shelf[2] - 0.007), (0.212, 0.160, 0.014), "#b49b73")
    for dx in (-0.095, 0.095):
        s.box(s.world, (shelf[0] + dx, shelf[1], z + 0.034), (0.014, 0.145, 0.068), "#444f54")
    starts = [(side * 0.139, -0.052, z), (-side * 0.139, -0.091, z)]
    # Cross clip/distance independently from color and mirror the bench. Pair
    # seeds 0/1, 2/3, ... for both assignments rather than rewarding "move far".
    marked = seed % 2
    for hand, dx in (("right", -0.31), ("left", 0.31)):
        s.rest_hand(hand, (dx, 0.105, z + 0.039))
    pencil = s.prop("pencil", (0, -0.208, z))
    s.rod(pencil, (-0.042, 0, 0.004), (0.042, 0, 0.004), 0.004, "#c19842")
    if phase == "exception":
        kit = s.prop("case", starts[0])
        s.box(kit, (0, 0, 0.017), (0.164, 0.098, 0.034), "#6a7978")
        s.box(kit, (0, 0, 0.035), (0.167, 0.102, 0.010), "#adb6a3")
        s.box(kit, (0.0, -0.051, 0.024), (0.027, 0.010, 0.017), "#959e9d")
        workmat(s, "organizer", starts[1], colors[1][1], True, False)
        return Case(
            "Free a bench spot for a new project.",
            {
                "case": "Shelve the closed stitching kit.",
                "organizer": "Shelve the loose organizer.",
            },
            "case",
            "organizer",
            {
                "case": [Motion("robot", "case", shelf)],
                "organizer": [Motion("robot", "organizer", shelf)],
            },
            [],
        )
    sewing = phase == "transfer"
    for i, item in enumerate(("near", "far")):
        workmat(s, item, starts[i], colors[i][1], sewing, i == marked)
    command = (
        "Make room for the cutting board on my sewing counter."
        if sewing
        else "Clear a spot on my workbench."
    )
    options = {item: f"Shelve the {colors[i][0]} mat." for i, item in enumerate(("near", "far"))}
    misplaced, alternate = ("near", "far") if marked == 0 else ("far", "near")
    return Case(
        command,
        options,
        alternate,
        misplaced,
        {item: [Motion("robot", item, shelf)] for item in options},
        [Motion("human-left" if side > 0 else "human", misplaced, starts[marked])]
        if phase == "teach"
        else [],
        {"silent": "", "retry": "Try again.", "other": "No, the other mat."},
    )


BUILDERS = {"paused-work": build}


def reverse_preference(scene, case, phase):
    """Matched-scene control: this person clips the work they want put away."""
    if phase == "exception":
        return case
    name = case.expected
    start = tuple(float(v) for v in scene.props[name].get("pos").split())
    actor = case.human[0].actor if case.human else "human"
    return replace(
        case,
        expected=case.default,
        default=name,
        human=[Motion(actor, name, start)] if phase == "teach" else [],
    )
