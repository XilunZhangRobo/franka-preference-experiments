"""Lofted, metric props shared by the workshop and household scenes."""

import math
import xml.etree.ElementTree as ET

import numpy as np

from .scene import fmt, rgba


def finish_material(s, color, finish):
    material = f"cargo_{finish}_{color[1:]}"
    if s.asset.find(f"material[@name='{material}']") is None:
        spec, shine = {"steel": (".68", ".52"), "enamel": (".32", ".3"), "matte": (".09", ".08")}[
            finish
        ]
        ET.SubElement(
            s.asset,
            "material",
            name=material,
            rgba=rgba(color),
            specular=spec,
            shininess=shine,
            metallic=".83" if finish == "steel" else ".0",
            roughness={"steel": ".29", "enamel": ".34", "matte": ".72"}[finish],
        )
    return material


def surface(
    s,
    b,
    key,
    xyz,
    sections,
    color,
    closed=False,
    finish="matte",
    *,
    uv=None,
    material=None,
    cap_ends=True,
):
    """Loft equal-length outlines, closing the ends or joining the final ring to the first."""
    if not hasattr(s, "asset"):
        return
    name = "cargo_" + key
    if s.asset.find(f"mesh[@name='{name}']") is None:
        points = [p for section in sections for p in section]
        faces = []
        n = len(sections[0])
        for i in range(len(sections) if closed else len(sections) - 1):
            j = (i + 1) % len(sections)
            for k in range(n):
                h = (k + 1) % n
                a, b0, c, d = i * n + k, i * n + h, j * n + h, j * n + k
                faces.extend((a, b0, c, a, c, d))
        if not closed and cap_ends:
            for k in range(1, n - 1):
                faces.extend(
                    (0, k + 1, k, len(points) - n, len(points) - n + k, len(points) - n + k + 1)
                )
        # Sweeps may advance along any axis. Orient closed meshes outwards so
        # native and path-traced normals agree even for pods swept along +Y.
        faces = np.reshape(faces, (-1, 3))
        a, b1, c = np.asarray(points)[faces].transpose(1, 0, 2)
        if np.sum(a * np.cross(b1, c)) < 0:
            faces = faces[:, ::-1]
        ET.SubElement(
            s.asset,
            "mesh",
            name=name,
            vertex=fmt(v for p in points for v in p),
            face=" ".join(map(str, faces.flat)),
            **({"texcoord": fmt(np.ravel(uv))} if uv is not None else {}),
        )
    material = material or finish_material(s, color, finish)
    return ET.SubElement(
        b,
        "geom",
        type="mesh",
        mesh=name,
        material=material,
        pos=fmt(xyz),
        contype="0",
        conaffinity="0",
    )


def ring(s, b, key, xyz, profile, color, sides=40, hexagon=False, finish="steel"):
    sections = []
    for radius, z, outer in profile:
        loop = []
        for i in range(sides):
            a = 2 * math.pi * i / sides
            r = radius
            if hexagon and outer:
                r *= math.cos(math.pi / 6) / math.cos(a % (math.pi / 3) - math.pi / 6)
            loop.append((r * math.cos(a), r * math.sin(a), z))
        sections.append(loop)
    surface(s, b, key, xyz, sections, color, closed=True, finish=finish)


def band(s, b, key, xyz, r, bore, h, color, hexagon=False, finish="steel"):
    chamfer = min(0.00085, h / 4, (r - bore) / 4)
    ring(
        s,
        b,
        key,
        xyz,
        [
            (r - chamfer, 0, 1),
            (r, chamfer, 1),
            (r, h - chamfer, 1),
            (r - chamfer, h, 1),
            (bore + chamfer, h, 0),
            (bore, h - chamfer, 0),
            (bore, chamfer, 0),
            (bore + chamfer, 0, 0),
        ],
        color,
        sides=48,
        hexagon=hexagon,
        finish=finish,
    )


def rounded_outline(w, d, r, z):
    points = []
    for j, (cx, cy) in enumerate(((1, 1), (-1, 1), (-1, -1), (1, -1))):
        for k in range(6):
            a = (j + k / 5) * math.pi / 2
            points.append(
                (cx * (w / 2 - r) + r * math.cos(a), cy * (d / 2 - r) + r * math.sin(a), z)
            )
    return points


def rounded_solid(s, b, key, xyz, width, depth, height, r, color, finish="matte"):
    sections = []
    bevel = min(height / 4, r / 3, 0.002)
    for inset, z in ((bevel, 0), (0, bevel), (0, height - bevel), (bevel, height)):
        loop = []
        for j, (cx, cy) in enumerate(((1, 1), (-1, 1), (-1, -1), (1, -1))):
            for i in range(6):
                a = (j + i / 5) * math.pi / 2
                loop.append(
                    (
                        cx * (width / 2 - r) + (r - inset) * math.cos(a),
                        cy * (depth / 2 - r) + (r - inset) * math.sin(a),
                        z,
                    )
                )
        sections.append(loop)
    surface(s, b, key, xyz, sections, color, finish=finish)
