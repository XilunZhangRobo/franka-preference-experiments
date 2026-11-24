"""Tabletop craft and packing interactions."""

from math import cos, pi, sin
from random import Random

from . import gift_props
from .episode import Case, Motion
from .prop_mesh import ring, surface


def _body(s, name, x, y):
    return s.prop(name, (x, y, s.table_z))


def _block(s, body, size, color, x=0, y=0, z=0):
    s.box(body, (x, y, z + size[2] / 2), size, color)


def _tray(s, body, w, d, h, color):
    _block(s, body, (w, d, 0.004), color)
    for side in (-1, 1):
        _block(s, body, (0.004, d, h), color, x=side * (w - 0.004) / 2)
        _block(s, body, (w, 0.004, h), color, y=side * (d - 0.004) / 2)


def _move(s, item, x, y, height=0, actor="robot"):
    return Motion(actor, item, (x, y, s.table_z + height))


def _gift(s, phase, seed):
    s.person(x=0, y=0.44)
    rng = Random(seed)
    mirror = rng.choice((-1, 1))
    delta = rng.uniform(-0.012, 0.012)
    if phase == "teach":
        card = _body(s, "card", delta, 0.09)
        f = _body(s, "flower", mirror * 0.16, -0.065)
        gift_props.card_and_flower(s, card, f)
        above_card = (delta + 0.018, 0.104, s.table_z + 0.085)
        return Case(
            "Help prepare the handmade card.",
            {
                "place": "Bring the flower over the card to attach it.",
                "set_out": "Set the flower beside the card.",
            },
            "set_out",
            "place",
            {
                "place": [Motion("robot", "flower", above_card, "offer")],
                "set_out": [_move(s, "flower", delta + 0.114, 0.09)],
            },
            [
                Motion("human", "flower", (delta - 0.083, 0.13, s.table_z + 0.17), "stop"),
                _move(s, "flower", delta + 0.018, 0.104, 0.005, "human-left"),
            ],
        )
    if phase == "transfer":
        box = _body(s, "box", delta, 0.075)
        gift_props.container(s, box)
        lid = s.prop("lid", (delta, 0.075, s.table_z + 0.035))
        # Start the lidded box closed so staging visibly opens it.
        gift_props.gift_lid(s, lid)
        tissue = _body(s, "tissue", mirror * 0.156, -0.077)
        gift_props.tissue(s, tissue)
        gift = _body(s, "gift", -mirror * 0.146, -0.075)
        gift_props.parcel(s, gift)
        open_box = _move(s, "lid", 0.045 * mirror, -0.128)
        stage = [
            open_box,
            _move(s, "tissue", -0.14 * mirror, 0.09),
            _move(s, "gift", 0.14 * mirror, 0.09),
        ]
        finish = [
            open_box,
            _move(s, "tissue", delta, 0.075, 0.004),
            _move(s, "gift", delta, 0.075, 0.0085),
            _move(s, "lid", delta, 0.075, 0.035),
        ]
        return Case(
            "Help get the gift box ready.",
            {
                "stage": "Open the box and set the tissue and gift alongside it.",
                "pack": "Arrange the tissue and gift inside and close the box.",
            },
            "stage",
            "pack",
            {"stage": stage, "pack": finish},
            [],
        )
    if phase != "exception":
        raise ValueError(phase)
    pack, stage = [], []
    for i, x in enumerate((-0.14, 0.14)):
        x += delta
        box = _body(s, f"lunchbox{i}", x, 0.075)
        gift_props.container(s, box, lunch=True)
        food = _body(s, f"portion{i}", x, -0.09)
        gift_props.sandwich(s, food)
        lid = _body(s, f"cover{i}", x * 0.45, -0.14)
        gift_props.lunch_lid(s, lid, i)
        pack.extend(
            [_move(s, f"portion{i}", x, 0.075, 0.004), _move(s, f"cover{i}", x, 0.075, 0.029)]
        )
        stage.extend([_move(s, f"portion{i}", x, 0.158), _move(s, f"cover{i}", x * 0.46, -0.016)])
    return Case(
        "Prepare the labeled lunches for tomorrow morning.",
        {
            "stage": "Set out the boxes, portions, and lids for packing.",
            "pack": "Put a portion in each box and close each lid.",
        },
        "pack",
        "stage",
        {"stage": stage, "pack": pack},
        [],
    )


def _order(s, phase, seed):
    # From the side seat the person's right points toward +x and -y.
    seat_yaw = 120 if phase == "transfer" else 0
    if phase == "transfer":
        s.person(x=-0.69, y=0.17, yaw=seat_yaw)
    else:
        s.person(x=0, y=0.49)
    rng = Random(seed)
    delta = rng.uniform(-0.015, 0.015)
    mirror = rng.choice((-1, 1))
    if phase == "teach":
        base = _body(s, "base", -0.10 * mirror, -0.09)
        s.cyl(base, (0, 0, 0.012), 0.034, 0.024, "#b74744")
        s.cyl(base, (0, 0, 0.030), 0.016, 0.012, "#d05a4f")
        cap = _body(s, "cap", 0.10 * mirror, -0.09)
        s.cyl(cap, (0, 0, 0.009), 0.030, 0.018, "#e8bd45")

        def row(sign):
            return [
                _move(s, "base", delta + sign * 0.115, 0.12),
                _move(s, "cap", delta - sign * 0.115, 0.12),
            ]

        def hand(item, x, y, z=0):
            return _move(s, item, delta + x, y, z, "human")

        return Case(
            "Set out the red base and yellow cap for assembly.",
            {
                "red_left": "Set the red base on the person's left and the cap on their right.",
                "red_right": "Set the red base on the person's right and the cap on their left.",
            },
            "red_right",
            "red_left",
            {"red_left": row(1), "red_right": row(-1)},
            [
                hand("cap", 0, 0.045),
                hand("base", -0.115, 0.12),
                hand("cap", 0.115, 0.12),
                hand("base", 0, 0.155),
                hand("cap", 0, 0.155, 0.036),
            ],
        )
    if phase == "transfer":
        pot = _body(s, "pot", mirror * 0.15, -0.095)

        # Revolve the outer terracotta wall and return down to the drainage hole.
        profile = [
            (0.020, 0),
            (0.030, 0.044),
            (0.033, 0.044),
            (0.033, 0.053),
            (0.028, 0.053),
            (0.017, 0.004),
            (0.003, 0.004),
            (0.003, 0),
        ]
        ring(
            s,
            pot,
            "terracotta",
            (0, 0, 0),
            [(r, h, 0) for r, h in profile],
            "#bd795a",
            finish="matte",
        )
        s.grasp("pot", (0, 0, 0.030))
        scoop = _body(s, "scoop", 0, -0.095)
        s.rod(scoop, (0, -0.039, 0.008), (0, -0.008, 0.009), 0.006, "#976d48")
        s.rod(scoop, (0, -0.009, 0.009), (0, 0.012, 0.005), 0.003, "#929e9d")
        sections = []
        for y, width, floor, curl in [
            (0.005, 0.004, 0.005, 0.003),
            (0.012, 0.015, 0.002, 0.010),
            (0.031, 0.018, 0.001, 0.010),
            (0.042, 0.012, 0.001, 0.004),
            (0.050, 0.001, 0.001, 0.0005),
        ]:
            face = [(width * t / 4, y, floor + curl * (t / 4) ** 2) for t in range(-4, 5)]
            sections.append(face + [(x, y, z - 0.001) for x, y, z in reversed(face)])
        surface(s, scoop, "potting_blade", (0, 0, 0), sections, "#acb9b8", finish="steel")
        s.grasp("scoop", (0, -0.020, 0.008))
        tag = _body(s, "tag", -mirror * 0.15, -0.095)
        _block(s, tag, (0.007, 0.060, 0.005), "#dfc494")
        _block(s, tag, (0.034, 0.024, 0.005), "#f9e8bf", y=0.022, z=0.005)

        def row(sign):
            # sign=+1 orders from anatomical left, the rotated local +x axis.
            angle = seat_yaw * pi / 180
            cx, cy = -0.150 + delta, 0.060
            dx, dy = sign * 0.115 * cos(angle), sign * 0.115 * sin(angle)
            return [
                _move(s, "pot", cx + dx, cy + dy),
                _move(s, "scoop", cx, cy),
                _move(s, "tag", cx - dx, cy - dy),
            ]

        return Case(
            "Set out a row for the seated person to use the pot, scoop, then tag.",
            {
                "pot_left": "Place the pot at the person's left, scoop in the middle, and tag at their right.",
                "pot_right": "Place the pot at the person's right, scoop in the middle, and tag at their left.",
            },
            "pot_right",
            "pot_left",
            {"pot_left": row(1), "pot_right": row(-1)},
            [],
        )
    if phase != "exception":
        raise ValueError(phase)
    for x, y, yaw in ((-0.72, 0.13, 95), (-0.41, 0.56, 38), (0.44, 0.52, -42)):
        s.guest(x, y, yaw)
    tray = _body(s, "shared_tray", delta, 0.010)
    _tray(s, tray, 0.17, 0.091, 0.014, "#b5a58b")
    shared, row = [], []
    colors = ["#4177aa", "#568d5c", "#b45465", "#805ca2"]
    rng.shuffle(colors)
    for i, color in enumerate(colors):
        name = f"marker{i}"
        x = (i - 1.5) * 0.095
        marker = _body(s, name, x * mirror, -0.124)
        s.rod(marker, (0, -0.031, 0.006), (0, 0.018, 0.006), 0.006, "#e5e2d9")
        s.rod(marker, (0, 0.017, 0.006), (0, 0.031, 0.006), 0.007, color)
        shared.append(_move(s, name, delta + (i - 1.5) * 0.031, 0.010, 0.004))
        row.append(_move(s, name, delta + x, 0.157))
    return Case(
        "Put out the markers for four people sharing the table.",
        {
            "tray": "Put the markers together in the central tray.",
            "row": "Lay the markers in a row in front of the seated person.",
        },
        "tray",
        "row",
        {"tray": shared, "row": row},
        [],
    )


BUILDERS = {"gift-finishing": _gift, "material-order": _order}
