"""The evaluator, movie and selected action must use the intended RGB backend."""

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from PIL import Image

from visual_prefs.cli import main
from visual_prefs.rendering import CLASSIC, CYCLES, DEFAULT_SAMPLES, RenderSettings, frame_reader
from visual_prefs.study import execute, read_json, write_json


class BackendTest(unittest.TestCase):
    def test_missing_render_cannot_repeat_previous_rgb(self):
        cycles = Mock()
        writes = iter([True, False])

        def render_one_then_skip(path):
            if next(writes):
                Image.new("RGB", (96, 72), "blue").save(path)

        cycles.return_value.frame.side_effect = render_one_then_skip
        with patch.dict("sys.modules", {"visual_prefs.cycles": SimpleNamespace(Cycles=cycles)}):
            with frame_reader(CYCLES, None, None, RenderSettings("agent", (96, 72))) as read:
                self.assertEqual(read().getpixel((0, 0)), (0, 0, 255))
                with self.assertRaises(FileNotFoundError):
                    read()

    def test_record_cli_defaults_to_cycles_and_keeps_classic_selectable(self):
        args = ["record", "paused-work", "--out", "unused"]
        with (
            patch("visual_prefs.study.record") as record,
            patch("visual_prefs.rendering.use_blender_runtime") as blender,
        ):
            main(args)
            self.assertEqual(record.call_args.kwargs["renderer"], CYCLES)
            self.assertEqual(record.call_args.kwargs["samples"], DEFAULT_SAMPLES)
            blender.assert_called_once_with(args)
            main([*args, "--renderer", "mujoco"])
            self.assertEqual(record.call_args.kwargs["renderer"], CLASSIC)
            self.assertEqual(blender.call_count, 1)

    def test_execute_respects_both_archived_and_cycles_settings(self):
        def render(scene, case, folder, **kwargs):
            folder.mkdir()
            return {}, {}

        config = dict(
            family="paused-work",
            profile="standard",
            calibration=None,
            camera="agent",
            phases={"transfer": {"layout_seed": 103, "choices": {"A": "near"}, "answer": "A"}},
            size=[960, 720],
            fps=12,
        )
        with (
            tempfile.TemporaryDirectory() as tmp,
            patch("visual_prefs.study.scene_for", return_value=(None, None)),
            patch("visual_prefs.study.render", side_effect=render) as renderer,
            patch("visual_prefs.study.cycles_provenance", return_value={}),
        ):
            bundle = Path(tmp)
            (bundle / "examiner").mkdir()
            for source, backend, samples in (
                ({}, CLASSIC, DEFAULT_SAMPLES),
                (
                    {"renderer": CYCLES, "renderer_provenance": {"samples": 17, "device": "CPU"}},
                    CYCLES,
                    17,
                ),
            ):
                with self.subTest(backend=backend):
                    write_json(bundle / "examiner/run.json", config | source)
                    out = bundle / backend
                    execute(bundle, "transfer", "A", out)
                    self.assertEqual(renderer.call_args.kwargs["renderer"], backend)
                    self.assertEqual(renderer.call_args.kwargs["samples"], samples)
                    self.assertEqual(read_json(out / "measurement.json")["renderer"], backend)
