"""Handover choices in the seated recipient's frame of reference."""

from math import copysign, cos, pi, radians, sin
from random import Random

from .episode import Case, Motion
from .prop_mesh import surface


def _shell(scene, body, name, rings, color, *, shape=1, finish="matte", wave=0):
    """Circular sections for a cup or light; superellipses for cloth or a remote."""
    sections = []
    for z, rx, ry in rings:
        outline = []
        for j in range(64):
            angle = 2 * pi * j / 64
            x, y = cos(angle), sin(angle)
            outline.append(
                (
                    rx * copysign(abs(x) ** shape, x),
                    ry * copysign(abs(y) ** shape, y),
                    z + wave * (sin(3 * angle + 0.3) + 0.5 * cos(5 * angle)),
                )
            )
        sections.append(outline)
    return surface(scene, body, name, (0, 0, 0), sections, color, finish=finish)


def _object(scene, item, position):
    body = scene.prop(item, position)
    # Preserve the original pinch heights independently of decorative geometry.
    scene.grasp(
        item, (0, 0, {"flashlight": 0.035, "remote": 0.012, "tumbler": 0.046, "cloth": 0.009}[item])
    )
    if item == "flashlight":
        profile = [
            (0, 0.016),
            (0.003, 0.018),
            (0.053, 0.018),
            (0.060, 0.020),
            (0.073, 0.028),
            (0.086, 0.028),
            (0.088, 0.026),
            (0.088, 0.023),
            (0.081, 0.020),
            (0.077, 0.009),
        ]
        _shell(
            scene, body, "torch_housing", [(z, r, r) for z, r in profile], "#57616a", finish="steel"
        )
        for z in (0.007, 0.012, 0.017, 0.022, 0.027, 0.032, 0.037, 0.042, 0.047):
            scene.cyl(body, (0, 0, z), 0.0186, 0.0022, "#303738")
        for z in (0.074, 0.079):
            scene.cyl(body, (0, 0, z), 0.0284, 0.0017, "#32393c")
        scene.cyl(body, (0, 0, 0.081), 0.020, 0.001, "#bfc4ba")
        scene.ell(body, (0, 0, 0.082), (0.006, 0.006, 0.002), "#ebd9a7")
        scene.ell(body, (0.009, -0.015, 0.054), (0.006, 0.004, 0.006), "#ca8d44")
    elif item == "remote":
        _shell(
            scene,
            body,
            "remote_case",
            [
                (0, 0.018, 0.044),
                (0.004, 0.022, 0.049),
                (0.009, 0.023, 0.050),
                (0.017, 0.023, 0.050),
                (0.023, 0.021, 0.048),
            ],
            "#353c40",
            shape=0.30,
        )
        scene.ell(body, (-0.011, 0.036, 0.023), (0.005, 0.005, 0.002), "#ba584f")
        scene.cyl(body, (0, 0.014, 0.024), 0.012, 0.003, "#737b7b")
        scene.cyl(body, (0, 0.014, 0.026), 0.006, 0.002, "#44494b")
        for y in (-0.010, -0.022, -0.034):
            for x in (-0.011, 0, 0.011):
                scene.ell(body, (x, y, 0.024), (0.0045, 0.003, 0.0018), "#b9b7ae")
    elif item == "tumbler":
        profile = [
            (0, 0.023),
            (0.003, 0.025),
            (0.008, 0.0255),
            (0.092, 0.033),
            (0.098, 0.0332),
            (0.099, 0.032),
            (0.0975, 0.0308),
            (0.009, 0.023),
        ]
        _shell(
            scene, body, "glazed_cup", [(z, r, r) for z, r in profile], "#447e83", finish="enamel"
        )
        scene.cyl(body, (0, 0, 0.071), 0.0283, 0.0012, "#493629")
    else:
        for i in range(3):
            z = i * 0.017 + 0.0015
            panel = _shell(
                scene,
                body,
                f"fold_{i}",
                [
                    (z, 0.051, 0.034),
                    (z + 0.004, 0.055, 0.039),
                    (z + 0.011, 0.056, 0.038),
                    (z + 0.015, 0.052, 0.035),
                ],
                "#667f92",
                shape=0.24,
                wave=0.0009,
            )
            panel.set("pos", f"{0.001 * (i % 2)} {0.0015 * (i % 2)} 0")
        for x in (-0.039, -0.032):
            scene.rod(body, (x, -0.030, 0.051), (x, 0.030, 0.051), 0.0012, "#d9cbb2")


def _start(scene, seed):
    rng = Random(seed)
    return (-0.08 + rng.uniform(-0.023, 0.023), -0.10 + rng.uniform(-0.018, 0.018), scene.table_z)


def receiving_hand(scene, phase, seed):
    scene.person(x=0, y=0.44)
    z = scene.table_z
    palms = {"left": (0.145, 0.155, z + 0.095), "right": (-0.145, 0.155, z + 0.095)}
    for side, palm in palms.items():
        scene.rest_hand(side, palm)
    item = "flashlight" if phase == "teach" else "remote"
    _object(scene, item, _start(scene, seed))
    if phase == "exception":
        # The person's left hand is visibly occupied holding folded paper steady.
        x, y, _ = palms["left"]
        for layer in range(4):
            scene.box(
                scene.world,
                (x, y - layer * 0.004, z + 0.002 + layer * 0.003),
                (0.111, 0.077, 0.003),
                "#dbb770" if layer == 3 else "#f0dcaa",
            )
        scene.rest_hand("left", (x, y + 0.023, z + 0.024))
        scene.rest_hand("right", (-0.145, 0.11, z + 0.096))
    options = {
        "left": "Offer it to the person's left hand.",
        "right": "Offer it to the person's right hand.",
    }
    targets = {side: (x, y - 0.041, height - 0.01) for side, (x, y, height) in palms.items()}
    robot = {side: [Motion("robot", item, pos, style="offer")] for side, pos in targets.items()}
    # The first hand takes the flashlight from the gripper and carries it inward.
    # The second takes it from the first and keeps it at the recipient's left.
    correction = (
        [
            Motion("human", item, (-0.026, 0.157, z + 0.114), style="hold"),
            Motion("human-left", item, (0.139, 0.153, z + 0.103), style="hold"),
        ]
        if phase == "teach"
        else []
    )
    command = "Hand me the flashlight." if item == "flashlight" else "Pass me the remote."
    return Case(
        command, options, "right" if phase == "exception" else "left", "right", robot, correction
    )


def approach_side(scene, phase, seed):
    # A quarter turn puts the transfer recipient on the left edge of the table.
    # Their current left-front location is now on the opposite world-X side.
    cx, cy, yaw = (-0.65, -0.012, 87) if phase == "transfer" else (0.018, 0.42, -8)
    z = scene.table_z
    scene.person(x=cx, y=cy, yaw=yaw)
    angle = radians(yaw)

    def relative(lateral, forward, height):
        return (
            cx + lateral * cos(angle) + forward * sin(angle),
            cy + lateral * sin(angle) - forward * cos(angle),
            height,
        )

    for side, sign in (("left", 1), ("right", -1)):
        scene.rest_hand(side, relative(sign * 0.215, 0.215, z + 0.047))
    item = "tumbler" if phase == "teach" else "cloth"
    _object(scene, item, _start(scene, seed))
    options = {
        "left": "Present it in the person's left-front quarter.",
        "right": "Present it in the person's right-front quarter.",
    }
    reach = 0.49 if phase == "transfer" else 0.39
    targets = {
        side: relative(sign * 0.155, reach, z + 0.145)
        for side, sign in (("left", 1), ("right", -1))
    }
    if phase == "exception":
        x, y, _ = targets["left"]
        # Raised shelf occupies the left presentation location. The left option
        # stops on the near side of the obstruction while waiting for access.
        scene.box(scene.world, (x, y, z + 0.153), (0.130, 0.115, 0.024), "#a57448")
        for dx in (-0.052, 0.052):
            for dy in (-0.045, 0.045):
                scene.box(
                    scene.world, (x + dx, y + dy, z + 0.072), (0.016, 0.016, 0.144), "#715846"
                )
        targets["left"] = (x, y - 0.125, z + 0.145)
        options["left"] = "Wait by the shelf for access to the person's left-front quarter."
        scene.rest_hand("right", relative(-0.156, 0.37, z + 0.105))
    robot = {side: [Motion("robot", item, pos, style="offer")] for side, pos in targets.items()}
    # The recipient indicates a location. The robot keeps carrying the drink
    # while presenting it a second time in front of the indicated shoulder.
    point = relative(0.155, reach, z + 0.10)
    correction = (
        [
            Motion("human", item, point, style="point"),
            Motion("robot", item, targets["left"], style="offer"),
        ]
        if phase == "teach"
        else []
    )
    command = "Bring me my drink." if item == "tumbler" else "Bring me the folded cloth."
    return Case(
        command, options, "right" if phase == "exception" else "left", "right", robot, correction
    )


BUILDERS = {"receiving-hand": receiving_hand, "approach-side": approach_side}
