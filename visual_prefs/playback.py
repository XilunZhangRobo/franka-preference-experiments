"""Deterministic kinematic playback, sampled on a common clock for camera and speech."""

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from math import ceil

import mujoco
import numpy as np

from .episode import carry_clearance


def ease(t):
    """Minimum-jerk interpolation with zero endpoint velocity and acceleration."""
    return t * t * t * (10 + t * (-15 + 6 * t))


@dataclass
class Sample:
    index: int
    time: float
    actor: str
    action: str
    utterance: str = ""


class Playback:
    def __init__(self, scene, fps=12):
        self.scene = scene
        self.fps = fps
        self.model = mujoco.MjModel.from_xml_string(
            ET.tostring(scene.root, encoding="unicode"), scene.files
        )
        self.data = mujoco.MjData(self.model)
        self.site = self.model.site("pinch").id
        self.ids = {key: self.model.body(key).mocapid[0] for key in scene.props}
        self.q = [self.model.joint(f"joint{i}").qposadr[0] for i in range(1, 8)]
        self.dofs = [self.model.joint(f"joint{i}").dofadr[0] for i in range(1, 8)]
        self.limits = np.array([self.model.joint(f"joint{i}").range for i in range(1, 8)])
        self.index = 0
        self.peak_error = 0.0
        self.targets = dict(scene.avatar.rest)
        self.grips = {"right": 0.0, "left": 0.0}
        self.data.qpos[self.q] = [0.80, 0.16, 0, -1.95, 0, 2.11, 0.65]
        self.data.qpos[7:9] = 0.038
        mujoco.mj_forward(self.model, self.data)
        self.park = self.data.site_xpos[self.site].copy()
        self.robot_target = self.park.copy()
        self.robot_grip = 0.0
        self.holders = {}
        self.gestures = {}
        self._joint_target = None
        self._update()

    def _ik(self, target):
        # The 7th degree of freedom is free; keep the fingers facing the bench.
        if self._joint_target is not None and np.array_equal(target, self._joint_target):
            return
        m, d = self.model, self.data
        jp = np.zeros((3, m.nv))
        jr = np.zeros_like(jp)
        for _ in range(55):
            mujoco.mj_kinematics(m, d)
            mujoco.mj_comPos(m, d)
            error = target - d.site_xpos[self.site]
            axis = d.site_xmat[self.site].reshape(3, 3)[:, 2]
            tilt = np.cross(axis, (0.0, 0.0, -1.0))
            if np.linalg.norm(error) < 0.001 and np.linalg.norm(tilt) < 0.018:
                break
            mujoco.mj_jacSite(m, d, jp, jr, self.site)
            # Constrain tilt, leave yaw free about the gripper axis.
            angular = (np.eye(3) - np.outer(axis, axis)) @ jr[:, self.dofs]
            jac = np.vstack((jp[:, self.dofs], 0.16 * angular))
            delta = jac.T @ np.linalg.solve(
                jac @ jac.T + 0.00015 * np.eye(6), np.r_[error, 0.16 * tilt]
            )
            d.qpos[self.q] = np.clip(
                d.qpos[self.q] + np.clip(delta, -0.16, 0.16), self.limits[:, 0], self.limits[:, 1]
            )
        self._joint_target = target.copy()

    def _update(self):
        self.scene.avatar.pose(
            self.model, self.data, self.index / self.fps, self.targets, self.grips
        )
        for idx, guest in enumerate(self.scene.guests):
            guest.pose(self.model, self.data, self.index / self.fps + 0.79 * (idx + 1), {}, {})
        self._ik(self.robot_target)
        self.data.qpos[7:9] = 0.038 - 0.027 * self.robot_grip
        self.data.time = self.index / self.fps
        mujoco.mj_forward(self.model, self.data)
        error = np.linalg.norm(self.robot_target - self.data.site_xpos[self.site])
        self.peak_error = max(self.peak_error, float(error))
        if error > 0.02:
            raise ValueError(
                f"Unreachable gripper waypoint {self.robot_target.round(3)} (error {error:.3f} m)"
            )

    def _frame(self, actor, action, utterance=""):
        self._update()
        sample = Sample(self.index, self.index / self.fps, actor, action, utterance)
        self.index += 1
        return sample

    def pause(self, seconds, utterance=""):
        for i in range(max(1, round(seconds * self.fps))):
            yield self._frame("idle", "rest", utterance if i == 0 else "")

    def _stroke(self, actor, end, grip, action, duration, attached=None, arc=0.0):
        robot = actor == "robot"
        side = "left" if actor == "human-left" else "right"
        start = (self.robot_target if robot else self.targets[side]).copy()
        g0 = self.robot_grip if robot else self.grips[side]
        end = np.asarray(end)
        count = max(2, ceil(duration * self.fps))
        if attached:
            origin = self.data.mocap_pos[self.ids[attached]].copy()
        for i in range(1, count + 1):
            t = ease(i / count)
            delta = (end - start) * t
            delta[2] += arc * 4 * t * (1 - t)
            if robot:
                self.robot_target = start + delta
                self.robot_grip = g0 + t * (grip - g0)
            else:
                self.targets[side] = start + delta
                self.grips[side] = g0 + t * (grip - g0)
            if attached:
                self.data.mocap_pos[self.ids[attached]] = origin + delta
            yield self._frame(actor, action)

    def move(self, motion):
        actor, item = motion.actor, motion.item
        start = self.data.mocap_pos[self.ids[item]].copy()
        target = np.asarray(motion.target)
        offset = self.scene.grasps.get(item)
        if actor != "robot" and item in self.scene.human_grasps:
            offset = np.asarray(self.scene.human_grasps[item])
        if offset is None:
            # Use object geometry for a reasonable grip height on unfamiliar props.
            geom = self.scene.props[item].find("geom")
            height = float(geom.get("pos", "0 0 .012").split()[2]) if geom is not None else 0.012
            offset = np.array((0.0, 0.0, max(0.006, height)))
        source = start + offset
        goal = target + offset
        side = "left" if actor == "human-left" else "right"
        rest = self.park if actor == "robot" else self.scene.avatar.rest[side]
        length = np.linalg.norm(source - rest)
        if motion.style == "say":
            yield self._frame(actor, "say", self.scene.sounds[item])
            return
        if motion.style in ("stop", "point"):
            self.scene.avatar.gestures = {side: motion.style}
            yield from self._stroke(actor, target, 0.0, motion.style, 0.63, arc=0.018)
            for _ in range(max(1, round(0.32 * self.fps))):
                yield self._frame(actor, motion.style)
            yield from self._stroke(actor, rest, 0.0, "withdraw", 0.59)
            self.scene.avatar.gestures = {}
            return
        previous = self.holders.get(item)
        # At a handover the two effectors contact opposite sides of the item.
        if actor != "robot" and previous and previous != actor:
            offset = offset + np.array((0.018 if side == "left" else -0.018, 0.012, 0.002))
            source, goal = start + offset, target + offset
        if previous != actor:
            yield from self._stroke(actor, source, 0.0, "reach", 0.35 + 1.35 * length, arc=0.048)
        spoken = ""
        if motion.style == "touch":
            if item in self.scene.switches:
                light = self.model.light(self.scene.switches[item]).id
                self.model.light_active[light] = not self.model.light_active[light]
            spoken = self.scene.sounds.get(item, "")
            yield self._frame(actor, "touch", spoken)
        else:
            if previous != actor:
                yield from self._stroke(actor, source, 1.0, "grasp", 0.20)
                if previous:
                    giver_side = "left" if previous == "human-left" else "right"
                    giver_rest = (
                        self.park if previous == "robot" else self.scene.avatar.rest[giver_side]
                    )
                    giver_pos = (
                        self.robot_target if previous == "robot" else self.targets[giver_side]
                    )
                    yield from self._stroke(previous, giver_pos, 0.0, "release", 0.16)
                    yield from self._stroke(previous, giver_rest, 0.0, "withdraw", 0.45, arc=0.03)
            arc = 0.0 if motion.style == "slide" else carry_clearance(item, goal - source)
            duration = 0.42 + 1.7 * np.linalg.norm(goal - source)
            yield from self._stroke(actor, goal, 1.0, "transport", duration, item, arc)
            if motion.style in ("offer", "hold"):
                self.holders[item] = actor
                return
            self.holders.pop(item, None)
            yield from self._stroke(actor, goal, 0.0, "release", 0.18)
        yield from self._stroke(actor, rest, 0.0, "withdraw", 0.40 + 1.2 * length, arc=0.050)

    def play(self, case, choice, *, correct=False, utterance="", visible=True):
        yield from self.pause(0.5)
        for motion in case.robot[choice]:
            yield from self.move(motion)
        if correct and choice != case.expected:
            if visible:
                for motion in case.human:
                    yield from self.move(motion)
            if utterance:
                yield from self.pause(0.35, utterance)
        yield from self.pause(0.5)
