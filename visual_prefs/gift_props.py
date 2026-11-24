"""Metric craft and meal-prep objects used in the gift-finishing scenes."""

from math import cos, pi, sin

from .prop_mesh import rounded_outline, rounded_solid, surface
from .scene import fmt


def _turn(geom, angle):
    geom.set("quat", fmt((cos(angle / 2), 0, 0, sin(angle / 2))))


def card_and_flower(s, card, flower):
    rounded_solid(s, card, "card_stock", (0, 0, 0), 0.145, 0.092, 0.004, 0.002, "#b97f67")
    rounded_solid(s, card, "card_face", (0, 0, 0.004), 0.138, 0.085, 0.0008, 0.001, "#f2dfbd")
    for a, b in (
        ((-0.033, -0.029), (-0.014, -0.018)),
        ((-0.014, -0.018), (0.006, -0.002)),
        ((0.006, -0.002), (0.018, 0.014)),
    ):
        s.rod(card, (*a, 0.005), (*b, 0.005), 0.0012, "#62784d")
    for x, y, angle in ((-0.020, -0.014, -0.91), (-0.010, -0.019, 0.18), (0.001, 0.001, -0.83)):
        _turn(s.ell(card, (x, y, 0.0054), (0.009, 0.0029, 0.0006), "#809268"), angle)
    for count, radius, shape, z, col, offset in (
        (10, 0.014, (0.013, 0.006, 0.0018), 0.0025, "#b35a70", 0),
        (9, 0.010, (0.010, 0.005, 0.0021), 0.0045, "#dc8294", 0.18),
    ):
        for i in range(count):
            a = i * 2 * pi / count + offset
            _turn(s.ell(flower, (radius * cos(a), radius * sin(a), z), shape, col), a)
    s.ell(flower, (0, 0, 0.0068), (0.007, 0.007, 0.0028), "#d9ac50")
    for i in range(10):
        a = i * 2 * pi / 10
        s.ell(
            flower, (0.0048 * cos(a), 0.0048 * sin(a), 0.0086), (0.0009, 0.0009, 0.0007), "#a97636"
        )


def container(s, b, lunch=False):
    if lunch:
        w, d, h, r, wall, col = 0.094, 0.076, 0.029, 0.011, 0.0025, "#759da3"
        key = "lunch"
    else:
        w, d, h, r, wall, col = 0.12, 0.095, 0.035, 0.0022, 0.002, "#b88c69"
        key = "gift"
    sections = [
        rounded_outline(w - 0.003, d - 0.003, r, 0),
        rounded_outline(w, d, r, h),
        rounded_outline(w - wall * 2, d - wall * 2, max(0.001, r - wall), h),
        rounded_outline(w - wall * 2 - 0.003, d - wall * 2 - 0.003, max(0.001, r - wall), 0.004),
    ]
    surface(s, b, key + "_shell", (0, 0, 0), sections, col, finish="enamel" if lunch else "matte")


def gift_lid(s, b):
    rounded_solid(s, b, "gift_lid", (0, 0, 0), 0.124, 0.099, 0.006, 0.003, "#9b7354")
    rounded_solid(s, b, "gift_tag", (0.022, -0.010, 0.0061), 0.039, 0.021, 0.0008, 0.002, "#f3e0b9")
    for dx in (-0.011, -0.008):
        s.rod(b, (0.022 + dx, -0.018, 0.007), (0.022 + dx, -0.002, 0.007), 0.00065, "#a56d60")


def tissue(s, b):
    # Accordion-folded tissue, with stepped edges and a shallow irregular crease.
    for j, (w, dx, z, col) in enumerate(
        (
            (0.090, 0, 0, "#c69bb0"),
            (0.084, 0.002, 0.0013, "#dcb8cb"),
            (0.078, 0.005, 0.0025, "#efcfdd"),
        )
    ):
        sections = []
        for i in range(13):
            x = w * (i / 12 - 0.5)
            edge = 0.031 + 0.0014 * sin(i * 0.8 + j)
            crease = 0.0008 * (i % 2)
            sections.append(
                [
                    (x, -edge, crease),
                    (x, edge, crease),
                    (x, edge, crease + 0.00065),
                    (x, -edge, crease + 0.00065),
                ]
            )
        surface(s, b, "folded_tissue_" + str(j), (dx, 0, z), sections, col)


def parcel(s, b):
    rounded_solid(s, b, "gift_wrap", (0, 0, 0), 0.055, 0.043, 0.022, 0.003, "#448489")
    s.box(b, (0, 0, 0.0222), (0.008, 0.043, 0.0006), "#dfb958")
    s.box(b, (0, 0, 0.0227), (0.055, 0.006, 0.0006), "#e4c672")
    for sign in (-1, 1):
        s.box(b, (0, sign * 0.0215, 0.011), (0.008, 0.0005, 0.022), "#d1a849")
        s.box(b, (sign * 0.0275, 0, 0.011), (0.0005, 0.006, 0.022), "#d1a849")
        _turn(s.ell(b, (sign * 0.005, 0, 0.0248), (0.006, 0.003, 0.002), "#ddb754"), sign * 0.28)
    s.ell(b, (0, 0, 0.025), (0.0028, 0.003, 0.0024), "#f2d27b")


def sandwich(s, b):
    # Loaf slices have a domed crown and a visible crust around the cut face.
    for key, z, h, scale, col in (
        ("lower_crust", 0, 0.006, 1, "#b6804d"),
        ("cheese", 0.006, 0.002, 0.99, "#e4b557"),
        ("greens", 0.008, 0.0026, 1.02, "#7c9653"),
        ("tomato", 0.0106, 0.002, 0.94, "#b76749"),
        ("upper_crust", 0.0126, 0.006, 1, "#ba8451"),
        ("crumb", 0.0186, 0.0006, 0.92, "#e0bf8e"),
    ):
        outline = [
            (-0.027, -0.022),
            (0.027, -0.022),
            (0.028, -0.019),
            (0.026, 0.006),
            (0.029, 0.012),
            (0.028, 0.017),
            (0.022, 0.021),
            (0.010, 0.024),
            (-0.009, 0.024),
            (-0.022, 0.021),
            (-0.028, 0.017),
            (-0.029, 0.012),
            (-0.026, 0.006),
            (-0.028, -0.019),
        ]
        loops = [[(x * scale, y * scale, dz) for x, y in outline] for dz in (0, h)]
        surface(s, b, "sandwich_" + key, (0, 0, z), loops, col)
    for x, y in ((-0.016, 0.009), (0.007, 0.013), (0.018, -0.006), (-0.004, -0.011)):
        s.ell(b, (x, y, 0.0192), (0.0014, 0.00085, 0.00028), "#b2946f")


def lunch_lid(s, b, i):
    rounded_solid(s, b, "lunch_lid", (0, 0, 0), 0.097, 0.079, 0.006, 0.011, "#53858e", "enamel")
    rounded_solid(s, b, "lunch_lid_panel", (0, 0, 0.0058), 0.084, 0.066, 0.0015, 0.008, "#6e9aa1")
    for sign in (-1, 1):
        rounded_solid(
            s, b, "lunch_catch", (sign * 0.046, 0, 0.005), 0.006, 0.026, 0.004, 0.002, "#b0c5c4"
        )
    label = s.label(b, (0, -0.001, 0.008), "Alex" if i == 0 else "Sam", 0.034, 0.015)
    label.set("quat", fmt((cos(pi / 4), sin(pi / 4), 0, 0)))
