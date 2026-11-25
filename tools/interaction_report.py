"""Render a relocatable HTML and MP4 evidence report from report_manifest.json."""

import argparse
import hashlib
import html
import json
import math
import os
import struct
import subprocess
import tempfile
from fractions import Fraction
from pathlib import Path
from urllib.parse import quote

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont

SIZE = (768, 512)
FPS = 12
VERSION = "2"


def source(root, value):
    path = (root / value).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise ValueError(f"Missing or out-of-bundle artifact {value!r}")
    return path


def url(root, path):
    return quote(path.relative_to(root).as_posix(), safe="/")


def esc(value):
    return html.escape(str(value), quote=True)


def link(root, label, value):
    return f'<a href="{url(root, source(root, value))}">{esc(label)}</a>'


def links(root, mapping):
    return " · ".join(link(root, label, path) for label, path in mapping.items())


def font(size):
    try:
        return ImageFont.truetype("DejaVuSans.ttf", size)
    except OSError:
        return ImageFont.load_default(size=size)


def wrap_line(text, face, width):
    # Measure glyphs, including unbroken identifiers from raw model responses.
    lines = []
    while face.getlength(text) > width:
        low, high = 1, len(text)
        while low < high:
            mid = (low + high + 1) // 2
            if face.getlength(text[:mid]) <= width:
                low = mid
            else:
                high = mid - 1
        split = text.rfind(" ", 0, low + 1)
        cut = split + 1 if split > 0 else low
        lines.append(text[:cut])
        text = text[cut:]
    return [*lines, text]


def turn_label(turn):
    return " · ".join(
        str(turn[key])
        for key in ("time", "role", "channel")
        if key in turn and turn[key] is not None
    )


def cards(turn):
    face = font(24)
    lines = [
        part
        for line in str(turn.get("text", "")).split("\n")
        for part in wrap_line(line, face, SIZE[0] - 64)
    ]
    for start in range(0, len(lines), 11):
        img = Image.new("RGB", SIZE, "#142532")
        draw = ImageDraw.Draw(img)
        draw.text((32, 30), turn_label(turn), font=font(21), fill="#8ae4ca")
        chunk = lines[start : start + 11]
        for i, line in enumerate(chunk):
            draw.text((32, 91 + i * 33), line, font=face, fill="#ffffff")
        yield img, min(8, max(2, math.ceil(len(" ".join(chunk).split()) / 3.4)))


def media(turn):
    for key in ("image", "images", "clip"):
        value = turn.get(key)
        if value:
            for path in value if isinstance(value, list) else [value]:
                yield key, path


def encode(args):
    subprocess.run(
        [
            imageio_ffmpeg.get_ffmpeg_exe(),
            "-nostdin",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            *map(str, args),
        ],
        check=True,
    )


def segment(work, cache, src, duration):
    key = src, duration
    if key not in cache:
        out = work / f"s{len(cache)}.mp4"
        inputs = ["-loop", "1", "-framerate", FPS] if duration else []
        timing = ["-t", duration] if duration else []
        filt = (
            f"fps={FPS},scale={SIZE[0]}:{SIZE[1]}:force_original_aspect_ratio=decrease,"
            f"pad={SIZE[0]}:{SIZE[1]}:(ow-iw)/2:(oh-ih)/2,setsar=1"
        )
        encode(
            [
                *inputs,
                "-i",
                src,
                *timing,
                "-vf",
                filt,
                "-an",
                "-c:v",
                "libx264",
                "-threads",
                2,
                "-preset",
                "veryfast",
                "-crf",
                19,
                "-pix_fmt",
                "yuv420p",
                out,
            ]
        )
        cache[key] = out
    return cache[key]


def movie(root, ep, outdir, work, cache, index):
    turns = ep["turns"]
    digest = hashlib.sha256((VERSION + json.dumps(turns, sort_keys=True)).encode())
    for turn in turns:
        for _, raw in media(turn):
            path = source(root, raw)
            with path.open("rb") as stream:
                digest.update(hashlib.file_digest(stream, "sha256").digest())
    out = outdir / f"episode-{index}-{digest.hexdigest()[:16]}.mp4"
    if out.exists():
        return out
    parts = []
    for turn in turns:
        for img, seconds in cards(turn):
            card = work / (hashlib.sha256(img.tobytes()).hexdigest() + ".png")
            if not card.exists():
                img.save(card)
            parts.append(segment(work, cache, card, seconds))
        for kind, raw in media(turn):
            parts.append(segment(work, cache, source(root, raw), None if kind == "clip" else 2))
    if not parts:
        return None
    listing = work / "sequence.txt"
    listing.write_text("".join(f"file '{p.name}'\n" for p in parts))
    pending = work / "episode.mp4"
    encode(
        [
            "-f",
            "concat",
            "-safe",
            1,
            "-i",
            listing,
            "-c",
            "copy",
            "-movflags",
            "+faststart",
            pending,
        ]
    )
    os.replace(pending, out)
    return out


def movie_duration(path):
    """Read the exact MP4 container duration from the movie header without decoding."""
    with path.open("rb") as stream:
        limit = path.stat().st_size
        while stream.tell() + 8 <= limit:
            start = stream.tell()
            size, kind = struct.unpack(">I4s", stream.read(8))
            if size == 1:
                (size,) = struct.unpack(">Q", stream.read(8))
            end = start + size if size else limit
            if end <= start or end > limit:
                break
            if kind == b"moov":
                limit = end
                continue
            if kind == b"mvhd":
                version = stream.read(4)[0]
                if version not in (0, 1):
                    break
                stream.seek(16 if version else 8, os.SEEK_CUR)
                (scale,) = struct.unpack(">I", stream.read(4))
                (duration,) = struct.unpack(
                    ">Q" if version else ">I", stream.read(8 if version else 4)
                )
                return Fraction(duration, scale)
            stream.seek(end)
    raise ValueError(f"Missing MP4 movie header in {path}")


def continuous_movie(root, episodes, work, cache, outdir):
    parts, chapters = [], []
    elapsed = Fraction(0)
    metadata = [";FFMETADATA1"]
    for index, (ep, film) in enumerate(episodes):
        title = str(ep.get("title") or ep["scenario"])
        start = elapsed
        part = work / f"continuous-{index}.mp4"
        os.link(film, part)
        parts.append(part)
        elapsed += movie_duration(part)
        if ep.get("transcript"):
            after = source(root, ep["transcript"]).with_name("library-after.json")
            if after.exists():
                count = len(json.loads(after.read_text()))
                text = f"{count} written {'note' if count == 1 else 'notes'} after this episode."
                for img, seconds in cards(
                    {"role": "Continuous library", "channel": title, "text": text}
                ):
                    card = work / f"continuous-count-{index}.png"
                    img.save(card)
                    part = segment(work, cache, card, seconds)
                    parts.append(part)
                    elapsed += movie_duration(part)
        clean = "".join(("\\" + ch if ch in "\\;#=" else ch) for ch in " ".join(title.splitlines()))
        metadata.extend(
            [
                "[CHAPTER]",
                "TIMEBASE=1/1000",
                f"START={round(start * 1000)}",
                f"END={round(elapsed * 1000)}",
                "title=" + clean,
            ]
        )
        chapters.append((title, start))
    listing = work / "continuous.txt"
    listing.write_text("".join(f"file '{part.name}'\n" for part in parts))
    tags = work / "chapters.ffmeta"
    tags.write_text("\n".join(metadata) + "\n", encoding="utf-8")
    pending = work / "continuous-library.mp4"
    encode(
        [
            "-f",
            "concat",
            "-safe",
            1,
            "-i",
            listing,
            "-f",
            "ffmetadata",
            "-i",
            tags,
            "-map",
            "0:v:0",
            "-map_metadata",
            "1",
            "-map_chapters",
            "1",
            "-c:v",
            "copy",
            "-movflags",
            "+faststart",
            pending,
        ]
    )
    result = outdir / pending.name
    os.replace(pending, result)
    href = url(root, result)
    jumps = " · ".join(
        f'<a href="{href}#t={float(start):.3f}">{esc(title)}</a>' for title, start in chapters
    )
    return (
        f'<section id="continuous-film"><h2>One robot across {len(episodes)} episodes</h2>'
        f'<video controls preload="none" src="{href}"></video><p>'
        f'<a href="{href}">Open chaptered MP4</a></p><nav>{jumps}</nav></section>'
    )


def outcome(value):
    if isinstance(value, bool):
        return "Correct" if value else "Incorrect"
    return "Unscored" if value is None else esc(value)


def raw_calls(root, ep):
    index = next(
        (v for v in ep.get("artifacts", {}).values() if Path(v).name == "calls.json"), None
    )
    if not index:
        return ""
    items = []
    for key, receipt_file in json.loads(source(root, index).read_text()).items():
        receipt = json.loads(source(root, receipt_file).read_text())
        request = source(root, receipt["request"])
        files = [
            link(root, "Request JSON", receipt["request"]),
            link(root, "Reply receipt", receipt_file),
        ]
        prompt = request.with_name("prompt.txt")
        if prompt.exists():
            files.append(link(root, "Exact prompt", prompt.relative_to(root)))
        for attempt in sorted(request.parent.glob("attempt-*")):
            for name, label in (("reply.txt", "Raw reply"), ("events.jsonl", "Events")):
                artifact = attempt / name
                if artifact.exists():
                    files.append(link(root, label, artifact.relative_to(root)))
        images = json.loads(request.read_text()).get("images", [])
        frames = [
            link(root, str(i), (request.parent / entry["file"]).relative_to(root))
            for i, entry in enumerate(images, 1)
        ]
        gallery = " · Ordered images " + " ".join(frames) if frames else ""
        items.append(f"<li><b>{esc(key)}</b> · " + " · ".join(files) + gallery + "</li>")
    return (
        "<details><summary>Exact model inputs and replies</summary><ol>"
        + "".join(items)
        + "</ol></details>"
    )


def table_of_scores(episodes):
    columns = [("Teaching", "teaching_miss"), ("Transfer", "transfer"), ("Exception", "control")]
    html = [
        '<h2 id="scores">Episode scores</h2><p>Each probe cell lists cold / written note / '
        "learner, in that order. ✓ means the choice matched the person’s reference action. "
        "× means it missed. A dash means no score was recorded.</p><table><tr><th>Episode</th>"
    ]
    html.extend(f"<th>{label}</th>" for label, _ in columns)
    html.append("</tr>")
    for i, ep in enumerate(episodes, 1):
        scores = ep.get("scores", {})
        html.append(
            f'<tr><th><a href="#episode-{i}">{esc(ep["mode"])} · {esc(ep["scenario"])}</a></th>'
        )
        for _, key in columns:
            if key == "teaching_miss":
                value = scores.get(key)
                cell = "Miss" if value is True else "Matched" if value is False else "—"
            else:
                cell = " / ".join(
                    {True: "✓", False: "×"}.get(scores.get(key + "_" + arm), "—")
                    for arm in ("cold", "note", "learner")
                )
            html.append(f"<td>{cell}</td>")
        html.append("</tr>")
    return "".join(html) + "</table>"


def timeline(root, episodes):
    parts = ['<h2 id="library">Continuous library timeline</h2><ol>']
    for i, ep in enumerate(episodes, 1):
        if ep["mode"] != "continuous":
            continue
        parts.append(f'<li><a href="#episode-{i}">{esc(ep["scenario"])}</a>')
        if ep.get("transcript"):
            folder = source(root, ep["transcript"]).parent
            before = folder / "library-before.json"
            after = folder / "library-after.json"
            if before.exists() and after.exists():
                old = json.loads(before.read_text())
                new = json.loads(after.read_text())
                parts.append(f" · {len(old)} → {len(new)} files · ")
                parts.append(
                    link(root, "Before", before.relative_to(root))
                    + " · "
                    + link(root, "After", after.relative_to(root))
                )
                added = sorted(set(new) - {k if k.endswith(".md") else k + ".md" for k in old})
                if not added:
                    parts.append(" · No new library file")
                for filename in added:
                    path = source(root, Path("library") / filename)
                    parts.append(
                        " · "
                        + link(
                            root,
                            path.read_text().splitlines()[0].lstrip("# "),
                            path.relative_to(root),
                        )
                    )
        parts.append("</li>")
    return "".join(parts) + "</ol>"


def episode_html(root, ep, film, index):
    anchor = f"episode-{index}"
    title = esc(ep.get("title") or ep["scenario"])
    body = [f'<article id="{anchor}"><h3>{title}</h3>']
    if film:
        body.append(f'<video controls preload="none" src="{url(root, film)}"></video>')
    paths = dict(ep.get("artifacts", {}))
    if ep.get("transcript"):
        paths["Recorded transcript"] = ep["transcript"]
    body.append(f"<p>{links(root, paths)}</p>")
    body.append(raw_calls(root, ep))
    scores = ep.get("scores", {})
    if scores:
        body.append("<table><caption>Recorded outcomes</caption><tbody>")
        for label, value in scores.items():
            result = esc(value) if label == "teaching_miss" else outcome(value)
            body.append(f"<tr><th>{esc(label)}</th><td>{result}</td></tr>")
        body.append("</tbody></table>")
    body.append("<details><summary>Episode transcript and original observations</summary>")
    for n, turn in enumerate(ep["turns"], 1):
        tid = f"{anchor}-turn-{n}"
        files = " · ".join(
            link(root, f"{kind} {i}", raw) for i, (kind, raw) in enumerate(media(turn), 1)
        )
        body.append(
            f'<section id="{tid}"><h4><a href="#{tid}">Turn {n}</a> · '
            f"{esc(turn_label(turn))}</h4><pre>{esc(turn.get('text', ''))}</pre>"
            f"{files}</section>"
        )
    return "".join(body) + "</details></article>"


def render(directory):
    root = directory.resolve()
    data = json.loads((root / "report_manifest.json").read_text())
    episodes = data["episodes"]
    outdir = root / "report-media"
    outdir.mkdir(exist_ok=True)
    body = [
        '<!doctype html><html lang="en"><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        "<title>Interaction study</title><style>"
        "body{margin:2rem auto;padding:0 1rem;max-width:58rem;background:#f7f7f3;"
        "color:#142532;font:17px/1.5 system-ui}article{padding:1rem 0 2rem;"
        "border-top:1px solid #899}video{width:100%;max-width:768px;background:#142532}"
        "pre{white-space:pre-wrap;overflow-wrap:anywhere;font:inherit}a{color:#075968}"
        "td,th{padding:.3rem .8rem;text-align:left;border-bottom:1px solid #ddd}"
        "caption{text-align:left;font-weight:bold}summary{cursor:pointer;margin:1rem 0}"
        "</style><main><h1>Interaction study</h1>"
    ]
    body.append(
        f"<nav>{links(root, {'Run manifest': 'report_manifest.json', **data.get('artifacts', {})})}</nav>"
    )
    modes = ["isolated", "contrast", "continuous"]
    modes = [mode for mode in modes if any(ep["mode"] == mode for ep in episodes)]
    if any(ep["mode"] not in modes for ep in episodes):
        raise ValueError("Unknown episode mode")
    body.append(
        "<p>In an original isolated episode the robot meets one person with a specified "
        "preference. When its first action already matched that preference, a separate "
        "contrast episode tests a person whose profile disagrees with its first choice. "
        "The contrast cases are selected examples of correction.</p>"
        "<p>In the continuous series the same robot and person keep their conversations "
        "across all ten tasks. On each probe a fresh cold robot sees the task and image. "
        "A second fresh robot also gets the written note. The episode learner keeps its "
        "conversation and can ask a question before acting.</p>"
        '<nav><a href="#scores">Episode scores</a> · <a href="#library">Library timeline</a></nav>'
    )
    feature_position = len(body)
    for mode in modes:
        body.append(f'<h2><a href="#{mode}">{mode.title()}</a></h2><ul>')
        for i, ep in enumerate(episodes, 1):
            if ep["mode"] == mode:
                body.append(
                    f'<li><a href="#episode-{i}">{esc(ep.get("title") or ep["scenario"])}</a></li>'
                )
        body.append("</ul>")
    body.extend([table_of_scores(episodes), timeline(root, episodes)])
    if data.get("comparisons"):
        body.append(
            "<h2>Held-out comparisons</h2><table><tr><th>Scenario</th><th>Cold</th><th>Note</th></tr>"
        )
        for row in data["comparisons"]:
            body.append(
                f"<tr><td>{esc(row['scenario'])}</td><td>{outcome(row['cold'])}</td>"
                f"<td>{outcome(row['note'])}</td></tr>"
            )
        body.append("</table>")
    with tempfile.TemporaryDirectory(dir=outdir) as temp:
        work, cache = Path(temp), {}
        continuous = []
        for mode in modes:
            body.append(f'<h2 id="{mode}">{mode.title()} episodes</h2>')
            for i, ep in enumerate(episodes, 1):
                if ep["mode"] == mode:
                    film = movie(root, ep, outdir, work, cache, i)
                    body.append(episode_html(root, ep, film, i))
                    if mode == "continuous" and film:
                        continuous.append((ep, film))
        if continuous:
            body.insert(feature_position, continuous_movie(root, continuous, work, cache, outdir))
        body.append("</main></html>")
        pending = work / "index.html"
        pending.write_text("\n".join(body), encoding="utf-8")
        os.replace(pending, root / "index.html")
    return root / "index.html"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    print(render(parser.parse_args().directory))
