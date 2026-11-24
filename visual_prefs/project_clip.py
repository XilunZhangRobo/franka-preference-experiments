"""Metric foldback clip and the job ticket it grips on a removable work mat.

Clip sections and wire paths below use millimetres in the plane of the ticket.
Both mats carry the same card, slot and printed details. Only the steel changes.
"""

import math
import xml.etree.ElementTree as ET

import numpy as np

from .scene import fmt, rgba

WIDTH_MM = 41.0
# The short card stands in a groove at the rear corner of the mat opposite the recipient’s grasp. Its top
# enters the jaws and stops short of the inside of the folded steel crown.
CARD_Y = 0.040
CARD_TOP, JAW_Z = 0.047, 0.031
TILT = math.radians(-10)


def _mount(points):
    pts = np.array(points, dtype=float) * 0.001
    y, z = pts[..., 1].copy(), pts[..., 2].copy()
    pts[..., 1] = y * math.cos(TILT) - z * math.sin(TILT)
    pts[..., 2] = y * math.sin(TILT) + z * math.cos(TILT)
    return pts


def _corners(points, radius, samples=6):
    """Round successive bends with tangent quadratic arcs, retaining both ends."""
    pts = np.array(points, dtype=float)
    rounded = [pts[0]]
    for a, b, c in zip(pts, pts[1:], pts[2:]):
        before, after = a - b, c - b
        lengths = np.linalg.norm(before), np.linalg.norm(after)
        trim = min(radius, 0.45 * min(lengths))
        start, end = b + before * trim / lengths[0], b + after * trim / lengths[1]
        for t in np.linspace(0, 1, samples):
            rounded.append((1 - t) ** 2 * start + 2 * (1 - t) * t * b + t**2 * end)
    return np.array([*rounded, pts[-1]])


def _loft(s, b, name, sections, material, card_x):
    """Connect closed rings and cap each end. Meshes are cached across bodies."""
    if s.asset.find(f"mesh[@name='{name}']") is None:
        points = _mount(sections)
        count, sides = points.shape[:2]
        xyz = points.reshape(-1, 3)
        faces = []
        for j in range(count - 1):
            for i in range(sides):
                a, h = j * sides + i, j * sides + (i + 1) % sides
                faces.extend([(a, h, h + sides), (a, h + sides, a + sides)])
        for i in range(1, sides - 1):
            end = (count - 1) * sides
            faces.extend([(0, i + 1, i), (end, end + i, end + i + 1)])
        face = np.array(faces)
        a, c, d = xyz[face].transpose(1, 0, 2)
        if np.sum(a * np.cross(c, d)) < 0:
            face = face[:, ::-1]
        ET.SubElement(
            s.asset, "mesh", name=name, vertex=fmt(xyz.flat), face=" ".join(map(str, face.flat))
        )
    ET.SubElement(
        b,
        "geom",
        type="mesh",
        mesh=name,
        pos=fmt((card_x, CARD_Y, JAW_Z)),
        material=material,
        contype="0",
        conaffinity="0",
    )


def _spring(s, b, card_x):
    # Constant-thickness steel folded into an open channel. Curls at both
    # jaw lips leave a passage for the wire pivots. The ends stay visibly open.
    wall = _corners(
        [
            (-0.92, 0.25),
            (-0.92, 1.3),
            (-8.9, 17.4),
            (-8.6, 19.0),
            (8.6, 19.0),
            (8.9, 17.4),
            (0.92, 1.3),
            (0.92, 0.25),
        ],
        1.65,
    )
    tangent = np.gradient(wall, axis=0)
    normals = np.stack((-tangent[:, 1], tangent[:, 0]), axis=1)
    normals *= 0.23 / np.linalg.norm(normals, axis=1)[:, None]
    sections = []
    for point, normal in zip(wall, normals):
        front, back = point + normal, point - normal
        sections.append(
            [
                (-WIDTH_MM / 2, *front),
                (WIDTH_MM / 2, *front),
                (WIDTH_MM / 2, *back),
                (-WIDTH_MM / 2, *back),
            ]
        )
    _loft(s, b, "clip_folded_shell", sections, "clip_enamel", card_x)
    for side in (-1, 1):
        # Slits in the rolls let the bent wire protrude at the shoulders.
        for i, (lo, hi) in enumerate(((-20.5, -16), (-12, 12), (16, 20.5))):
            rings = []
            for angle in np.linspace(-0.14, math.radians(283), 28):
                rings.append(
                    [
                        (x, side * (2.64 - r * math.cos(angle)), 0.75 - r * math.sin(angle))
                        for x, r in ((lo, 1.85), (hi, 1.85), (hi, 1.39), (lo, 1.39))
                    ]
                )
            _loft(s, b, f"clip_rolled_lip_{side}_{i}", rings, "clip_enamel", card_x)


def _handle(s, b, side, card_x):
    # A single bent wire: pivot pins, raised shoulders, narrow neck and a
    # flared finger pad. Parallel transport avoids twists in the round sweep.
    half = [
        (-19.7, 2.64, 0.75),
        (-14.2, 2.64, 0.75),
        (-14.2, 4.15, 2.8),
        (-15.3, 10.6, 17.7),
        (-7.0, 13.0, 27.7),
        (-7.4, 14.0, 30.6),
        (-10.3, 15.4, 35.1),
        (-9.6, 16.1, 37.3),
        (-6.6, 16.6, 38.5),
    ]
    path = _corners(
        [(x, side * y, z) for x, y, z in half + [(-x, y, z) for x, y, z in half[::-1]]], 2.6
    )
    axes = np.gradient(path, axis=0)
    axes /= np.linalg.norm(axes, axis=1)[:, None]
    normal = np.array([0, 0, 1.0])
    rings = []
    angles = np.arange(12) * math.tau / 12
    for p, axis in zip(path, axes):
        normal = normal - axis * np.dot(normal, axis)
        normal /= np.linalg.norm(normal)
        binormal = np.cross(axis, normal)
        rings.append(
            p + 0.98 * (np.outer(np.cos(angles), normal) + np.outer(np.sin(angles), binormal))
        )
    _loft(s, b, f"clip_wire_{side}", rings, "clip_nickel", card_x)


def clip(s, b, card_x):
    if not hasattr(s, "asset"):
        return
    for name, color, spec, gloss, metal, rough in (
        ("clip_enamel", "#202428", ".58", ".44", ".25", ".27"),
        ("clip_nickel", "#d3d6d5", ".85", ".76", ".88", ".21"),
    ):
        if s.asset.find(f"material[@name='{name}']") is None:
            ET.SubElement(
                s.asset,
                "material",
                name=name,
                rgba=rgba(color),
                specular=spec,
                shininess=gloss,
                metallic=metal,
                roughness=rough,
            )
    _spring(s, b, card_x)
    for side in (-1, 1):
        _handle(s, b, side, card_x)


def job_ticket(s, b, card_x):
    """The same unlabelled drafting slip and holder on both candidate mats."""

    def on_card(x, y, z):
        return (
            card_x + x,
            CARD_Y + y * math.cos(TILT) - z * math.sin(TILT),
            JAW_Z + y * math.sin(TILT) + z * math.cos(TILT),
        )

    def strip(x, y, z, w, d, h, color):
        g = s.box(b, on_card(x, y, z), (w, d, h), color)
        g.set("quat", fmt((math.cos(TILT / 2), math.sin(TILT / 2), 0, 0)))
        return g

    upright = strip(0, 0, -0.003, 0.064, 0.00138, 2 * (CARD_TOP - JAW_Z + 0.003), "#ebe4d3")
    # A pair of shallow rails sandwich the bottom edge of the paper stack.
    for side in (-1, 1):
        s.box(
            b,
            (card_x, on_card(0, 0, -0.022)[1] + side * 0.0021, 0.0085),
            (0.068, 0.0028, 0.005),
            "#534e48",
        )
    # Quiet ruling typical of a shop traveler, consistent across both choices.
    for y in (-0.00078, 0.00078):
        for z in (-0.011, -0.006, 0.000, 0.009):
            strip(0, y, z, 0.052, 0.00010, 0.00034, "#8f9188")
        strip(-0.015, y, -0.001, 0.00040, 0.00010, 0.020, "#8f9188")
    return upright
