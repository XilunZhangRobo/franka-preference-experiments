"""Build a metric tabletop scene around the original articulated Panda mesh."""

import xml.etree.ElementTree as ET
from hashlib import sha256
from io import BytesIO
from math import pi
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .assets import asset_dir


def fmt(values):
    return " ".join(f"{x:.7g}" for x in values)


def rgba(color):
    return fmt([int(color[i : i + 2], 16) / 255 for i in (1, 3, 5)] + [1])


def png(image):
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


class Scene:
    table_z = 0.75
    tabletop_center = (0, -0.18, 0.726)
    tabletop_size = (1.16, 0.90, 0.048)

    def __init__(self, room="workroom"):
        panda = asset_dir().resolve()
        if not (panda / "panda.xml").is_file():
            raise FileNotFoundError("Install the robot mesh with 'franka-prefs assets'.")
        self.root = ET.parse(panda / "panda.xml").getroot()
        self.root.find("compiler").set("meshdir", str(panda / "assets"))
        self.world = self.root.find("worldbody")
        self.asset = self.root.find("asset")
        self.files = {}
        self.props = {}
        self.grasps = {}
        self.human_grasps = {}
        self.switches = {}
        self.sounds = {}
        self.avatar = None
        self.guests = []
        self.world.find("body[@name='link0']").attrib.update(
            pos="0 -.50 .75", euler=f"0 0 {pi / 2}"
        )
        hand = self.world.find(".//body[@name='hand']")
        ET.SubElement(hand, "site", name="pinch", pos="0 0 .102", size=".002", rgba="0 0 0 0")
        for parent in self.world.iter():
            for light in parent.findall("light"):
                parent.remove(light)
        visual = ET.SubElement(self.root, "visual")
        ET.SubElement(visual, "global", offwidth="1280", offheight="960")
        ET.SubElement(visual, "quality", shadowsize="4096", offsamples="4")
        ET.SubElement(visual, "map", shadowscale=".7")
        ET.SubElement(
            visual,
            "headlight",
            ambient=".31 .31 .31",
            diffuse=".26 .26 .26",
            specular=".09 .09 .09",
        )
        with Image.open(
            Path(__file__).parent / "data/materials/wood_table_001_diff_1k.jpg"
        ) as texture:
            self._texture("grain", texture)
        wall = {"sewing": "#b9c7ba", "shared": "#c9c2b6"}.get(room, "#c0b9ac")
        self.box(self.world, (0, 1.15, 1.25), (3.6, 0.06, 2.5), wall)
        self.box(self.world, (-1.65, 0, 1.25), (0.06, 3.1, 2.5), "#aab5b2")
        self.box(self.world, (0, 0, -0.03), (4, 4, 0.06), "#777b73")
        top = self.box(self.world, self.tabletop_center, self.tabletop_size, "#ffffff")
        top.set("material", "grain")
        for x in (-0.52, 0.52):
            for y in (-0.54, 0.215):
                self.box(self.world, (x, y, 0.35), (0.046, 0.046, 0.70), "#3e4749")
        # A cabinet and backsplash give perspective without labeling task objects.
        self.box(self.world, (-0.10, 0.86, 0.42), (1.65, 0.33, 0.84), "#83948a")
        for x in (-0.69, -0.29, 0.11, 0.51):
            self.box(self.world, (x, 0.686, 0.45), (0.38, 0.02, 0.64), "#adb7aa")
            self.box(self.world, (x + 0.08, 0.667, 0.67), (0.09, 0.018, 0.012), "#4d5654")
        self.box(self.world, (-0.10, 0.86, 0.855), (1.70, 0.36, 0.03), "#dbd5c8")
        if room == "sewing":
            # Fabric bolts and thread spools distinguish this room in RGB.
            for i, color in enumerate(("#7a5268", "#36635d", "#b9a587", "#5f7188")):
                x = 0.34 + i * 0.085
                self.box(self.world, (x, 0.82, 1.01), (0.063, 0.14, 0.28), color)
                self.box(self.world, (x, 0.745, 1.03), (0.064, 0.008, 0.035), "#d4c7a8")
            for i, color in enumerate(("#ac6a66", "#7f9e96", "#c4ae74")):
                x = -0.63 + i * 0.078
                self.cyl(self.world, (x, 0.79, 0.912), 0.026, 0.076, color)
                for end in (0.874, 0.951):
                    self.cyl(self.world, (x, 0.79, end), 0.033, 0.006, "#c1a77e")
        elif room == "kitchen":
            for i in range(12):
                self.box(
                    self.world, (-0.92 + i * 0.16, 1.105, 1.02), (0.157, 0.013, 0.245), "#c9d2c9"
                )
            for i, tone in enumerate(("#e2d4c0", "#bc816d", "#dad0ae")):
                self.cyl(self.world, (0.31 + i * 0.095, 0.80, 0.938), 0.042, 0.134, tone)
                self.cyl(self.world, (0.31 + i * 0.095, 0.80, 1.009), 0.046, 0.010, "#817661")
        elif room in ("shared", "studio"):
            for i, tone in enumerate(("#6b8c94", "#a3786a", "#d2c599", "#818778")):
                self.box(
                    self.world,
                    (-0.68 + i * 0.044, 0.80, 0.984),
                    (0.037, 0.12, 0.22 + i * 0.012),
                    tone,
                )
            self.box(self.world, (0.50, 1.098, 1.44), (0.43, 0.032, 0.30), "#7d6c55")
            self.box(self.world, (0.50, 1.078, 1.44), (0.39, 0.012, 0.26), "#ddd3b8")
            self.box(self.world, (0.47, 1.068, 1.43), (0.21, 0.006, 0.085), "#799487")
        ET.SubElement(
            self.world,
            "light",
            pos=".7 -.9 2.7",
            dir="-.25 .45 -1",
            directional="true",
            diffuse=".49 .47 .44",
            specular=".10 .10 .10",
        )
        ET.SubElement(
            self.world,
            "light",
            pos="-.6 .4 1.8",
            dir=".3 -.35 -1",
            directional="true",
            castshadow="false",
            diffuse=".22 .26 .30",
        )
        self.camera("agent", (0.76, -0.78, 1.59), (0, 0.07, 1.005), 46)
        self.camera("wide", (0.83, -1.36, 1.60), (0, 0.03, 1.02), 42)

    def camera(self, name, eye, look, fov):
        back = np.array(eye) - look
        back /= np.linalg.norm(back)
        right = np.cross((0, 0, 1), back)
        right /= np.linalg.norm(right)
        ET.SubElement(
            self.world,
            "camera",
            name=name,
            pos=fmt(eye),
            xyaxes=fmt((*right, *np.cross(back, right))),
            fovy=str(fov),
        )

    def inspection_camera(self, item):
        """A close-up at the initial prop position for off-line asset inspection."""
        origin = np.fromstring(self.props[item].get("pos"), sep=" ")
        self.camera("inspection", origin + (0.128, -0.245, 0.192), origin + (0, 0, 0.025), 33)

    def _texture(self, name, image, *, fingerprint=False):
        content = png(image)
        suffix = "_" + sha256(content).hexdigest()[:16] if fingerprint else ""
        filename = name + suffix + ".png"
        self.files[filename] = content
        ET.SubElement(self.asset, "texture", name=name, type="2d", file=filename)
        ET.SubElement(
            self.asset, "material", name=name, texture=name, specular=".08", shininess=".1"
        )

    def label(self, body, xyz, text, width, height):
        image = Image.new("RGB", (512, 192), "#eee9d8")
        draw = ImageDraw.Draw(image)
        font = ImageFont.load_default(size=51)
        for line in text.splitlines():
            while draw.textlength(line, font=font) > 485:
                font = ImageFont.load_default(size=font.size - 1)
        draw.multiline_text((256, 96), text, fill="#182e39", font=font, anchor="mm", align="center")
        name = f"print_{len(self.files)}"
        self._texture(name, image)
        g = self.box(body, xyz, (width, 0.0008, height), "#ffffff")
        g.set("material", name)
        return g

    def prop(self, name, xyz):
        if name in self.props:
            raise ValueError(f"Duplicate prop {name}")
        body = ET.SubElement(self.world, "body", name=name, mocap="true", pos=fmt(xyz))
        self.props[name] = body
        return body

    def grasp(self, name, xyz):
        self.grasps[name] = np.asarray(xyz, dtype=float)

    def switch(self, item, light_name):
        self.switches[item] = light_name
        self.world.find(f"light[@name='{light_name}']").set("active", "false")

    def sound(self, item, text):
        self.sounds[item] = text

    def person(self, x=0, y=0.44, yaw=0):
        from .avatar import Avatar

        self.avatar = Avatar(self, x, y, yaw)
        return self.avatar

    def rest_hand(self, side, xyz):
        self.avatar.rest[side] = np.asarray(xyz, dtype=float)

    def guest(self, x, y, yaw=0):
        from .avatar import Avatar

        self.guests.append(Avatar(self, x, y, yaw, index=len(self.guests) + 1))

    @staticmethod
    def _geom(body, kind, color, **attrs):
        return ET.SubElement(
            body, "geom", type=kind, contype="0", conaffinity="0", rgba=rgba(color), **attrs
        )

    def box(self, body, xyz, full_size, color):
        return self._geom(body, "box", color, pos=fmt(xyz), size=fmt(np.asarray(full_size) / 2))

    def ell(self, body, xyz, radii, color):
        return self._geom(body, "ellipsoid", color, pos=fmt(xyz), size=fmt(radii))

    def cyl(self, body, xyz, radius, height, color):
        return self._geom(body, "cylinder", color, pos=fmt(xyz), size=fmt((radius, height / 2)))

    def rod(self, body, start, end, radius, color):
        return self._geom(body, "capsule", color, fromto=fmt((*start, *end)), size=str(radius))
