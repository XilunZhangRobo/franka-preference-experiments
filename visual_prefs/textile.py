"""Procedural cotton and wound-thread albedos in physical texture coordinates."""

import numpy as np
from PIL import Image


def _texture(scene, name, pixels):
    scene._texture(name, Image.fromarray(np.uint8(np.clip(pixels, 0, 255))), fingerprint=True)
    material = scene.asset.find(f"material[@name='{name}']")
    material.attrib.update(roughness=".91", metallic="0", specular=".05")
    return name


def cotton(scene):
    name = "cotton_woven_gingham"
    if scene.asset.find(f"material[@name='{name}']") is not None:
        return name
    # Texture axes span 150 x 44 mm of unrolled fabric. Red warp and weft
    # bands cross naturally: each crossing reveals whichever yarn is on top.
    v, u = np.mgrid[:384, :1280]
    x, y = u * (150 / 1280), v * (44 / 384)
    warp = x / 0.41 + 0.12 * np.sin(y * 0.7) + 0.06 * np.sin(0.24 * x + 0.49 * y)
    weft = y / 0.43 + 0.12 * np.sin(x * 0.42) + 0.07 * np.sin(0.42 * x - 0.38 * y)
    warp_float = (np.floor(warp) + np.floor(weft)) % 2
    ridge_x = np.sin(np.pi * warp) ** 2
    ridge_y = np.sin(np.pi * weft) ** 2
    select = np.clip(0.5 + (ridge_x - ridge_y) * 0.85 + (warp_float - 0.5) * 0.58, 0, 1)

    def dyed(axis):
        # Narrow paired overstripes border the broad dyed bands.
        pos = np.remainder(axis, 12)
        return np.where(pos < 5.2, 0.88, np.where((pos > 6.3) & (pos < 6.9), 0.58, 0.04))

    dye = select * dyed(x + 0.08 * np.sin(y * 0.75)) + (1 - select) * dyed(
        y + 0.08 * np.sin(x * 0.46)
    )
    cream = np.array([231.0, 191.0, 163.0])
    rose = np.array([158.0, 84.0, 86.0])
    pixels = cream + dye[:, :, None] * (rose - cream)
    fiber = (select * ridge_x + (1 - select) * ridge_y - 0.5) * 18
    fiber += 2 * np.sin(10.2 * x + 8 * y) + 1.5 * np.sin(13 * x - 6 * y)
    return _texture(scene, name, pixels + fiber[:, :, None])


def wound_thread(scene, color):
    name = f"wound_cotton_{color[1:]}"
    if scene.asset.find(f"material[@name='{name}']") is not None:
        return name
    v, u = np.mgrid[:384, :1024]
    # An outer traverse winds over the earlier turns, both at a fine pitch.
    # The periodic circumference joins the texture at the spindle seam.
    a, h = u / 1024, v / 384
    winding = h * 86 + 7 * a + 0.23 * np.sin(2 * np.pi * (3 * a + h))
    reverse = h * 82 - 9 * a + 0.16 * np.sin(2 * np.pi * (2 * a - h))
    outer = 0.5 + 0.5 * np.sin(2 * np.pi * winding)
    under = 0.5 + 0.5 * np.sin(2 * np.pi * reverse)
    strands = 28 * (outer - 0.5) + 14 * (under - 0.5) * (1 - outer)
    twist = 2 * np.sin(2 * np.pi * (91 * a + 11 * h)) + 2 * np.cos(2 * np.pi * (77 * a - 31 * h))
    base = np.array([int(color[i : i + 2], 16) for i in (1, 3, 5)])
    return _texture(scene, name, base + (strands + twist)[:, :, None])
