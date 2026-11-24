"""An undone robot action can teach a preference without demonstrating its replacement."""

import xml.etree.ElementTree as ET
from dataclasses import dataclass, replace
from random import Random

from . import bench_cargo, project_clip
from .episode import Case, Motion
from .work_surface import work_surface


@dataclass
class MatParts:
    base: ET.Element
    loose: list[list[ET.Element]]  # One group of collision envelopes per loose item.
    attached: list[ET.Element]
    cargo_visuals: list[ET.Element]
    ticket: list[ET.Element]
    clip: list[ET.Element]


def workmat(s, name, pos, color, sewing, clipped):
    b = s.prop(name, pos)
    base = work_surface(s, b, color, sewing)
    start_cargo = len(b)
    loose = bench_cargo.sewing_supplies(s, b) if sewing else bench_cargo.workshop_parts(s, b)
    card_x = -s.cargo_layout_side * 0.050
    start_ticket = len(b)
    upright = project_clip.job_ticket(s, b, card_x)
    start_clip = len(b)
    attached = [upright]
    if clipped:
        project_clip.clip(s, b, card_x)
        # The contact model treats the closed spring as attached to its ticket.
        # Its steel body dominates the mass; the wire handles are visual detail.
        attached.append(
            s.box(
                ET.Element("body"),
                (card_x, project_clip.CARD_Y + 0.002, project_clip.JAW_Z + 0.010),
                (0.041, 0.014, 0.019),
                "#26292a",
            )
        )
    visuals = list(b)
    s.mat_parts[name] = MatParts(
        base=base,
        loose=loose,
        attached=attached,
        cargo_visuals=visuals[start_cargo:start_ticket],
        ticket=visuals[start_ticket:start_clip],
        clip=visuals[start_clip:],
    )
    s.grasp(name, (0, -0.061, 0.014))
    s.human_grasps[name] = (s.cargo_layout_side * 0.083, 0.043, 0.025)


def build(s, phase, seed):
    s.mat_parts = {}
    s.cargo_layout_seed = seed // 2
    s.person()
    rng = Random(seed)
    side = rng.choice((-1, 1))
    s.cargo_layout_side = side
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
        bench_cargo.closed_kit(s, kit)
        s.grasp("case", (0, 0, 0.017))
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
