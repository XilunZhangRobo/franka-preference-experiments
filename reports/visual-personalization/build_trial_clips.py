"""Build standalone interaction clips from archived camera recordings with the experiment venv."""
import json
import subprocess
from functools import cache
from pathlib import Path
from tempfile import TemporaryDirectory

import imageio_ffmpeg

ROOT = Path(__file__).resolve().parent
ARCHIVE = ROOT / "visual-interaction-study-v1"
OUT = ROOT / "trial-clips"
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()


def ffmpeg(*args):
    return subprocess.check_output([FFMPEG, "-v", "error", "-nostdin", "-xerror", *args])


@cache
def timeline(source):
    folder = source.parents[1]
    fps = json.loads((folder / "render.json").read_text())["fps"]
    events = json.loads((folder / "measurement.json").read_text())["events"]
    return fps, events


@cache
def validate_clock(path, fps, count):
    # Decode every frame and check the clock, frame count, and continuity.
    data = ffmpeg("-i", path, "-map", "0:v:0", "-fps_mode", "passthrough", "-f", "framemd5", "-").decode()
    assert f"#tb 0: 1/{fps}\n" in data, path
    rows = [line.split(",") for line in data.splitlines() if not line.startswith("#")]
    assert len(rows) == count and all(int(r[2]) == i and int(r[3]) == 1 for i, r in enumerate(rows)), path
    return [row[-1].strip() for row in rows]


def feedback_start(source, action):
    _, events = timeline(source)
    _, before = timeline(action)
    # The action-only recording ends with a settling hold. Its preceding events
    # include any human setup (such as writing before a completion update).
    onset = max(i for i, e in enumerate(before) if e["actor"] != "idle") + 1
    assert events[:onset] == before[:onset] and events[onset]["actor"].startswith("human"), source
    if any(e["actor"] == "robot" for e in events[onset:]):
        return 0  # Keep the full joint approach/handoff that prompted the reaction.
    return onset - 1  # One pre-response frame gives the starting arrangement.


@cache
def make_clip(source, start):
    fps, events = timeline(source)
    end = len(events)
    assert all(e["index"] == i and abs(e["time"] - i / fps) < 1e-6 for i, e in enumerate(events))
    source_hashes = validate_clock(source, fps, end)
    stem = "-".join(source.relative_to(ARCHIVE).parts[1:4])
    if start:
        stem += "-feedback"
    output = OUT / f"{stem}.webm"
    fallback = OUT / f"{stem}.mp4" if start else source
    poster = source.parent / f"frame-{start:05d}.jpg"
    with TemporaryDirectory(dir=OUT) as tmp:
        movie = Path(tmp) / "clip.webm"
        trim = f"trim=start_frame={start},setpts=PTS-STARTPTS"
        if not output.exists() or validate_clock(output, fps, end - start) != source_hashes[start:]:
            ffmpeg("-i", source, "-vf", f"{trim},setsar=1", "-an", "-c:v", "libvpx-vp9",
                   "-pix_fmt", "yuv420p", "-lossless", "1", "-row-mt", "1",
                   "-cpu-used", "6", "-threads", "4", movie)
            assert validate_clock(movie, fps, end - start) == source_hashes[start:], output
            movie.replace(output)
        if start:
            if not fallback.exists():
                temp_mp4 = Path(tmp) / "clip.mp4"
                ffmpeg("-i", source, "-vf", trim, "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                       "-crf", "15", "-movflags", "+faststart", temp_mp4)
                temp_mp4.replace(fallback)
            validate_clock(fallback, fps, end - start)
            stats = Path(tmp) / "psnr.txt"
            ffmpeg("-i", source, "-i", fallback, "-lavfi",
                   f"[0:v]{trim}[cut];[cut][1:v]psnr=stats_file={stats}", "-f", "null", "-")
            values = [float(row.split("psnr_avg:")[1].split()[0]) for row in stats.read_text().splitlines()]
            assert len(values) == end - start and min(values) > 40, fallback
        if not poster.is_file():
            poster = output.with_suffix(".jpg")
            ffmpeg("-y", "-i", output, "-frames:v", "1", "-q:v", "2", poster)
    assert poster.is_file()
    return dict(file=str(output.relative_to(ROOT)), mp4=str(fallback.relative_to(ROOT)), duration=(end-start)/fps,
                poster=str(poster.relative_to(ROOT)), source=str(source.relative_to(ROOT)),
                start=start/fps, end=end/fps, start_frame=start, end_frame_exclusive=end, fps=fps)


def main():
    OUT.mkdir(exist_ok=True)
    manifest = {}
    for trial in json.loads((ARCHIVE / "report_manifest.json").read_text())["episodes"]:
        turns = [t for t in trial["turns"] if "clip" in t]
        assert [t["channel"] for t in turns] == [
            "visual evidence to person", "visual feedback to robot", "executed probe action", "executed probe action"]
        action, feedback, transfer, control = [ARCHIVE / t["clip"] for t in turns]
        assert transfer.parts[-4].startswith("transfer-") and control.parts[-4].startswith("exception-")
        manifest[f"{trial['mode']}/{trial['scenario']}"] = {
            "action": make_clip(action, 0), "feedback": make_clip(feedback, feedback_start(feedback, action)),
            "transfer": make_clip(transfer, 0), "control": make_clip(control, 0)}
    assert len(manifest) == 24
    with TemporaryDirectory(dir=OUT) as tmp:
        path = Path(tmp) / "manifest.json"
        path.write_text(json.dumps(manifest, indent=2) + "\n")
        path.replace(OUT / "manifest.json")


if __name__ == "__main__":
    main()
