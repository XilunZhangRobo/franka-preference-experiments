"""Bench-scale visual parts and simple solid-envelope proxies for transport QA."""

import math
import xml.etree.ElementTree as ET
from random import Random

from . import textile
from .prop_mesh import band, finish_material, rounded_solid, surface
from .scene import fmt


def _disc_proxy(s, x, y, radius, height):
    # Outer footprint supplies the support plane. Holes and grooves are visual only.
    return [s.cyl(ET.Element("body"), (x, y, 0.006 + height / 2), radius, height, "#777777")]


def _layout(s, b):
    return Random(f"mat-cargo/{getattr(s, 'cargo_layout_seed', 0)}/{b.get('name')}")


def _internal_thread(s, b, key, pos, bore, height, color):
    # Triangular thread ridge swept continuously around the bore. Ends stop
    # inside the entry chamfers. Thread pitch is an appearance approximation.
    pitch = 0.00175
    turns = int((height - 0.0025) / pitch)
    sections = []
    for j in range(turns * 36 + 1):
        a = math.tau * j / 36
        z = 0.0013 + j * pitch / 36
        sections.append(
            [
                (r * math.cos(a), r * math.sin(a), z + h)
                for r, h in (
                    (bore + 0.00008, -0.00061),
                    (bore - 0.00065, 0),
                    (bore + 0.00008, 0.00061),
                )
            ]
        )
    surface(s, b, key + "_thread", pos, sections, color, finish="steel")


def workshop_parts(s, b):
    rng = _layout(s, b)
    side = s.cargo_layout_side
    x = side * -0.0025 + rng.uniform(-0.002, 0.002)
    y = rng.uniform(-0.002, 0.002)
    p = (x, y, 0.006)
    band(s, b, "bearing_outer", p, 0.029, 0.024, 0.014, "#aebabe")
    band(s, b, "bearing_inner", p, 0.0158, 0.0108, 0.014, "#b9c4c7")
    # Open upper race exposes polished balls seated in a brass retainer.
    band(s, b, "bearing_race", p, 0.0242, 0.0156, 0.0065, "#595c58")
    band(s, b, "bearing_cage", (x, y, 0.013), 0.0227, 0.017, 0.0018, "#ba9157")
    for i in range(10):
        a = 2 * math.pi * i / 10
        ball = s.ell(
            b,
            (x + 0.0199 * math.cos(a), y + 0.0199 * math.sin(a), 0.0155),
            (0.0039, 0.0039, 0.0039),
            "#c4cbd0",
        )
        if hasattr(s, "asset"):
            ball.set("material", finish_material(s, "#c4cbd0", "steel"))
    groups = [_disc_proxy(s, x, y, 0.0288, 0.014)]
    for key, x, y, radius, bore, h, color, hexagon in (
        ("locknut", -0.075, -0.025, 0.013, 0.006, 0.010, "#9aa7af", True),
        ("washer", -0.0525, 0, 0.015, 0.0068, 0.003, "#c28b5c", False),
        ("brass_nut", 0.0125, 0.0475, 0.016, 0.0075, 0.012, "#c7a26b", True),
    ):
        x = x * side + rng.uniform(-0.002, 0.002)
        y += rng.uniform(-0.002, 0.002)
        band(s, b, key, (x, y, 0.006), radius, bore, h, color, hexagon)
        if hexagon:
            _internal_thread(s, b, key, (x, y, 0.006), bore, h, color)
        groups.append(_disc_proxy(s, x, y, radius * (0.90 if hexagon else 0.99), h))
    return groups


def _swatch(s, b, x, y, angle):
    # Sweep transverse sections along a single folded piece. The lower length
    # lies flat and doubles back over a rounded fold with an oblique loose end.
    co, si = math.cos(angle), math.sin(angle)

    def point(u, v, z):
        return (x + co * u - si * v, y + si * u + co * v, z)

    edges = []
    for i in range(11):
        t = i / 10
        v = -0.020 + t * 0.040
        ripple = 0.0015 * math.sin(2 * math.pi * t + 0.6)
        lower_end = -0.037 + 0.004 * t + ripple
        bend = 0.028 - 0.005 * t + ripple
        tip = -0.024 + 0.032 * t + 0.002 * math.sin(4 * t)
        peak = 0.016 + 0.006 * math.sin(math.pi * t)
        edges.append(
            [
                (lower_end, v, 0.007),
                (bend - 0.012, v, 0.007),
                (bend, v, 0.008),
                (bend + 0.0055, v, 0.011),
                (bend + 0.004, v, 0.015),
                (bend - 0.002, v, 0.0175),
                (bend - 0.010, v, 0.016),
                ((bend - 0.010 + tip) / 2, v, peak),
                (tip, v, 0.0095 + 0.002 * math.sin(4 * t) ** 2),
            ]
        )

    # Each segment is a ribbon along the width with a real selvage thickness.
    # A narrow contrasting hem follows the slanted end and a darker underface
    # is exposed to the left of the fold.
    # Arc length along each row preserves the print through the fold.
    paths = [[0.0] for _ in edges]
    for path, row in zip(paths, edges):
        for a, b1 in zip(row, row[1:]):
            path.append(path[-1] + math.dist(a, b1))
    fabric = textile.cotton(s) if hasattr(s, "asset") else None
    for k in range(len(edges[0]) - 1):
        slices = []
        uv = []
        for row, path in zip(edges, paths):
            u0, v0, z0 = row[k]
            u1, v1, z1 = row[k + 1]
            v = (v0 + 0.022) / 0.044
            a, c = path[k] / 0.15, path[k + 1] / 0.15
            uv.append([(a, v), (a, v), (c, v), (c, v)][:: 1 if u1 > u0 else -1])
            slices.append(
                [
                    point(u0, v0, z0 - 0.0009),
                    point(u0, v0, z0 + 0.0009),
                    point(u1, v1, z1 + 0.0009),
                    point(u1, v1, z1 - 0.0009),
                ][:: 1 if u1 > u0 else -1]
            )
        # Unique geometry depends on this mat's pose. Keep names separate
        # because the two cloth pieces share the enclosing MuJoCo asset list.
        surface(
            s,
            b,
            f"cotton_{b.get('name')}_{k}",
            (0, 0, 0),
            slices,
            "#dda390",
            uv=uv,
            material=fabric,
        )
    for i in range(10):
        u, v, z = edges[i][-1]
        un, vn, zn = edges[i + 1][-1]
        s.rod(
            b,
            point(u + 0.0018, v, z + 0.0015),
            point(
                u * 0.35 + un * 0.65 + 0.0018, v * 0.35 + vn * 0.65, z * 0.35 + zn * 0.65 + 0.0015
            ),
            0.0008,
            "#f6d7ab",
        )
    proxy = s.box(ET.Element("body"), (x, y, 0.011), (0.066, 0.037, 0.010), "#777777")
    proxy.set("quat", fmt((math.cos(angle / 2), 0, 0, math.sin(angle / 2))))
    return [proxy]


def _winding(s, b, x, y, thread, angle):
    if not hasattr(s, "asset"):
        return
    # Each section follows the radial cross section of the wound cotton.
    # The first and last sections share a seam with independent UV endpoints.
    profile = [
        (0.0100, 0),
        (0.0138, 0),
        (0.0144, 0.00045),
        (0.0147, 0.0028),
        (0.0148, 0.010),
        (0.0148, 0.016),
        (0.0146, 0.022),
        (0.0142, 0.0242),
        (0.0137, 0.0248),
        (0.0100, 0.0248),
    ]
    sections, uv = [], []
    for i in range(65):
        a = math.tau * i / 64
        sections.append([(r * math.cos(a), r * math.sin(a), z) for r, z in profile])
        uv.append([(i / 64, z / 0.0248) for r, z in profile])
    geom = surface(
        s,
        b,
        "thread_pack",
        (x, y, 0.0098),
        sections,
        thread,
        uv=uv,
        material=textile.wound_thread(s, thread),
        cap_ends=False,
    )
    geom.set("quat", fmt((math.cos(angle / 2), 0, 0, math.sin(angle / 2))))


def sewing_supplies(s, b):
    rng = _layout(s, b)
    groups = []
    for x, y, thread in (
        (-0.0225, 0.010, "#ad603d"),
        (-0.070, 0.010, "#385a70"),
    ):
        x = x * s.cargo_layout_side + rng.uniform(-0.002, 0.002)
        y += rng.uniform(-0.002, 0.002)
        band(s, b, "spool_core", (x, y, 0.0088), 0.010, 0.0041, 0.0255, "#bd9465", finish="matte")
        for z in (0.006, 0.034):
            band(s, b, "spool_end", (x, y, z), 0.017, 0.004, 0.003, "#ddba86", finish="matte")
        _winding(s, b, x, y, thread, rng.uniform(0, 2 * math.pi))
        groups.append(_disc_proxy(s, x, y, 0.0168, 0.031))
    groups.append(
        _swatch(
            s,
            b,
            s.cargo_layout_side * 0.045 + rng.uniform(-0.002, 0.002),
            0.020 + rng.uniform(-0.002, 0.002),
            rng.uniform(-0.08, 0.08),
        )
    )
    return groups


def closed_kit(s, b):
    rounded_solid(s, b, "tin_lower", (0, 0, 0), 0.164, 0.099, 0.030, 0.012, "#5f7876", "enamel")
    rounded_solid(s, b, "tin_lip", (0, 0, 0.0285), 0.166, 0.101, 0.0035, 0.012, "#b6b4a3", "steel")
    rounded_solid(s, b, "tin_lid", (0, 0, 0.032), 0.167, 0.102, 0.009, 0.012, "#89a39a", "enamel")
    rounded_solid(
        s, b, "tin_stamp", (0, 0, 0.0404), 0.142, 0.078, 0.0015, 0.009, "#92aca2", "enamel"
    )
    # Screen-printed scissor emblem on the raised panel of the sewing tin.
    for side in (-1, 1):
        band(
            s,
            b,
            "tin_emblem_eye",
            (-0.019, side * 0.008, 0.04195),
            0.0065,
            0.0048,
            0.0004,
            "#56716a",
            finish="matte",
        )
        s.rod(b, (-0.014, side * 0.006, 0.0422), (0.022, -side * 0.008, 0.0422), 0.0011, "#56716a")
    s.cyl(b, (0.001, 0, 0.0426), 0.0016, 0.0007, "#c2aa83")
    for x in (-0.050, 0.050):
        s.rod(b, (x - 0.011, 0.05, 0.031), (x + 0.011, 0.05, 0.031), 0.0028, "#b4aaa0")
    rounded_solid(
        s, b, "tin_clasp", (0, -0.051, 0.020), 0.026, 0.004, 0.017, 0.0016, "#c2b49c", "steel"
    )
    s.rod(b, (-0.009, -0.053, 0.023), (0.009, -0.053, 0.023), 0.002, "#796e61")
