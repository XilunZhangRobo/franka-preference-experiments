"""Cooked florets and bean pods at table scale. Firmness is a scripted shape cue."""

from math import cos, pi, sin
from random import Random

from .prop_mesh import surface


def _floret(scene, body, key, xyz, width, height, angle):
    # A compact, lobed head with bud-scale surface variation and a cut stem.
    sections = []
    for row in range(14):
        latitude = -1.34 + row * (2.82 / 13)
        ring = []
        for k in range(40):
            phi = 2 * pi * k / 40
            lobes = (
                1
                + 0.083 * cos(5 * phi + angle) * cos(latitude)
                + 0.05 * sin(8 * phi - 2 * latitude)
            )
            buds = 0.055 * sin(17 * phi + 0.7 * row) * cos(4.7 * row + 2 * phi)
            r = width * cos(latitude) * (lobes + buds)
            ring.append(
                (r * cos(phi), r * sin(phi), height * (sin(latitude) + 1) * (1 + 0.32 * buds))
            )
        sections.append(ring)
    surface(scene, body, key, xyz, sections, "#426b38")


def broccoli(scene, body, tender):
    stem = 0.011 if tender else 0.027
    spread = 0.016 if tender else 0.012
    sections = []
    for z, r in ((0, 0.007), (0.002, 0.0073), (stem * 0.55, 0.0055), (stem, 0.0036)):
        sections.append(
            [
                (r * (1 + 0.06 * cos(5 * a)) * cos(a), r * sin(a), z)
                for a in (i * 2 * pi / 24 for i in range(24))
            ]
        )
    surface(scene, body, f"floret_stalk_{int(tender)}", (0, 0, 0), sections, "#94ad69")
    for i, direction in enumerate((0.14, 1.4, 2.82, 3.91, 5.16, 0)):
        radius = spread if i < 5 else 0.001
        x, y = radius * cos(direction), radius * sin(direction)
        z = stem * 0.54 if i < 5 else stem * 0.9
        scene.rod(body, (0, 0, stem * 0.36), (x, y, z + 0.004), 0.0037, "#88a75e")
        _floret(
            scene,
            body,
            f"floret_{int(tender)}_{i}",
            (x, y, z),
            0.0115 if i < 5 else 0.014,
            (0.0057 if tender else 0.0085) * (1 + 0.1 * cos(direction)),
            direction,
        )


def beans(scene, body, tender):
    # Three distinct pods, with seams, seed bulges and tapered ends. Both
    # doneness conditions share the size, color, and pod-to-pod variation.
    rng = Random(156)
    for i, color in enumerate(("#77944e", "#678749", "#789450")):
        angle, length, phase = (
            rng.uniform(-0.11, 0.11),
            rng.uniform(0.063, 0.073),
            rng.uniform(0, 1),
        )
        rings = []
        for j in range(25):
            t = j / 24
            y = (t - 0.5) * length
            x = (0.0095 if tender else 0.002) * sin(pi * t) + angle * y
            radius = (
                0.0036 * (0.16 + 0.84 * sin(pi * t) ** 0.37) * (1 + 0.09 * cos(9 * pi * t + phase))
            )
            mid_z = radius * 0.79 + 0.0006 * sin(2 * pi * t) ** 2
            rings.append(
                [
                    (
                        x + radius * cos(a),
                        y,
                        mid_z + 0.78 * radius * sin(a) * (1 + 0.10 * cos(2 * a)),
                    )
                    for a in (k * 2 * pi / 14 for k in range(14))
                ]
            )
        surface(scene, body, f"bean_{int(tender)}_{i}", ((i - 1) * 0.012, 0, 0), rings, color)
