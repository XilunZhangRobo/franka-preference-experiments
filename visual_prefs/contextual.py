"""Light selection, cooked vegetable samples, and completion announcements."""

import math
import random
import xml.etree.ElementTree as ET

from .episode import Case, Motion


def _press(item, pos, actor="robot"):
    return Motion(actor, item, pos, "touch")


def _lamp(s, item, x, overhead):
    z = s.table_z
    y = -0.065
    pos = (x, y, z)
    switch = s.prop(item, pos)
    # An angled key face presents its printed legend to a standing operator.
    panel = ET.SubElement(switch, "body", pos="0 0 .026", euler="-.63 0 .52")
    s.box(panel, (0, 0.003, 0), (0.102, 0.011, 0.046), "#41505b")
    s.label(panel, (0, -0.003, 0), "CEILING" if overhead else "DESK", 0.095, 0.040)
    s.box(switch, (0, 0, 0.006), (0.104, 0.056, 0.012), "#35444e")
    s.grasp(item, (0, -0.008, 0.034))
    if overhead:
        # A linear pendant hangs from the room ceiling above human head height.
        # The work camera sees the pool of light; its downward view excludes the ceiling.
        lx, ly, lz = -0.10, -0.06, 1.96
        ceiling_z = 2.48
        s.box(s.world, (0, 0, ceiling_z + 0.014), (3.22, 2.30, 0.028), "#e5e2da")
        s.box(s.world, (lx, ly, ceiling_z - 0.008), (0.40, 0.045, 0.016), "#b2b1a6")
        for dx in (-0.17, 0.17):
            s.rod(
                s.world,
                (lx + dx, ly, lz + 0.025),
                (lx + dx, ly, ceiling_z - 0.012),
                0.0035,
                "#666760",
            )
        s.box(s.world, (lx, ly, lz + 0.012), (0.47, 0.105, 0.024), "#717773")
        s.box(s.world, (lx, ly, lz - 0.002), (0.454, 0.095, 0.006), "#efeada")
    else:
        lx, ly, lz = x, 0.10, z + 0.23
        s.cyl(s.world, (x, ly + 0.05, z + 0.008), 0.042, 0.016, "#54777b")
        s.rod(s.world, (x, ly + 0.05, z + 0.015), (x, ly + 0.055, lz + 0.025), 0.007, "#54777b")
        s.rod(s.world, (x, ly + 0.055, lz + 0.025), (x, ly, lz + 0.015), 0.007, "#54777b")
        s.cyl(s.world, (lx, ly, lz + 0.007), 0.032, 0.024, "#50767b")
        s.cyl(s.world, (lx, ly, lz - 0.007), 0.029, 0.004, "#f2e9c8")
    name = f"{item}_light"
    ET.SubElement(
        s.world,
        "light",
        name=name,
        pos=f"{lx} {ly} {lz - 0.012}",
        dir="0 0 -1",
        diffuse="0.88 0.87 0.80" if overhead else "0.82 0.78 0.68",
        specular="0.05 0.05 0.05",
        cutoff="60" if overhead else "40",
        exponent="1",
        castshadow="false",
    )
    s.switch(item, name)
    return pos


def lighting(s, phase, seed):
    rng = random.Random(seed)
    z = s.table_z
    s.person(x=0, y=0.44)
    side = rng.choice((-1, 1))
    desk = _lamp(s, "desk_switch", 0.19 * side, False)
    overhead = _lamp(s, "ceiling_switch", -0.19 * side, True)
    colors = ["#d28777", "#788ba0", "#b6a366", "#609287"]
    rng.shuffle(colors)
    for i in range(4):
        x, y = (i % 2 - 0.5) * 0.070, 0.095 + (i // 2) * 0.060
        if phase == "teach":
            s.box(s.world, (x, y, z + 0.003), (0.064, 0.053, 0.006), colors[i])
            s.cyl(s.world, (x + 0.027, y, z + 0.003), 0.010, 0.006, colors[i])
        elif phase == "transfer":
            s.box(s.world, (x, y, z + 0.005), (0.058, 0.048, 0.010), colors[i])
            for dx in (-0.014, 0.014):
                s.box(s.world, (x + dx, y, z + 0.011), (0.004, 0.040, 0.002), "#eee5c6")
        else:
            for j in range(5):
                a = math.tau * j / 5
                s.ell(
                    s.world,
                    (x + 0.013 * math.cos(a), y + 0.013 * math.sin(a), z + 0.004),
                    (0.012, 0.012, 0.004),
                    colors[i],
                )
    if phase == "exception":
        s.guest(-0.70, 0.15, 70)
        s.guest(0.44, 0.52, -42)
    command = {
        "teach": "Turn on a light for the person working on a puzzle.",
        "transfer": "Turn on a light for the person comparing ceramic tile patterns.",
        "exception": "Turn on a light for the group making paper decorations.",
    }[phase]
    return Case(
        command,
        {"desk": "Turn on the desk lamp.", "ceiling": "Turn on the overhead fixture."},
        "ceiling",
        "desk",
        {"desk": [_press("desk_switch", desk)], "ceiling": [_press("ceiling_switch", overhead)]},
        [_press("desk_switch", desk, "human"), _press("ceiling_switch", overhead, "human")]
        if phase == "teach"
        else [],
    )


def _vegetable(s, item, pos, broccoli, tender):
    b = s.prop(item, pos)
    if broccoli:
        h = 0.011 if tender else 0.027
        spread = 0.017 if tender else 0.011
        s.cyl(b, (0, 0, h / 2), 0.008, h, "#81a554")
        for i in range(7):
            a = i * math.tau / 7
            s.ell(
                b,
                (spread * math.cos(a), spread * math.sin(a), h),
                (0.012, 0.012, h * 0.44),
                "#497947",
            )
    else:
        for i in range(3):
            dx = (i - 1) * 0.012
            mid = 0.009 if tender else 0.002
            s.rod(b, (dx, -0.033, 0.004), (dx + mid, -0.006, 0.006), 0.004, "#63864a")
            s.rod(b, (dx + mid, -0.006, 0.006), (dx - mid * 0.4, 0.031, 0.004), 0.004, "#63864a")


def texture(s, phase, seed):
    rng = random.Random(seed)
    z = s.table_z
    s.person(x=0.015, y=0.44)
    sign = rng.choice((-1, 1))
    plate = (0, 0.145, z + 0.009)
    s.cyl(s.world, (0, 0.145, z + 0.004), 0.065, 0.008, "#e6dfc9")
    # The other ingredients convey which dish the person is preparing.
    if phase == "exception":
        for i in range(8):
            a = math.tau * i / 8
            s.ell(
                s.world,
                (0.041 * math.cos(a), 0.145 + 0.041 * math.sin(a), z + 0.014),
                (0.014, 0.011, 0.005),
                "#7ba35a" if i % 3 else "#c26953",
            )
    else:
        for i in range(4):
            s.ell(
                s.world,
                (0.032 + 0.009 * (i % 2), 0.132 + 0.015 * (i // 2), z + 0.020),
                (0.012, 0.012, 0.011),
                "#c39d64",
            )
    positions = {}
    for item, side in (("firm", sign), ("tender", -sign)):
        x = 0.135 * side
        s.box(s.world, (x, -0.028, z + 0.004), (0.103, 0.121, 0.008), "#acb9b7")
        positions[item] = (x, -0.025, z + 0.008)
        _vegetable(s, item, positions[item], phase == "teach", item == "tender")
        # Each tray carries the cook's batch card. Doneness is otherwise ambiguous in RGB.
        card = s.prop(f"{item}_card", (x, -0.072, z + 0.008))
        s.box(card, (0, 0, 0.013), (0.092, 0.004, 0.026), "#f3eada")
        s.label(card, (0, -0.0025, 0.014), item.upper(), 0.085, 0.020)
    fork_pos = (0, -0.12, z)
    fork = s.prop("fork", fork_pos)
    s.rod(fork, (0, -0.036, 0.004), (0, 0.018, 0.004), 0.0045, "#929d9d")
    s.box(fork, (0, 0.018, 0.004), (0.020, 0.008, 0.005), "#929d9d")
    for i in range(4):
        x = (i - 1.5) * 0.005
        s.rod(fork, (x, 0.019, 0.004), (x, 0.036, 0.004), 0.0015, "#929d9d")
    expected = "firm" if phase == "exception" else "tender"
    default = "tender" if phase == "exception" else "firm"
    human = []
    if phase == "teach":
        human.append(Motion("human", "firm", positions["firm"]))
        for item in ("firm", "tender"):
            x, y, h = positions[item]
            human.append(
                Motion("human", "fork", (x, y - 0.025, h + (0.036 if item == "firm" else 0.014)))
            )
        human.extend([Motion("human", "fork", fork_pos), Motion("human", "tender", plate)])
    command = {
        "teach": "Serve cooked broccoli alongside the warm dinner.",
        "transfer": "Prepare cooked green beans for the warm side dish.",
        "exception": "Prepare cooked green beans for the chilled salad.",
    }[phase]
    return Case(
        command,
        {"firm": "Serve the firmer batch.", "tender": "Serve the more tender batch."},
        expected,
        default,
        {k: [Motion("robot", k, plate)] for k in positions},
        human,
    )


def completion(s, phase, seed):
    rng = random.Random(seed)
    z = s.table_z
    s.person(x=0, y=0.44)
    sign = rng.choice((-1, 1))
    speaker_pos = (0.14 * sign, -0.072, z)
    speaker = s.prop("speaker", speaker_pos)
    s.box(speaker, (0, 0, 0.027), (0.055, 0.045, 0.054), "#4a5763")
    s.ell(speaker, (0, -0.023, 0.026), (0.016, 0.003, 0.017), "#253540")
    s.sound("speaker", "Work is complete.")
    speak = Motion("robot", "speaker", speaker_pos, "say")
    pen_pos = (-0.015 * sign, 0.111, z + 0.004)
    paper = (0.012 * sign, 0.107, z)
    s.box(s.world, (paper[0], paper[1], z + 0.002), (0.14, 0.103, 0.004), "#eee5cf")
    for i in range(4):
        s.rod(
            s.world,
            (-0.040, 0.130 - i * 0.009, z + 0.0043),
            (0.006 + i * 0.005, 0.130 - i * 0.009, z + 0.0043),
            0.001,
            "#788596",
        )
    pen = s.prop("pencil", pen_pos)
    s.rod(pen, (0, -0.028, 0.004), (0.020, 0.031, 0.004), 0.0035, "#dda651")
    s.rod(pen, (0, -0.028, 0.004), (-0.002, -0.033, 0.004), 0.002, "#424954")
    bin_x = -0.155 * sign
    bin_body = s.prop("filled_bin", (bin_x, -0.062, z))
    s.box(bin_body, (0, 0, 0.014), (0.090, 0.071, 0.028), "#6a928c")
    for i in range(3):
        s.box(bin_body, ((i - 1) * 0.026, 0, 0.036), (0.022, 0.055, 0.020), "#bf996e")
    writing = Motion(
        "human", "pencil", (pen_pos[0] + 0.019, pen_pos[1] - 0.013, pen_pos[2]), "slide"
    )
    set_pencil_down = Motion("human", "pencil", (0.11 * sign, 0.13, z))
    activity = [writing, set_pencil_down]
    if phase == "teach":
        activity.append(_press("filled_bin", (bin_x, -0.062, z), "human"))
    if phase == "exception":
        screen_pos = (0.045 * sign, 0.137, z)
        screen = s.prop("call_screen", screen_pos)
        s.box(screen, (0, 0, 0.068), (0.145, 0.010, 0.112), "#475363")
        s.box(screen, (0, -0.006, 0.068), (0.132, 0.004, 0.100), "#8bb0b8")
        s.ell(screen, (0, -0.010, 0.076), (0.020, 0.004, 0.025), "#cba48a")
        s.ell(screen, (0, -0.010, 0.042), (0.038, 0.004, 0.013), "#77839d")
        s.label(screen, (0, -0.014, 0.108), "CALL", 0.040, 0.014)
        # Putting away the screen marks the end of the conversation before speech.
        activity = [Motion("human", "call_screen", (0.20 * sign, 0.14, z))]
    command = {
        "teach": "The bin is full. Give the person a low-priority completion update.",
        "transfer": "The delivery is complete while the person draws alone. Give a low-priority update.",
        "exception": "The shelf is organized while the person speaks on a video call. Give a low-priority update.",
    }[phase]
    options = {
        "now": "Give a brief spoken update now.",
        "later": "Give the spoken update at the person's next pause.",
    }
    expected = "later" if phase == "exception" else "now"
    default = "now" if phase == "exception" else "later"
    # Both clips contain the same exogenous activity. Only speech timing changes.
    human = [Motion("human", "pencil", pen_pos)] if phase == "teach" else []
    return Case(
        command,
        options,
        expected,
        default,
        {"now": [speak, *activity], "later": [*activity, speak]},
        human,
    )


BUILDERS = {"lighting": lighting, "vegetable-texture": texture, "completion-update": completion}
