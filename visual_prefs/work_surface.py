"""A die-cut work surface with a radiused edge and registered metric printing."""

import math
import xml.etree.ElementTree as ET

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .scene import fmt

WIDTH, DEPTH, HEIGHT = 0.185, 0.141, 0.006


def _print(color, sewing):
    # Four texels per millimetre. The rules are printed in physical mm so two
    # layout colors have identical marks. No symbol encodes project status.
    w, h = 740, 564
    base = np.array(tuple(bytes.fromhex(color[1:])), dtype=float)
    noise = np.random.default_rng(74).normal(0, 1.6, (h, w, 1))
    image = Image.fromarray(np.uint8(np.clip(base + noise, 0, 255)))
    draw = ImageDraw.Draw(image)
    ink = tuple(np.uint8(0.65 * base + 0.35 * 225))
    major = tuple(np.uint8(0.43 * base + 0.57 * 232))
    border = 22
    draw.rounded_rectangle(
        (border, border, w - border, h - border), radius=10, outline=ink, width=2
    )
    for axis, end in enumerate((w, h)):
        for i, pos in enumerate(range(border + 12, end - border - 5, 4)):
            tick = 12 if i % 10 == 0 else 7 if i % 5 == 0 else 3
            if axis == 0:
                draw.line((pos, border, pos, border + tick), fill=major)
            else:
                draw.line((border, pos, border + tick, pos), fill=major)
    if sewing:
        for x in range(border + 12, w - border, 40):
            draw.line((x, border + 14, x, h - border), fill=ink)
        for y in range(border + 12, h - border, 40):
            draw.line((border + 14, y, w - border, y), fill=ink)
        font = ImageFont.load_default(size=12)
        for i in range(2, 17, 2):
            draw.text(
                (border + 12 + i * 40, h - border - 13), str(i), fill=major, font=font, anchor="mm"
            )
    # The separate UV of the perimeter samples this unprinted elastomer edge.
    draw.rectangle((0, 0, 6, 6), fill=tuple(np.uint8(0.52 * base)))
    return image


def work_surface(s, b, color, sewing):
    base = s.box(b, (0, 0, HEIGHT / 2), (WIDTH, DEPTH, HEIGHT), color)
    # This envelope is also used by the human support solver and contact QA.
    base.set("group", "3")
    base.set("rgba", "0 0 0 0")
    if not hasattr(s, "asset"):
        return base
    mesh = "radiused_work_surface"
    if s.asset.find(f"mesh[@name='{mesh}']") is None:
        verts, faces = [], []
        radius = 0.006
        for inset, z in ((0.001, 0), (0, 0.001), (0, 0.0048), (0.0012, HEIGHT)):
            for j, (sx, sy) in enumerate(((1, 1), (-1, 1), (-1, -1), (1, -1))):
                for k in range(7):
                    a = (j + k / 6) * math.pi / 2
                    verts.append(
                        (
                            sx * (WIDTH / 2 - radius) + (radius - inset) * math.cos(a),
                            sy * (DEPTH / 2 - radius) + (radius - inset) * math.sin(a),
                            z,
                        )
                    )
        count = len(verts) // 4
        uv = [(0.003, 0.997)] * (3 * count) + [
            (x / WIDTH + 0.5, y / DEPTH + 0.5) for x, y, _ in verts[-count:]
        ]
        for j in range(3):
            for i in range(count):
                a, h = j * count + i, j * count + (i + 1) % count
                faces.extend(((a, h, h + count), (a, h + count, a + count)))
        for i in range(1, count - 1):
            faces.extend(((0, i + 1, i), (3 * count, 3 * count + i, 3 * count + i + 1)))
        ET.SubElement(
            s.asset,
            "mesh",
            name=mesh,
            vertex=fmt(np.ravel(verts)),
            face=" ".join(map(str, np.ravel(faces))),
            texcoord=fmt(np.ravel(uv)),
        )
    material = f"work_surface_{int(sewing)}_{color[1:]}"
    if s.asset.find(f"material[@name='{material}']") is None:
        s._texture(material, _print(color, sewing), fingerprint=True)
    ET.SubElement(
        b, "geom", type="mesh", mesh=mesh, material=material, contype="0", conaffinity="0"
    )
    return base
