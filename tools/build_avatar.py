"""Build Rocketbox runtime data and a texture-packed, editable Blender project.

Run with bpy==4.3.0, numpy<2, and Pillow. --cache caches pinned upstream inputs.
"""

import argparse
import json
from pathlib import Path
from urllib.request import urlretrieve

import bpy
import numpy as np
from PIL import Image

REV = "0943055db6ec570bcef9f2c8b41c9e5467c808f9"
BASE = f"https://raw.githubusercontent.com/microsoft/Microsoft-Rocketbox/{REV}"
MODEL = "Assets/Avatars/Adults/Male_Adult_01"
PARTS = ("body", "head", "opacity")
ROOT = Path(__file__).resolve().parents[1]


def source(cache, relative):
    path = cache / Path(relative).name
    if not path.exists():
        urlretrieve(f"{BASE}/{relative}", path)
    return path


def semantic_bones():
    mapping = dict(
        pelvis="Pelvis", spine="Spine", spine_mid="Spine1", chest="Spine2", neck="Neck", head="Head"
    )
    for side, short in (("left", "L"), ("right", "R")):
        for key, bone in (
            ("clavicle", "Clavicle"),
            ("upper_arm", "UpperArm"),
            ("forearm", "Forearm"),
            ("hand", "Hand"),
            ("thigh", "Thigh"),
            ("calf", "Calf"),
            ("foot", "Foot"),
            ("toe", "Toe0"),
        ):
            mapping[f"{side}_{key}"] = f"{short} {bone}"
        for i, finger in enumerate(("thumb", "index", "middle", "ring", "pinky")):
            for joint, suffix in enumerate(("", "1", "2"), 1):
                mapping[f"{side}_{finger}_{joint}"] = f"{short} Finger{i}{suffix}"
    return {key: "Bip01 " + name for key, name in mapping.items()}


def build(cache, out, project):
    project.mkdir(parents=True, exist_ok=True)
    out.mkdir(parents=True, exist_ok=True)
    cache.mkdir(parents=True, exist_ok=True)
    (out / "LICENSE.md").write_bytes(source(cache, "LICENSE.md").read_bytes())
    (project / "LICENSE.md").write_bytes((out / "LICENSE.md").read_bytes())
    fbx = source(cache, f"{MODEL}/Export/Male_Adult_01.fbx")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(fbx), use_anim=False, use_image_search=False)
    obj = next(o for o in bpy.context.scene.objects if o.type == "MESH")
    arm = next(o for o in bpy.context.scene.objects if o.type == "ARMATURE")
    mesh = obj.data
    atlas = Image.new("RGBA", (2048, 2048))
    offsets = [(0, 0), (1024, 0), (0, 1024)]
    material_indices = []
    for mat in mesh.materials:
        part = mat.name.split("_")[-1]
        index = PARTS.index(part)
        material_indices.append(index)
        path = source(cache, f"{MODEL}/Textures/m002_{part}_color.tga")
        with Image.open(path) as source_image:
            tile = source_image.convert("RGBA").resize((1024, 1024), Image.Resampling.LANCZOS)
            atlas.paste(tile, offsets[index])
        mat.use_nodes = True
        mat.node_tree.nodes.clear()
        nodes, links = mat.node_tree.nodes, mat.node_tree.links
        output = nodes.new("ShaderNodeOutputMaterial")
        shader = nodes.new("ShaderNodeBsdfPrincipled")
        image = nodes.new("ShaderNodeTexImage")
        image.image = bpy.data.images.load(str(path))
        image.image.pack()
        links.new(image.outputs["Color"], shader.inputs["Base Color"])
        if part == "opacity":
            links.new(image.outputs["Alpha"], shader.inputs["Alpha"])
        links.new(shader.outputs["BSDF"], output.inputs["Surface"])
    atlas.save(out / "albedo.png")
    # Remove unused FBX path placeholders before saving the packed project.
    for image in list(bpy.data.images):
        if image.users == 0:
            bpy.data.images.remove(image)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(project / "avatar.blend"), compress=True)

    bones = list(arm.data.bones)
    names = [b.name for b in bones]
    parents = [names.index(b.parent.name) if b.parent else -1 for b in bones]
    matrices = np.stack([np.array(arm.matrix_world @ b.matrix_local) for b in bones])
    # FBX armature object carries a uniform centimeter-to-meter conversion.
    matrices[:, :3, :3] /= np.linalg.norm(matrices[:, :3, :3], axis=1, keepdims=True)
    positions = np.array([obj.matrix_world @ v.co for v in mesh.vertices])
    ankles = [matrices[names.index("Bip01 " + s + " Foot"), :3, 3] for s in ("L", "R")]
    origin = np.mean(ankles, axis=0)
    origin[2] = positions[:, 2].min()
    positions -= origin
    matrices[:, :3, 3] -= origin
    weights = np.zeros((len(positions), len(bones)))
    for vertex in mesh.vertices:
        for g in vertex.groups:
            name = obj.vertex_groups[g.group].name
            if name in names:
                weights[vertex.index, names.index(name)] = g.weight

    # Separate UV-seam vertices. Cut opacity cards into smaller triangles and
    # discard transparent pieces for renderers exposing RGB-only skin textures.
    mesh.calc_loop_triangles()
    vertices, texcoords, weights_out, triangles, materials = [], [], [], [], []
    cache_vertex = {}
    alpha = np.asarray(atlas)[:, :, 3]

    def emit(corners, material, depth):
        if material == 2 and depth:
            a, b, c = corners
            ab, bc, ca = (a + b) / 2, (b + c) / 2, (c + a) / 2
            for sub in ((a, ab, ca), (ab, b, bc), (ca, bc, c), (ab, bc, ca)):
                emit(sub, material, depth - 1)
            return
        if material == 2:
            u, v = np.mean(corners, axis=0)[3:5]
            if alpha[int(v * 2048), int(u * 2048)] < 110:
                return
        face = []
        for corner in corners:
            key = corner.round(7).tobytes()
            if key not in cache_vertex:
                cache_vertex[key] = len(vertices)
                vertices.append(corner[:3])
                texcoords.append(corner[3:5])
                weights_out.append(corner[5:])
            face.append(cache_vertex[key])
        triangles.append(face)
        materials.append(material)

    uv_data = mesh.uv_layers.active.data
    for tri in mesh.loop_triangles:
        material = material_indices[tri.material_index]
        offset = np.array(offsets[material]) / 2048
        corners = []
        for loop_id in tri.loops:
            vi = mesh.loops[loop_id].vertex_index
            u, v = uv_data[loop_id].uv
            uv = offset + np.array([u, 1 - v]) / 2
            corners.append(np.r_[positions[vi], uv, weights[vi]])
        emit(corners, material, 2)
    dense = np.array(weights_out)
    joints = np.argsort(-dense, axis=1)[:, :4]
    sparse = np.take_along_axis(dense, joints, axis=1)
    assert sparse.sum(axis=1).min() > 0
    sparse /= sparse.sum(axis=1, keepdims=True)
    np.savez_compressed(
        out / "avatar.npz",
        vertices=np.float32(vertices),
        triangles=np.int32(triangles),
        uv=np.float32(texcoords),
        joints=joints.astype(np.int16),
        weights=sparse.astype(np.float32),
        bone_names=names,
        parents=np.int16(parents),
        rest_world=matrices,
        material=np.uint8(materials),
        material_names=PARTS,
    )
    mapping = semantic_bones()
    assert set(mapping.values()) <= set(names)
    (out / "bones.json").write_text(json.dumps(mapping, indent=2) + "\n")
    print(len(vertices), "vertices,", len(triangles), "triangles,", len(bones), "bones")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=ROOT / "visual_prefs/data/human")
    parser.add_argument("--project", type=Path, default=ROOT / "assets/human")
    args = parser.parse_args()
    build(args.cache.resolve(), args.out.resolve(), args.project.resolve())
