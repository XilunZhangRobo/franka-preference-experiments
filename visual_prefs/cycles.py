"""Blender Cycles rendering of a posed MuJoCo scene; loaded only in the Blender runtime."""

import math
from pathlib import Path

import bpy
import mujoco
import numpy as np
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Matrix, Vector

from .assets import avatar_blend


def linear(value):
    return value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4


def pose(pos, rot):
    matrix = Matrix(np.asarray(rot).reshape(3, 3)).to_4x4()
    matrix.translation = Vector(pos)
    return matrix


def mesh(name, vertices, faces, normals=None):
    data = bpy.data.meshes.new(name)
    data.from_pydata(vertices.tolist(), [], faces.tolist())
    data.update()
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    if normals is not None:
        data.polygons.foreach_set("use_smooth", np.ones(len(faces), dtype=bool))
        data.normals_split_custom_set(normals.reshape(-1, 3).tolist())
    return obj


def apply_uv(obj, coords):
    layer = obj.data.uv_layers.new()
    layer.data.foreach_set("uv", np.ascontiguousarray(coords, dtype=np.float32).ravel())


def principled(name, rgba, rough=0.55, metal=0.0, texture=None, wood=False, alpha=False):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = [*(linear(float(c)) for c in rgba[:3]), 1]
    shader.inputs["Roughness"].default_value = rough
    shader.inputs["Metallic"].default_value = metal
    shader.inputs["Alpha"].default_value = float(rgba[3])
    if texture:
        tex = mat.node_tree.nodes.new("ShaderNodeTexImage")
        tex.image = bpy.data.images.load(str(texture), check_existing=True)
        if alpha:
            mat.node_tree.links.new(tex.outputs["Alpha"], shader.inputs["Alpha"])
        if wood:
            texcoord = mat.node_tree.nodes.new("ShaderNodeTexCoord")
            tex.projection = "BOX"
            mapping = mat.node_tree.nodes.new("ShaderNodeVectorRotate")
            mapping.rotation_type = "Z_AXIS"
            mapping.inputs["Angle"].default_value = math.pi / 2
            mat.node_tree.links.new(texcoord.outputs["Generated"], mapping.inputs["Vector"])
            mat.node_tree.links.new(mapping.outputs["Vector"], tex.inputs["Vector"])
            bump = mat.node_tree.nodes.new("ShaderNodeBump")
            bump.inputs["Strength"].default_value = 0.17
            bump.inputs["Distance"].default_value = 0.0008
            mat.node_tree.links.new(tex.outputs["Color"], bump.inputs["Height"])
            mat.node_tree.links.new(bump.outputs["Normal"], shader.inputs["Normal"])
        mat.node_tree.links.new(tex.outputs["Color"], shader.inputs["Base Color"])
    return mat


def capsule(radius, half):
    rings = [
        (radius * math.cos(t), center + radius * math.sin(t))
        for center, start in ((-half, -math.pi / 2), (half, 0))
        for t in np.linspace(start, start + math.pi / 2, 9)
    ]
    vertices, faces = [], []
    for r, z in rings:
        for t in np.arange(32) * math.tau / 32:
            vertices.append((r * math.cos(t), r * math.sin(t), z))
    for j in range(len(rings) - 1):
        for i in range(32):
            a, b = j * 32 + i, j * 32 + (i + 1) % 32
            faces.append((a, b, b + 32, a + 32))
    obj = mesh("capsule", np.array(vertices), np.array(faces))
    for poly in obj.data.polygons:
        poly.use_smooth = True
    return obj


def geometry(m, i):
    kind, size = m.geom_type[i], m.geom_size[i]
    typ = mujoco.mjtGeom
    if kind == typ.mjGEOM_MESH:
        k = m.geom_dataid[i]
        va, fa, na = m.mesh_vertadr[k], m.mesh_faceadr[k], m.mesh_normaladr[k]
        f = slice(fa, fa + m.mesh_facenum[k])
        normals = m.mesh_normal[na + m.mesh_facenormal[f]]
        obj = mesh(
            m.mesh(k).name, m.mesh_vert[va : va + m.mesh_vertnum[k]], m.mesh_face[f], normals
        )
        if m.mesh_texcoordnum[k] and m.mesh_facetexcoord[f].min() >= 0:
            apply_uv(obj, m.mesh_texcoord[m.mesh_texcoordadr[k] + m.mesh_facetexcoord[f]])
        return obj
    if kind == typ.mjGEOM_CAPSULE:
        return capsule(size[0], size[1])
    if kind == typ.mjGEOM_ELLIPSOID or kind == typ.mjGEOM_SPHERE:
        bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=1)
        obj = bpy.context.object
        obj.data.transform(
            Matrix.Diagonal([*(size if kind == typ.mjGEOM_ELLIPSOID else (size[0],) * 3), 1])
        )
        for poly in obj.data.polygons:
            poly.use_smooth = True
        return obj
    if kind == typ.mjGEOM_BOX:
        bpy.ops.mesh.primitive_cube_add(size=2)
        obj = bpy.context.object
        obj.data.transform(Matrix.Diagonal([*size, 1]))
        width = min(0.0022, min(size) * 0.14)
    elif kind == typ.mjGEOM_CYLINDER:
        bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=size[0], depth=2 * size[1])
        obj = bpy.context.object
        for poly in obj.data.polygons:
            poly.use_smooth = len(poly.vertices) == 4
        width = min(0.001, min(size[:2]) * 0.10)
    else:
        raise ValueError(f"Unsupported visible MuJoCo primitive {kind}")
    edge = obj.modifiers.new("Manufactured edge radius", "BEVEL")
    edge.width = width
    edge.segments = 3
    edge.harden_normals = True
    obj.modifiers.new("Surface normals", "WEIGHTED_NORMAL")
    return obj


class Hair:
    """Use the original alpha cards for Cycles' shadow and transparency rays."""

    def __init__(self, m, prefix, rig, obj, tex, root_offset):
        data = obj.data
        data.calc_loop_triangles()
        part = next(
            i for i, mat in enumerate(data.materials) if mat.name.startswith("m002_opacity")
        )
        triangles = [tri for tri in data.loop_triangles if tri.material_index == part]
        subset = sorted({v for tri in triangles for v in tri.vertices})
        index = {v: i for i, v in enumerate(subset)}
        faces = np.array([[index[v] for v in tri.vertices] for tri in triangles])
        self.obj = mesh(prefix + " original hair cards", np.zeros((len(subset), 3)), faces)
        layer = data.uv_layers.active.data
        apply_uv(
            self.obj, np.array([[layer[index].uv[:] for index in tri.loops] for tri in triangles])
        )
        self.obj.data.materials.append(
            principled("Hair strands", (1, 1, 1, 1), 0.63, texture=tex, alpha=True)
        )
        self.obj.data.polygons.foreach_set("use_smooth", np.ones(len(faces), dtype=bool))
        names = list(rig["bone_names"])
        bind = rig["rest_world"][:, :3, 3]
        points = np.array([obj.matrix_world @ data.vertices[v].co for v in subset]) - root_offset
        dense = np.zeros((len(subset), len(names)))
        for i, v in enumerate(subset):
            for g in data.vertices[v].groups:
                key = obj.vertex_groups[g.group].name
                if key in names:
                    dense[i, names.index(key)] = g.weight
        self.joints = np.argsort(-dense, axis=1)[:, :4]
        self.weights = np.take_along_axis(dense, self.joints, axis=1)
        self.weights /= self.weights.sum(axis=1, keepdims=True)
        self.offset = points[:, None, :] - bind[self.joints]
        self.ids = np.array([m.body(f"{prefix}_joint_{i}").id for i in range(len(names))])

    def update(self, d):
        positions = d.xpos[self.ids][self.joints]
        rotates = d.xmat[self.ids].reshape(-1, 3, 3)[self.joints]
        xyz = (
            (positions + np.einsum("vsij,vsj->vsi", rotates, self.offset))
            * self.weights[:, :, None]
        ).sum(axis=1)
        self.obj.data.vertices.foreach_set("co", xyz.astype(np.float32).ravel())
        self.obj.data.update()


class Cycles:
    def __init__(self, source, playback, args, temp):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        self.scene = bpy.context.scene
        self.scene.render.engine = "CYCLES"
        self.scene.cycles.samples = args.samples
        self.scene.cycles.use_denoising = True
        self.scene.cycles.max_bounces = 5
        self.scene.render.threads_mode = "FIXED"
        self.scene.render.threads = args.threads
        self.scene.render.resolution_x, self.scene.render.resolution_y = args.size
        self.scene.render.resolution_percentage = 100
        self.scene.view_settings.view_transform = "AgX"
        if args.device != "CPU":
            pref = bpy.context.preferences.addons["cycles"].preferences
            pref.compute_device_type = args.device
            pref.refresh_devices()
            devices = [d for d in pref.devices if d.type == args.device]
            if not devices:
                raise ValueError(f"No {args.device} Cycles device")
            for device in pref.devices:
                device.use = device in devices
            self.scene.cycles.device = "GPU"
        self.p = playback
        m = playback.model
        self.mjscene = mujoco.MjvScene(m, maxgeom=10000)
        self.opt = mujoco.MjvOption()
        self.opt.geomgroup[3] = 0
        self.cam = mujoco.MjvCamera()
        self.cam.type = mujoco.mjtCamera.mjCAMERA_FIXED
        self.cam.fixedcamid = m.camera(args.camera).id
        bpy.ops.object.camera_add()
        self.camera = bpy.context.object
        self.scene.camera = self.camera
        self.camera.data.sensor_fit = "VERTICAL"
        self.camera.data.sensor_height = 24.0
        fov = math.radians(m.cam_fovy[self.cam.fixedcamid])
        self.camera.data.lens = 12.0 / math.tan(fov / 2.0)
        self.camera.data.clip_start = 0.01
        texture_paths = {}
        for tex in source.asset.findall("texture"):
            filename = tex.get("file")
            if filename in source.files:
                path = temp / Path(filename).name
                path.write_bytes(source.files[filename])
                texture_paths[tex.get("name")] = path
        mats = {}
        self.objects = {}
        for i in range(m.ngeom):
            if m.geom_group[i] == 3:
                continue
            matid = m.geom_matid[i]
            color = m.geom_rgba[i]
            if matid >= 0 and np.array_equal(color, (0.5, 0.5, 0.5, 1.0)):
                color = m.mat_rgba[matid]
            if color[3] <= 0:
                continue
            name = m.mat(matid).name if matid >= 0 else "surface"
            k = (name, tuple(color))
            if k not in mats:
                material = source.asset.find(f"material[@name='{name}']")
                tex = texture_paths.get(material.get("texture")) if material is not None else None
                metal = 0.45 if name in ("metal", "silver") else 0.0
                rough = 0.34 if matid >= 0 and name != "grain" else 0.58
                if matid >= 0:
                    if m.mat_metallic[matid] >= 0:
                        metal = float(m.mat_metallic[matid])
                    if m.mat_roughness[matid] >= 0:
                        rough = float(m.mat_roughness[matid])
                mats[k] = principled(name, color, rough, metal, tex, wood=name == "grain")
            obj = geometry(m, i)
            obj.name = f"{i:03d} {m.body(m.geom_bodyid[i]).name} {obj.name}"
            obj.data.materials.append(mats[k])
            self.objects[i] = obj
        self.skins = []
        self.hair = []
        rig = np.load(Path(__file__).parent / "data/human/avatar.npz")
        with bpy.data.libraries.load(str(avatar_blend()), link=False) as (
            src,
            out,
        ):
            out.objects = [n for n in src.objects if n == "Bip01" or n.startswith("m002_hipoly")]
        arm = next(o for o in out.objects if o.type == "ARMATURE")
        hair_source = next(o for o in out.objects if o.type == "MESH")
        pelvis = list(rig["bone_names"]).index("Bip01 Pelvis")
        root_offset = (
            np.array(arm.matrix_world @ arm.data.bones["Bip01 Pelvis"].head_local)
            - rig["rest_world"][pelvis, :3, 3]
        )
        alpha_image = next(
            im for im in bpy.data.images if im.name.startswith("m002_opacity") and im.packed_file
        )
        hair_tex = temp / "hair.tga"
        hair_tex.write_bytes(alpha_image.packed_file.data)
        for i in range(m.nskin):
            a, n = m.skin_faceadr[i], m.skin_facenum[i]
            faces = m.skin_face[a : a + n][rig["material"] != 2]
            n = len(faces)
            self.hair.append(Hair(m, m.skin(i).name, rig, hair_source, hair_tex, root_offset))
            nvert = m.skin_vertnum[i]
            obj = mesh(m.skin(i).name, np.zeros((nvert, 3)), faces)
            obj.data.polygons.foreach_set("use_smooth", np.ones(n, dtype=bool))
            u = m.skin_texcoord[m.skin_texcoordadr[i] : m.skin_texcoordadr[i] + nvert].copy()
            u[:, 1] = 1 - u[:, 1]
            apply_uv(obj, u[faces])
            obj.data.materials.append(
                principled(
                    "Rocketbox skin and cloth",
                    (1, 1, 1, 1),
                    0.64,
                    texture=texture_paths["avatar_albedo"],
                )
            )
            self.skins.append(obj)
        self.task_lights = {}
        for light_name in source.switches.values():
            i = m.light(light_name).id
            bpy.ops.object.light_add(type="SPOT")
            obj = bpy.context.object
            obj.name = light_name
            obj.data.color = m.light_diffuse[i].tolist()
            obj.data.spot_size = math.radians(min(175, 2 * m.light_cutoff[i]))
            obj.data.spot_blend = 0.6
            self.task_lights[i] = obj
        self.scene.world = bpy.data.worlds.new("Daylight")
        self.scene.world.use_nodes = True
        sky = self.scene.world.node_tree.nodes.get("Background")
        sky.inputs["Color"].default_value = (0.73, 0.83, 1.0, 1.0)
        sky.inputs["Strength"].default_value = 0.30
        for name, loc, power, size, tint in (
            ("Window", (-1.5, -1.0, 2.6), 95, 1.20, (1.0, 0.91, 0.80)),
            ("Ceiling bounce", (1.8, -0.2, 2.35), 52, 1.65, (0.83, 0.90, 1.0)),
            ("Back light", (0.40, 0.88, 2.25), 27, 0.80, (1.0, 0.89, 0.74)),
        ):
            bpy.ops.object.light_add(type="AREA", location=loc)
            light = bpy.context.object
            light.name = name
            light.data.energy = power
            light.data.shape = "DISK"
            light.data.size = size
            light.data.color = tint
            light.rotation_euler = (
                (Vector((0, 0.05, 0.85)) - light.location).to_track_quat("-Z", "Y").to_euler()
            )

    def frame(self, path):
        m, d = self.p.model, self.p.data
        mujoco.mjv_updateScene(
            m, d, self.opt, None, self.cam, mujoco.mjtCatBit.mjCAT_ALL, self.mjscene
        )
        for i, obj in self.objects.items():
            obj.matrix_world = pose(d.geom_xpos[i], d.geom_xmat[i])
        xyz = self.mjscene.skinvert.reshape(-1, 3)
        for i, obj in enumerate(self.skins):
            a = m.skin_vertadr[i]
            obj.data.vertices.foreach_set("co", xyz[a : a + len(obj.data.vertices)].ravel())
            obj.data.update()
        for i, light in self.task_lights.items():
            light.location = d.light_xpos[i]
            light.rotation_euler = Vector(d.light_xdir[i]).to_track_quat("-Z", "Y").to_euler()
            light.data.energy = 12.0 if m.light_active[i] else 0.0
        for hair in self.hair:
            hair.update(d)
        camid = self.cam.fixedcamid
        self.camera.matrix_world = pose(d.cam_xpos[camid], d.cam_xmat[camid])
        bpy.context.view_layer.update()
        # Compare camera projections independently through Blender and a MuJoCo
        # pinhole projection for visible world-space geom centers.
        width, height = self.scene.render.resolution_x, self.scene.render.resolution_y
        focal = height / (2 * math.tan(math.radians(m.cam_fovy[camid]) / 2))
        errors = []
        for i in self.objects:
            v = (d.geom_xpos[i] - d.cam_xpos[camid]) @ d.cam_xmat[camid].reshape(3, 3)
            if v[2] >= -0.01:
                continue
            expected = np.array((width / 2 - focal * v[0] / v[2], height / 2 - focal * v[1] / v[2]))
            if not (0 <= expected[0] < width and 0 <= expected[1] < height):
                continue
            uv = world_to_camera_view(self.scene, self.camera, Vector(d.geom_xpos[i]))
            errors.append(np.linalg.norm(np.array((width * uv.x, height * uv.y)) - expected))
        if not errors:
            raise ValueError("No geom centers project onto the image for a camera check")
        error = float(max(errors))
        if error > 0.02:
            raise ValueError(f"Camera projection drift {error} pixels")
        self.scene.render.filepath = str(path)
        result = bpy.ops.render.render(write_still=True)
        if "FINISHED" not in result:
            raise RuntimeError(f"Cycles render did not finish: {result}")
        return error
