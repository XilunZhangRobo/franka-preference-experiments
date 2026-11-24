"""Render a Blender character's weighted skin and solve its tabletop reach."""

import json
import struct
from functools import lru_cache
from pathlib import Path
from xml.etree.ElementTree import SubElement

import mujoco
import numpy as np

ASSETS = Path(__file__).resolve().parent / "data" / "human"
SIDES = (("left", 1), ("right", -1))
DIGITS = ("index", "middle", "ring", "pinky", "thumb")


def _unit(v):
    return v / max(1e-10, np.linalg.norm(v))


def _rotation(axis, angle):
    x, y, z = _unit(np.asarray(axis, dtype=float))
    skew = np.array([[0, -z, y], [z, 0, -x], [-y, x, 0]])
    return np.eye(3) + np.sin(angle) * skew + (1 - np.cos(angle)) * (skew @ skew)


def _align(a, b):
    a, b = _unit(a), _unit(b)
    axis = np.cross(a, b)
    if np.linalg.norm(axis) < 1e-8:
        if a @ b > 0:
            return np.eye(3)
        axis = np.cross(a, (1, 0, 0) if abs(a[0]) < 0.8 else (0, 1, 0))
    return _rotation(axis, np.arccos(np.clip(a @ b, -1, 1)))


def _frame(forward, across):
    fwd = _unit(forward)
    normal = _unit(np.cross(fwd, across))
    return np.column_stack((fwd, np.cross(normal, fwd), normal))


def _binary_skin(rig, centers, prefix):
    """Encode bind translations and normalized glTF skin weights as MuJoCo SKN."""
    verts, faces = rig["vertices"], rig["triangles"]
    # The PNG loader and glTF agree on the orientation of image rows.
    uv = rig["uv"]
    chunks = []
    for i, center in enumerate(centers):
        rows, slots = np.where((rig["joints"] == i) & (rig["weights"] > 0))
        if rows.size:
            chunks.extend(
                (
                    struct.pack(
                        "<40s7fi", f"{prefix}_joint_{i}".encode(), *center, 1, 0, 0, 0, len(rows)
                    ),
                    rows.astype("<i4").tobytes(),
                    rig["weights"][rows, slots].astype("<f4").tobytes(),
                )
            )
    return b"".join(
        [
            struct.pack("<4i", len(verts), len(uv), len(faces), len(chunks) // 3),
            verts.astype("<f4").tobytes(),
            uv.astype("<f4").tobytes(),
            faces.astype("<i4").tobytes(),
            *chunks,
        ]
    )


@lru_cache(maxsize=1)
def _load():
    with np.load(ASSETS / "avatar.npz") as packed:
        rig = dict(packed)
    names = list(rig["bone_names"].astype(str))
    mapping = json.loads((ASSETS / "bones.json").read_text())
    ids = {k: names.index(v) if isinstance(v, str) else v for k, v in mapping.items()}
    centers = rig["rest_world"][:, :3, 3].astype(float)
    parents = rig["parents"]
    families = []
    for i in range(len(names)):
        family = [i]
        for parent in family:
            family.extend(np.flatnonzero(parents == parent).tolist())
        families.append(np.array(family))
    return rig, centers, ids, families, (ASSETS / "albedo.png").read_bytes()


@lru_cache(maxsize=4)
def _skin(prefix):
    rig, centers, *_ = _load()
    return _binary_skin(rig, centers, prefix)


def _surface_lift(triangles, center, half, top):
    """Minimum vertical translation to clear the horizontal box footprint."""
    lo, hi = center - half, center + half
    keep = (
        (triangles[:, :, 2].min(axis=1) < top)
        & (triangles[:, :, :2].max(axis=1) >= lo).all(axis=1)
        & (triangles[:, :, :2].min(axis=1) <= hi).all(axis=1)
    )
    t = triangles[keep]
    if not len(t):
        return 0.0
    # Clip each triangle polygon against the rectangle's four sides. Surviving
    # vertices include intersections of triangle edges and shelf edges.
    minimum = top
    for triangle in t:
        polygon = list(triangle)
        for axis, bound, sign in ((0, lo[0], 1), (0, hi[0], -1), (1, lo[1], 1), (1, hi[1], -1)):
            if not polygon:
                break
            clipped = []
            a = polygon[-1]
            for b in polygon:
                da, db = sign * (a[axis] - bound), sign * (b[axis] - bound)
                if (da >= 0) != (db >= 0):
                    clipped.append(a + (b - a) * (da / (da - db)))
                if db >= 0:
                    clipped.append(b)
                a = b
            polygon = clipped
        if polygon:
            minimum = min(minimum, min(v[2] for v in polygon))
    return top - minimum


class Avatar:
    def __init__(self, scene, x, y, yaw, index=0):
        rig, self.bind, self.joints, self.family, image = _load()
        self.prefix = "avatar" if index == 0 else f"guest{index}"
        self.origin = np.array((x, y, 0.0))
        self.yaw = _rotation((0, 0, 1), np.deg2rad(yaw))
        self.table = scene.table_z
        self.rest = {
            side: self.origin + self.yaw @ (sign * 0.165, -0.245, self.table + 0.042)
            for side, sign in SIDES
        }
        self.gestures = {}
        self.scene = scene
        self.supports = None
        self.moving_surfaces = []
        self.pads = {}
        self.hand_faces = {}
        self.forearms = {}
        self.forearm_faces = {}
        for side, _ in SIDES:
            bones = self.family[self.joints[f"{side}_hand"]]
            mask = np.isin(rig["joints"][:, 0], bones)
            triangles = rig["triangles"]
            subset = triangles[mask[triangles].any(axis=1)]
            used, indices = np.unique(subset, return_inverse=True)
            self.hand_faces[side] = indices.reshape(-1, 3)
            mask = used
            joints = rig["joints"][mask]
            forearm = self.family[self.joints[f"{side}_forearm"]]
            foremask = np.isin(rig["joints"][:, 0], np.setdiff1d(forearm, bones))
            subset = triangles[foremask[triangles].any(axis=1)]
            used, indices = np.unique(subset, return_inverse=True)
            self.forearm_faces[side] = indices.reshape(-1, 3)
            fj = rig["joints"][used]
            self.forearms[side] = (
                fj,
                rig["weights"][used],
                rig["vertices"][used, None, :] - self.bind[fj],
            )
            self.pads[side] = (
                joints,
                rig["weights"][mask],
                rig["vertices"][mask, None, :] - self.bind[joints],
            )
        self.ids = None
        # Keep the chair in the character's frame for rotated approach episodes.
        chair = SubElement(
            scene.world,
            "body",
            name=f"{self.prefix}_chair",
            pos=f"{x} {y} 0",
            quat=f"{np.cos(np.deg2rad(yaw) / 2)} 0 0 {np.sin(np.deg2rad(yaw) / 2)}",
        )
        seat = self.table - 0.225
        scene.box(chair, (0, 0.025, seat), (0.40, 0.34, 0.045), "#586a63")
        scene.box(chair, (0, 0.168, seat + 0.195), (0.39, 0.034, 0.31), "#66796e")
        for leg_x in (-0.16, 0.16):
            for leg_y in (-0.105, 0.155):
                scene.rod(chair, (leg_x, leg_y, 0.012), (leg_x, leg_y, seat), 0.012, "#444a48")

        filename = f"{self.prefix}.skn"
        scene.files[filename] = _skin(self.prefix)
        if "avatar.png" not in scene.files:
            scene.files["avatar.png"] = image
            SubElement(scene.asset, "texture", name="avatar_albedo", type="2d", file="avatar.png")
            SubElement(
                scene.asset,
                "material",
                name="avatar_material",
                texture="avatar_albedo",
                specular=".04",
                shininess=".12",
            )
        deform = scene.root.find("deformable")
        if deform is None:
            deform = SubElement(scene.root, "deformable")
        SubElement(deform, "skin", name=self.prefix, file=filename, material="avatar_material")
        for i in range(len(self.bind)):
            SubElement(scene.world, "body", name=f"{self.prefix}_joint_{i}", mocap="true")

    def _turn(self, key, delta):
        i = self.joints.get(key)
        if i is None:
            return
        group = self.family[i]
        pivot = self.pos[i].copy()
        self.pos[group] = (self.pos[group] - pivot) @ delta.T + pivot
        self.rot[group] = delta @ self.rot[group]

    def _point(self, key, child, direction):
        i, j = self.joints[key], self.joints[child]
        self._turn(key, _align(self.pos[j] - self.pos[i], direction))

    def _arm(self, side, sign, target, grip, recruitment):
        arm, fore, hand = [f"{side}_{name}" for name in ("upper_arm", "forearm", "hand")]
        i, j, k = [self.joints[name] for name in (arm, fore, hand)]
        # Sweep the collarbone toward the working hand before extending the elbow.
        self._turn(f"{side}_clavicle", _rotation((0, 0, 1), -sign * (0.09 + 0.20 * recruitment)))
        shoulder = self.pos[i].copy()
        fwd = _unit(
            np.array(
                (
                    np.clip((target[0] - shoulder[0]) * 0.85, -0.35, 0.35),
                    -1.0,
                    -0.16 - (0.65 * grip if self.moving_surfaces else 0.0),
                )
            )
        )
        across = _unit(np.cross((0, 0, 1), fwd)) * -sign
        gesture = self.gestures.get(side)
        if gesture == "stop":
            fwd = _unit(np.array((sign * 0.06, -0.14, 1.0)))
        elif gesture == "point":
            fwd = _unit(np.array((target[0] - shoulder[0], target[1] - shoulder[1], -0.16)))
            across = _unit(np.cross((0, 0, 1), fwd)) * -sign
        mid = self.joints.get(f"{side}_middle_1")
        index = self.joints.get(f"{side}_index_1")
        pinky = self.joints.get(f"{side}_pinky_1")
        if mid is not None and index is not None and pinky is not None:
            palm_basis = _frame(self.bind[mid] - self.bind[k], self.bind[index] - self.bind[pinky])
            palm_rot = _frame(fwd, across) @ palm_basis.T
            palm_offset = 0.90 * (self.bind[mid] - self.bind[k])
        else:
            palm_offset = np.array((sign * 0.071, 0.0, 0.0))
            palm_rot = _align(palm_offset, fwd)
        wrist = target - palm_rot @ palm_offset + np.array((0.0, 0.0, 0.009))
        self._reach(arm, fore, hand, wrist, shoulder, sign, palm_rot)
        curl_axis = _unit(np.cross(fwd, (0, 0, -1)))
        for n, digit in enumerate(DIGITS):
            for level in (1, 2, 3):
                key = f"{side}_{digit}_{level}"
                angle = 0.095 + 0.024 * min(n, 3) + grip * (0.65 if level == 1 else 0.80)
                if gesture == "point":
                    angle = 0.0 if digit == "index" else (0.57 if digit == "thumb" else 0.84)
                elif gesture == "stop":
                    angle = 0.0
                axis = (
                    curl_axis if digit != "thumb" else _unit(0.55 * curl_axis + sign * 0.83 * fwd)
                )
                self._turn(key, _rotation(axis, angle * (0.55 if digit == "thumb" else 1.0)))

        # Straighten the point/stop fingers against the original rig's relaxed
        # bind curl. A curled index would otherwise indicate a different place.
        for digit in ("index",) if gesture == "point" else DIGITS if gesture == "stop" else ():
            if digit == "thumb":
                continue
            spread = 0.09 * (DIGITS.index(digit) - 1.5) if gesture == "stop" else 0.0
            direction = _unit(fwd - across * spread)
            for level in (1, 2):
                self._point(f"{side}_{digit}_{level}", f"{side}_{digit}_{level + 1}", direction)
        # Fit the actual blended finger pads against the bench when the target is
        # close to its surface. A low wrist control alone can push curled fingers
        # below the top of a thin mat.
        if target[2] < self.table + 0.21:
            joints, weights, rel = self.pads[side]
            vertices = self.pos[joints] + np.einsum("nkij,nkj->nki", self.rot[joints], rel)
            skin = np.einsum("nk,nki->ni", weights, vertices) @ self.yaw.T + self.origin
            lift = 0.0
            triangles = skin[self.hand_faces[side]]
            for center, half, top in self.supports_this_frame:
                lift = max(lift, _surface_lift(triangles, center, half, top + 0.0008))
            if lift > 0:
                wrist[2] += lift
                self._reach(arm, fore, hand, wrist, shoulder, sign, palm_rot)

        # Move the elbow around the shoulder-to-wrist axis while keeping the
        # fingertips fixed. Raised shelves can lie between wrist and elbow even
        # when both the grasp and its fingertip approach remain clear.
        joints, weights, rel = self.forearms[side]

        def forearm_deficit():
            vertices = self.pos[joints] + np.einsum("nkij,nkj->nki", self.rot[joints], rel)
            skin = np.einsum("nk,nki->ni", weights, vertices) @ self.yaw.T + self.origin
            needed = 0.0
            for center, half, top in self.supports:
                # A beveled approach margin avoids changing the elbow abruptly
                # when a vertex just crosses the edge of a shelf in projection.
                outside = np.maximum(np.abs(skin[:, :2] - center) - half, 0.0).max(axis=1)
                required = top + 0.006 - 2.0 * outside - skin[:, 2]
                needed = max(needed, float(required.max()))
            return needed

        if forearm_deficit() > 0:
            low, high = 0.0, 1.65
            self._reach(arm, fore, hand, wrist, shoulder, sign, palm_rot, high)
            residual = forearm_deficit()
            if residual > 0:
                wrist[2] += residual * 1.6
                self._reach(arm, fore, hand, wrist, shoulder, sign, palm_rot, high)
            else:
                for _ in range(6):
                    mid = (low + high) / 2
                    self._reach(arm, fore, hand, wrist, shoulder, sign, palm_rot, mid)
                    if forearm_deficit() > 0:
                        low = mid
                    else:
                        high = mid
                self._reach(arm, fore, hand, wrist, shoulder, sign, palm_rot, high)
        else:
            high = 0.0

        # Blended wrist triangles change shape when the forearm swivels; the
        # triangle envelope is re-evaluated after both IK constraints have run.
        for _ in range(3):
            correction = 0.0
            for group, faces, supports in (
                (self.forearms[side], self.forearm_faces[side], self.supports),
                (self.pads[side], self.hand_faces[side], self.supports_this_frame),
            ):
                joints, weights, rel = group
                vertices = self.pos[joints] + np.einsum("nkij,nkj->nki", self.rot[joints], rel)
                skin = np.einsum("nk,nki->ni", weights, vertices) @ self.yaw.T + self.origin
                triangles = skin[faces]
                for center, half, top in supports:
                    correction = max(
                        correction, _surface_lift(triangles, center, half, top + 0.0004)
                    )
            if correction < 0.00005:
                break
            wrist[2] += correction * 1.5
            self._reach(arm, fore, hand, wrist, shoulder, sign, palm_rot, high)

    def _reach(self, arm, fore, hand, wrist, shoulder, sign, palm_rot, elbow_lift=0.0):
        i, j, k = [self.joints[name] for name in (arm, fore, hand)]
        delta = wrist - shoulder
        axis = _unit(delta)
        upper = np.linalg.norm(self.bind[j] - self.bind[i])
        lower = np.linalg.norm(self.bind[k] - self.bind[j])
        dist = np.clip(np.linalg.norm(delta), abs(upper - lower) + 0.0005, upper + lower - 0.0005)
        along = (dist * dist + upper * upper - lower * lower) / (2 * dist)
        pole = np.array((sign * 0.85, 0.42, -0.83 + elbow_lift))
        perp = _unit(pole - axis * (pole @ axis))
        elbow = shoulder + along * axis + np.sqrt(max(upper * upper - along * along, 0)) * perp
        self._point(arm, fore, elbow - shoulder)
        self._point(fore, hand, shoulder + dist * axis - elbow)
        self._turn(hand, palm_rot @ self.rot[k].T)

    def pose(self, model, data, time, targets, grips):
        """Solve both arms in the seated character's frame, then apply scene yaw."""
        if self.supports is None:
            self.supports = []
            for geom in self.scene.world.findall("geom[@type='box']"):
                center = np.fromstring(geom.get("pos", "0 0 0"), sep=" ")
                half = np.fromstring(geom.get("size"), sep=" ")
                top = center[2] + half[2]
                if (
                    self.table - 0.001 <= top <= self.table + 0.18
                    and half[2] <= 0.026
                    and min(half[:2]) >= 0.05
                ):
                    self.supports.append((center[:2], half[:2], top))
            # Wide flat movable props can be gripped along their surface. Use
            # their current mocap position so curled fingers also clear the mat
            # while it is being transported.
            for name, body in self.scene.props.items():
                base = body.find("geom")
                if base is None or base.get("type") != "box":
                    continue
                half = np.fromstring(base.get("size"), sep=" ")
                if half[2] <= 0.006 and min(half[:2]) >= 0.045:
                    offset = np.fromstring(base.get("pos", "0 0 0"), sep=" ")
                    self.moving_surfaces.append((model.body(name).mocapid[0], offset, half))
        self.supports_this_frame = list(self.supports)
        for mocap_id, offset, half in self.moving_surfaces:
            pos = data.mocap_pos[mocap_id] + offset
            self.supports_this_frame.append((pos[:2], half[:2], pos[2] + half[2]))
        if self.ids is None:
            self.ids = np.array(
                [model.body(f"{self.prefix}_joint_{i}").mocapid[0] for i in range(len(self.bind))]
            )
        local = {
            side: self.yaw.T @ (np.asarray(targets.get(side, self.rest[side])) - self.origin)
            for side, _ in SIDES
        }
        excursions = {
            side: np.linalg.norm(targets.get(side, self.rest[side]) - self.rest[side])
            for side, _ in SIDES
        }
        weights = np.array([excursions[side] for side, _ in SIDES])
        gaze = (local["left"] * (0.08 + weights[0]) + local["right"] * (0.08 + weights[1])) / (
            0.16 + weights.sum()
        )
        reach_depth = max(-target[1] for target in local.values())
        activity = np.clip((reach_depth - 0.32) / 0.30, 0, 1)
        breath = np.sin(time * 1.45)
        sway = np.sin(time * 0.74)
        left = self.joints["left_upper_arm"]
        right = self.joints["right_upper_arm"]
        shoulder_mid = (self.bind[left] + self.bind[right]) / 2
        self.pos = self.bind - np.array(
            (shoulder_mid[0], shoulder_mid[1], shoulder_mid[2] - self.table - 0.40)
        )
        self.pos += np.array(
            (0.003 * sway + 0.14 * gaze[0] * activity, 0.055 - 0.010 * activity, 0.0025 * breath)
        )
        self.rot = np.repeat(np.eye(3)[None], len(self.bind), axis=0)
        for side, sign in SIDES:
            self._turn(f"{side}_thigh", _rotation((1, 0, 0), -1.34))
            self._turn(f"{side}_calf", _rotation((1, 0, 0), 1.46))
            self._turn(f"{side}_foot", _rotation((1, 0, 0), -0.12))
        self._turn("spine", _rotation((1, 0, 0), 0.10 + 0.34 * activity + 0.006 * breath))
        self._turn("chest", _rotation((0, 0, 1), np.clip(gaze[0], -0.3, 0.3) * 0.42))
        self._turn("neck", _rotation((1, 0, 0), 0.21 + 0.10 * activity))
        self._turn("head", _rotation((0, 0, 1), 0.52 * np.arctan2(gaze[0], max(0.1, -gaze[1]))))
        for side, sign in SIDES:
            self._arm(side, sign, local[side], grips.get(side, 0.0), min(1.0, excursions[side] * 4))
        data.mocap_pos[self.ids] = self.pos @ self.yaw.T + self.origin
        matrices = self.yaw @ self.rot
        quat = np.empty(4)
        for idx, matrix in zip(self.ids, matrices):
            mujoco.mju_mat2Quat(quat, matrix.ravel())
            data.mocap_quat[idx] = quat
