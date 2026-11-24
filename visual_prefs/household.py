"""Personal storage and cleaner selection episodes."""

import math
import random

from .episode import Case, Motion


def _tray(s, body, x, y, z, width, depth, wall, color):
    s.box(body, (x, y, z + 0.003), (width, depth, 0.006), color)
    for side in (-1, 1):
        s.box(body, (x + side * (width - 0.005) / 2, y, z + wall / 2), (0.005, depth, wall), color)
        s.box(body, (x, y + side * (depth - 0.005) / 2, z + wall / 2), (width, 0.005, wall), color)


def _paper(s, x, y, z):
    for i, color in enumerate(("#ce7563", "#ddbd63", "#71ada1")):
        s.box(
            s.world,
            (x + 0.011 * i, y + 0.009 * i, z + 0.0015 + i * 0.003),
            (0.082, 0.065, 0.003),
            color,
        )


def _keys(s, origin):
    b = s.prop("keys", origin)
    for i in range(12):

        def point(j):
            a = math.tau * j / 12
            return (0.015 * math.cos(a), 0.015 * math.sin(a), 0.005)

        s.rod(b, point(i), point(i + 1), 0.0024, "#afbdc6")
    for dx, dy, color in ((0.013, 0, "#c9a455"), (-0.005, -0.009, "#8798a5")):
        s.ell(b, (dx, dy, 0.005), (0.009, 0.010, 0.003), color)
        s.box(b, (dx, dy - 0.019, 0.005), (0.006, 0.030, 0.005), color)
        for n in range(2):
            s.box(b, (dx + 0.004, dy - 0.029 + n * 0.006, 0.005), (0.007, 0.003, 0.005), color)


def _flashlight(s, origin):
    b = s.prop("flashlight", origin)
    s.rod(b, (-0.032, 0, 0.012), (0.021, 0, 0.012), 0.009, "#324655")
    s.rod(b, (0.016, 0, 0.012), (0.030, 0, 0.012), 0.012, "#637787")
    s.rod(b, (0.030, 0, 0.012), (0.031, 0, 0.012), 0.010, "#e5dfb4")
    s.box(b, (0, 0, 0.021), (0.012, 0.005, 0.004), "#db984d")


def _case(s, origin):
    b = s.prop("pen_case", origin)
    s.box(b, (0, 0, 0.012), (0.105, 0.044, 0.023), "#413c52")
    s.box(b, (0, 0, 0.024), (0.101, 0.042, 0.003), "#846174")
    for edge in (-1, 1):
        s.box(b, (edge * 0.036, 0, 0.026), (0.005, 0.043, 0.002), "#b99461")
    s.box(b, (0, -0.023, 0.012), (0.016, 0.004, 0.009), "#d3ae68")


def _rulers(s, origin):
    b = s.prop("rulers", origin)
    for i in range(4):
        y, z = i * 0.006, 0.002 + i * 0.004
        s.box(b, (0, y, z), (0.103, 0.018, 0.004), "#dab37a")
        for j in range(11):
            length = 0.006 if j % 5 == 0 else 0.003
            s.box(
                b,
                (-0.045 + j * 0.009, y - 0.008 + length / 2, z + 0.0021),
                (0.001, length, 0.0005),
                "#5f5140",
            )


def storage(s, phase, seed):
    rng = random.Random(seed)
    z = s.table_z
    s.person(x=0.045, y=0.44)
    # The flush sliding cover parks behind the compartment when open.
    left = rng.choice((-1, 1))
    sx, tx = 0.131 * left, -0.131 * left
    sy = -0.003
    _tray(s, s.world, sx, sy, z, 0.151, 0.122, 0.047, "#795848")
    open_pos = (sx, sy + 0.128, z + 0.047)
    shut_pos = (sx, sy, z + 0.047)
    lid = s.prop("storage_cover", shut_pos)
    s.box(lid, (0, 0, 0.004), (0.153, 0.124, 0.008), "#977357")
    s.box(lid, (0, -0.046, 0.013), (0.047, 0.010, 0.012), "#514b47")
    _tray(s, s.world, tx, sy, z, 0.161, 0.124, 0.012, "#4b7977")
    if phase == "teach":
        _keys(s, (-0.061, -0.137, z))
        _flashlight(s, (0.064, -0.137, z))
        items = [("keys", -0.018, -0.015), ("flashlight", 0.012, 0.027)]
        cmd = "Put the house keys and flashlight away after use in the entryway."
        surface = "Set them together on the open tray."
    elif phase == "transfer":
        _case(s, (rng.uniform(-0.045, 0.045), -0.135, z))
        items = [("pen_case", 0, 0)]
        cmd = "I finished calligraphy practice. Leave my pen case handy for tomorrow."
        surface = "Leave the pen case on the open tray."
    else:
        _rulers(s, (rng.uniform(-0.045, 0.045), -0.135, z))
        _paper(s, tx, 0.120, z)
        items = [("rulers", 0, 0)]
        cmd = "Set out four rulers as the group takes their seats for crafts. The first step uses rulers."
        surface = "Set the rulers on the tray beside the shared craft materials."

    def stow(actor):
        return (
            [Motion(actor, "storage_cover", open_pos, style="slide")]
            + [Motion(actor, name, (sx + dx, sy + dy, z + 0.006)) for name, dx, dy in items]
            + [Motion(actor, "storage_cover", shut_pos, style="slide")]
        )

    tray = [Motion("robot", name, (tx + dx, sy + dy, z + 0.006)) for name, dx, dy in items]
    return Case(
        cmd,
        {
            "tray": surface,
            "compartment": "Place the items in the shallow compartment and close it.",
        },
        "tray" if phase == "exception" else "compartment",
        "tray",
        {"tray": tray, "compartment": stow("robot")},
        stow("human") if phase == "teach" else [],
    )


def _bottle(s, name, origin, text, tint):
    b = s.prop(name, origin)
    s.box(b, (0, 0, 0.047), (0.074, 0.047, 0.088), tint)
    s.ell(b, (0, 0, 0.088), (0.036, 0.023, 0.019), tint)
    s.cyl(b, (0, 0, 0.106), 0.012, 0.021, "#e4e7df")
    s.box(b, (0.005, 0, 0.121), (0.047, 0.021, 0.016), "#45545a")
    s.rod(b, (0.016, 0, 0.117), (0.014, 0, 0.103), 0.003, "#667374")
    s.label(b, (0, -0.0245, 0.049), text, 0.070, 0.048)


def _wipe(s, actor, x, z):
    return [Motion(actor, "cloth", (x, y, z), style="slide") for y in (-0.025, -0.135, -0.045)]


def scent(s, phase, seed):
    rng = random.Random(seed)
    z = s.table_z
    s.person(x=0.05, y=0.44)
    side = rng.choice((-1, 1))
    names = ("citrus", "free")
    pos = {name: ((1 - 2 * i) * side * 0.119, 0.089, z + 0.006) for i, name in enumerate(names)}
    _tray(s, s.world, 0, 0.091, z, 0.34, 0.086, 0.009, "#736b60")
    _bottle(s, "citrus", pos["citrus"], "MILD CITRUS", "#e9b15f")
    _bottle(s, "free", pos["free"], "FRAGRANCE FREE", "#89b9c2")
    cloth = s.prop("cloth", (0.01, -0.141, z))
    s.box(cloth, (0, 0, 0.004), (0.078, 0.055, 0.008), "#788eaa")
    for x in (-0.028, -0.023):
        s.box(cloth, (x, 0, 0.0082), (0.002, 0.052, 0.0008), "#d8dfdf")
    if phase == "teach":
        cmd = "Set out a cleaner so I can wipe my kitchen counter. I am home alone."
        for i in range(3):
            s.cyl(s.world, (-0.208, 0.074 + 0.03 * i, z + 0.020), 0.014, 0.040, "#d1c0a0")
            s.cyl(s.world, (-0.208, 0.074 + 0.03 * i, z + 0.042), 0.015, 0.005, "#805c44")
    elif phase == "transfer":
        cmd = "Wipe the work surface in my private sewing room. Only I use it."
        for i, tint in enumerate(("#b87076", "#71909b", "#cfad69")):
            x = -0.214 + i * 0.022
            s.cyl(s.world, (x, 0.161, z + 0.021), 0.010, 0.039, tint)
            for h in (0.003, 0.040):
                s.cyl(s.world, (x, 0.161, z + h), 0.013, 0.005, "#ccad89")
    else:
        cmd = "Wipe the shared worktop before the guests arrive for our craft session."
        _paper(s, -0.185, 0.164, z)

    ready = (0.103, -0.091, z)
    robot = {name: [Motion("robot", name, ready)] for name in names}
    if phase != "teach":
        for moves in robot.values():
            moves.extend(_wipe(s, "robot", -0.034, z))
    human = (
        (
            [Motion("human", "free", pos["free"]), Motion("human", "citrus", ready)]
            + _wipe(s, "human", -0.034, z)
        )
        if phase == "teach"
        else []
    )
    verb = "Set out" if phase == "teach" else "Use"
    options = {
        "citrus": f"{verb} the mild-citrus cleaner.",
        "free": f"{verb} the fragrance-free cleaner.",
    }
    return Case(cmd, options, "free" if phase == "exception" else "citrus", "free", robot, human)


BUILDERS = {"private-storage": storage, "cleaning-scent": scent}
