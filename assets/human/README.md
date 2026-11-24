# Textured civilian avatar

This is Male_Adult_01 from the Microsoft Rocketbox Avatar Library, originally created by Rocketbox and released by Microsoft under the MIT license. The input FBX and body, head, and opacity textures are pinned to commit 0943055db6ec570bcef9f2c8b41c9e5467c808f9. [Original character](https://github.com/microsoft/Microsoft-Rocketbox/tree/0943055db6ec570bcef9f2c8b41c9e5467c808f9/Assets/Avatars/Adults/Male_Adult_01) · [License](LICENSE.md)

The editable Blender 4.3 project contains the imported armature with 80 bones, weighted mesh, UVs, and packed original diffuse maps. The runtime atlas uses 1024-pixel tiles and the skin includes separate vertices at UV seams. Hair and eyelashes use small, alpha-tested triangles to approximate the source transparency on RGB-only renderers.

The runtime files are in `visual_prefs/data/human/`. The NPZ stores rest vertices in meters with Z up, the person's left along +X, and forward along −Y. The origin lies on the floor below the midpoint of the ankles. UV coordinates start at the image's top-left. Each vertex has four normalized bone weights. Rest-world matrices act on column vectors. Triangle material IDs correspond to the material_names array. The semantic names in bones.json index the original skeleton by bone name.

To rebuild from the repository root with Python 3.11:

```sh
uv run --python 3.11 --with bpy==4.3.0 --with 'numpy<2' --with pillow python tools/build_avatar.py --cache /tmp/rocketbox-male
```
