"""Handover choices in the seated recipient's frame of reference."""

from math import cos, radians, sin
from random import Random

from .episode import Case, Motion


def _object(scene, item, position):
    body = scene.prop(item, position)
    if item == "flashlight":
        scene.cyl(body, (0, 0, 0.035), 0.019, 0.070, "#d78d29")
        scene.cyl(body, (0, 0, 0.078), 0.028, 0.018, "#344456")
        scene.cyl(body, (0, 0, 0.089), 0.023, 0.004, "#f7e9ac")
    elif item == "remote":
        scene.box(body, (0, 0, 0.012), (0.046, 0.100, 0.024), "#313c49")
        for y in (-0.027, -0.009, 0.009):
            for x in (-0.010, 0.010):
                scene.box(body, (x, y, 0.025), (0.012, 0.009, 0.004), "#c9cdd1")
        scene.cyl(body, (0, 0.034, 0.025), 0.007, 0.004, "#e57650")
    elif item == "tumbler":
        scene.cyl(body, (0, 0, 0.046), 0.031, 0.092, "#26828c")
        scene.cyl(body, (0, 0, 0.096), 0.033, 0.008, "#d5ede6")
    else:
        for layer in range(3):
            scene.box(
                body,
                (0, 0.002 * (layer % 2), 0.009 + layer * 0.018),
                (0.112, 0.078, 0.017),
                ("#61789d", "#a8c5d5", "#6989ab")[layer],
            )
        for x in (-0.038, -0.030):
            scene.box(body, (x, 0, 0.055), (0.003, 0.076, 0.003), "#e9e1c8")


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
