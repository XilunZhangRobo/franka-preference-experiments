"""Calibrate the rendered agent view to an externally measured, undistorted camera.

Profile JSON fields:
  image_size: [width,height] of the rectified image at calibration resolution.
  image_space: "undistorted".
  intrinsics: {fx, fy, cx, cy} in pixels, zero skew, pixel centers at integers.
  world_from_camera: 4x4 rigid transform (optical x-right/y-down/z-forward
    to scene world, translation in meters). Invert OpenCV's world-to-camera
    extrinsics before supplying them here.
  fit_image_ids: nonempty list of all image IDs used for intrinsic or pose fits.

Validation JSON fields:
  image_id: held-out rectified image at native calibration resolution.
  corners: [{label, world_m: [x,y,z], pixel: [u,v]}, ...]. Supply at least
    four distinct board corners with measured scene coordinates and manually
    or independently detected pixel locations. Use the same world registration.
The caller supplies genuine measurements and acquisition IDs. Disjoint IDs
are checked; the tool cannot establish capture provenance from coordinates.

Run python -m visual_prefs.calibration profile.json measured_points.json.
Reference: https://docs.opencv.org/4.x/d9/d0c/group__calib3d.html
"""

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image


def _array(values, shape, description):
    result = np.asarray(values, dtype=float)
    if result.shape != shape or not np.isfinite(result).all():
        raise ValueError(f"Expected finite {description} with shape {shape}")
    return result


class CalibratedCamera:
    @classmethod
    def from_file(cls, path):
        return cls(json.loads(Path(path).read_text()))

    def __init__(self, profile):
        if profile["image_space"] != "undistorted":
            raise ValueError("Use rectified images with undistorted pinhole intrinsics")
        self.width, self.height = profile["image_size"]
        if any(type(n) is not int or n <= 0 for n in (self.width, self.height)):
            raise ValueError("Image size requires positive integer dimensions")
        k = profile["intrinsics"]
        self.fx, self.fy, self.cx, self.cy = _array(
            [k[key] for key in ("fx", "fy", "cx", "cy")], (4,), "intrinsics"
        )
        if min(self.fx, self.fy) <= 0:
            raise ValueError("Focal lengths must be positive")
        self.transform = _array(profile["world_from_camera"], (4, 4), "world_from_camera")
        rot = self.transform[:3, :3]
        if not (
            np.allclose(self.transform[3], [0, 0, 0, 1], atol=1e-8, rtol=0)
            and np.allclose(rot.T @ rot, np.eye(3), atol=1e-6, rtol=0)
            and np.isclose(np.linalg.det(rot), 1, atol=1e-6, rtol=0)
        ):
            raise ValueError("world_from_camera must be a proper rigid transform")
        ids = profile["fit_image_ids"]
        if (
            not isinstance(ids, list)
            or not ids
            or not all(isinstance(s, str) and s.strip() for s in ids)
        ):
            raise ValueError("List the images used to estimate intrinsics and extrinsics")
        self.fit_image_ids = set(ids)
        self.render_size = None

    def project(self, world_m):
        """Return native-resolution pixel-center coordinates for an N by 3 array."""
        xyz = np.asarray(world_m, dtype=float)
        if xyz.ndim != 2 or xyz.shape[1] != 3 or not np.isfinite(xyz).all():
            raise ValueError("Expected finite world points in meters")
        optical = (xyz - self.transform[:3, 3]) @ self.transform[:3, :3]
        if np.any(optical[:, 2] <= 0):
            raise ValueError("Board corner is on or behind the optical plane")
        return optical[:, :2] / optical[:, 2:] * [self.fx, self.fy] + [self.cx, self.cy]

    def validate(self, measured):
        """Measure Euclidean reprojection errors without estimating any parameters."""
        image_id = measured["image_id"]
        if not isinstance(image_id, str) or not image_id.strip() or image_id in self.fit_image_ids:
            raise ValueError("Use an independently held-out image ID")
        corners = measured["corners"]
        if len(corners) < 4:
            raise ValueError("At least four labeled corners required")
        labels = [c["label"] for c in corners]
        if not all(isinstance(s, str) and s.strip() for s in labels) or len(set(labels)) != len(
            labels
        ):
            raise ValueError("Corner labels must be unique nonempty strings")
        xyz = _array([c["world_m"] for c in corners], (len(labels), 3), "board corners")
        uv = _array([c["pixel"] for c in corners], (len(labels), 2), "measured pixels")
        if np.any(uv < -0.5) or np.any(uv >= np.array([self.width, self.height]) - 0.5):
            raise ValueError("Measured corners fall outside the calibration image")
        for points in (xyz, uv):
            if (
                len(np.unique(points, axis=0)) != len(labels)
                or np.linalg.matrix_rank(points - points[0]) < 2
            ):
                raise ValueError("Board corners must be distinct and span an area")
        errors = np.linalg.norm(self.project(xyz) - uv, axis=1)
        return {
            "image_id": image_id,
            "corners": len(labels),
            "rms_px": float(np.sqrt(np.mean(errors**2))),
            "max_px": float(errors.max()),
            "errors_px": dict(zip(labels, errors.tolist())),
        }

    def configure(self, scene, width, height):
        """Set agent-camera MJCF before compilation. Same-aspect resizes are allowed."""
        if (
            any(type(n) is not int or n <= 0 for n in (width, height))
            or width * self.height != height * self.width
        ):
            raise ValueError("Use positive dimensions with the calibrated aspect ratio")
        scale = width / self.width
        fx, fy = self.fx * scale, self.fy * scale
        # Pillow affine coordinates use pixel edge origin, unlike calibration labels.
        cx, cy = (self.cx + 0.5) * scale, (self.cy + 0.5) * scale
        # Enclose every required output ray in the symmetric source frustum.
        f = min(width / 2 * fx / max(cx, width - cx), height / 2 * fy / max(cy, height - cy))
        camera = scene.world.find("camera[@name='agent']")
        if camera is None:
            raise ValueError("Scene requires an agent camera")
        rotation = self.transform[:3, :3]
        axes = np.r_[rotation[:, 0], -rotation[:, 1]]
        camera.set("pos", " ".join(map(str, self.transform[:3, 3])))
        camera.set("xyaxes", " ".join(map(str, axes)))
        camera.set("fovy", str(np.rad2deg(2 * np.arctan(height / (2 * f)))))
        self.render_size = (width, height)
        self.affine = (f / fx, 0, width / 2 - cx * f / fx, 0, f / fy, height / 2 - cy * f / fy)

    def warp(self, image):
        """Sample a centered MuJoCo render into the measured pinhole view."""
        if image.size != self.render_size:
            raise ValueError("Configure the camera with the rendered image dimensions first")
        return image.transform(
            image.size, Image.Transform.AFFINE, self.affine, resample=Image.Resampling.BILINEAR
        )


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate independent board-corner reprojection error."
    )
    parser.add_argument("profile")
    parser.add_argument("measured_points")
    args = parser.parse_args()
    try:
        camera = CalibratedCamera.from_file(args.profile)
        print(
            json.dumps(
                camera.validate(json.loads(Path(args.measured_points).read_text())), indent=2
            )
        )
    except (OSError, TypeError, KeyError, ValueError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
