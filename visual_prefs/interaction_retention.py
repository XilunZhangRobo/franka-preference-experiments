"""Evaluate retrieval from a frozen note library on paired, held-out scenes."""

import fcntl
import hashlib
import html
import json
import os
import re
import shutil
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import quote

from .interaction_astra import AstraSession

SELECT = ('Select zero to three notes relevant to this task and observation. '
          'Return {"ids":["note ID", ...]}.')
DECIDE = ('Choose exactly one of the offered actions for the task and the observed scene. '
          'Return {"choice":"option letter"}.')
PHASES = ("transfer", "exception")


def save(path, data):
    pending = path.with_suffix(".tmp")
    pending.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    pending.replace(path)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def library(root):
    notes = {}
    for path in sorted((root / "library").glob("*.md")):
        if path.name not in {f"{i:02}.md" for i in range(1, 11)}:
            raise ValueError(f"Unexpected note slot {path.name}")
        content = path.read_bytes()
        lines = content.decode("utf-8").splitlines()
        if not lines or not lines[0].startswith("# "):
            raise ValueError(f"Missing note title in {path.name}")
        identity = "N-" + digest(path.name.encode())[:10]
        notes[identity] = {"title": lines[0][2:].strip(), "text": content.decode("utf-8"),
                           "file": str(path.relative_to(root)), "sha256": digest(content)}
    if len(notes) > 10:
        raise ValueError(f"Expected at most ten final notes, found {len(notes)}")
    return notes


def ask(stage, instruction, context, frame):
    # Keep completed arm replies when a later stage or another scene fails.
    checkpoint = stage / "receipt.json"
    if checkpoint.is_file():
        return json.loads(checkpoint.read_text())
    session = AstraSession(stage, persistent=False)
    reply = session.ask(instruction, context, [frame])
    save(checkpoint, reply)
    return reply


def choice(reply, options, expected):
    value = reply.get("choice")
    valid = isinstance(value, str) and value in options
    return {"choice": value, "correct": value == expected if valid else None,
            "status": "scored" if valid else "invalid choice"}


def probe(directory, family, phase, trial, frame, notes):
    directory.mkdir(parents=True, exist_ok=True)
    expected = trial.expected("standard")
    visible = {"task": trial.case.command, "options": trial.options}
    identity = {"family": family, "phase": phase, "visible": visible, "expected": expected,
                "image_sha256": digest(frame.read_bytes()),
                "notes": {key: n["sha256"] for key, n in notes.items()},
                "selection_instruction": SELECT, "decision_instruction": DECIDE}
    with (directory / ".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        identity_path = directory / "identity.json"
        if identity_path.exists() and json.loads(identity_path.read_text()) != identity:
            raise ValueError(f"Inputs changed for a checkpoint in {directory}")
        save(identity_path, identity)
        first = directory / "first.jpg"
        if not first.exists():
            shutil.copyfile(frame, first)
        if digest(first.read_bytes()) != identity["image_sha256"]:
            raise ValueError(f"Archived observation changed in {directory}")
        result_path = directory / "result.json"
        if result_path.exists():
            return json.loads(result_path.read_text())
        row = {"family": family, "phase": phase, "task": trial.case.command, "expected": expected,
               "folder": directory.name, "options": trial.options, "selected": []}
        cold = ask(directory / "cold", DECIDE, {**visible, "notes": []}, first)
        row["cold"] = choice(cold, trial.options, expected)
        catalog = [{"id": key, "title": note["title"]} for key, note in notes.items()]
        selected = ask(directory / "retrieve", SELECT, {**visible, "catalog": catalog}, first)
        ids = selected.get("ids")
        if (isinstance(ids, list) and len(ids) <= 3
                and all(isinstance(key, str) and key in notes for key in ids)
                and len(ids) == len(set(ids))):
            row["selected"] = ids
            texts = [notes[key]["text"] for key in ids]
            with_notes = ask(directory / "decision", DECIDE, {**visible, "notes": texts}, first)
            row["library"] = choice(with_notes, trial.options, expected)
        else:
            row["library"] = {"choice": None, "correct": None, "status": "invalid retrieval"}
        save(result_path, row)
        return row


def summary(rows):
    out = {}
    for phase in PHASES:
        group = [r for r in rows if r["phase"] == phase]
        pairs = [(r["cold"]["correct"], r["library"]["correct"]) for r in group]
        paired = [(a, b) for a, b in pairs if a is not None and b is not None]
        out[phase] = {"planned": len(group), "paired_scored": len(paired),
                      "cold_scored": sum(a is not None for a, _ in pairs),
                      "cold_correct": sum(a is True for a, _ in pairs),
                      "library_scored": sum(b is not None for _, b in pairs),
                      "library_correct": sum(b is True for _, b in pairs),
                      "gains": sum(not a and b for a, b in paired),
                      "losses": sum(a and not b for a, b in paired)}
    return out


def anchor(directory, target, label):
    href = quote(os.path.relpath(target, directory), safe="/")
    return f'<a href="{href}">{html.escape(str(label))}</a>'


def score(arm):
    result = arm["correct"]
    if result is None:
        return html.escape(arm["status"])
    return f'{html.escape(arm["choice"])} ({"correct" if result else "incorrect"})'


def report(directory, rows, notes, totals, slots):
    root = directory.parent
    chunks = ['<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" '
              'content="width=device-width, initial-scale=1"><title>Final-library retention</title>'
              '<style>body{max-width:75rem;margin:2rem auto;padding:0 1rem;font:16px/1.5 system-ui}'
              'td,th{padding:.4rem;text-align:left;vertical-align:top;border-bottom:1px solid #ccc}'
              'a{color:#075968}</style><main><h1>Final-library retention</h1>'
              '<p>Each pair uses the same held-out initial image, task and choices. A fresh reader '
              f'selects up to three of {len(notes)} available note titles. A separate decision receives the selected '
              'full notes. A fresh cold decision receives an empty note list.</p>',
              anchor(directory, directory / "results.json", "Results JSON"),
              '<h2>Paired outcomes</h2><table><tr><th>Probe</th><th>Planned</th><th>Cold '
              'correct/scored</th><th>Library correct/scored</th><th>Paired scored</th>'
              '<th>Gains</th><th>Losses</th></tr>']
    for phase, t in totals.items():
        chunks.append(f'<tr><th>{phase}</th><td>{t["planned"]}</td>'
                      f'<td>{t["cold_correct"]}/{t["cold_scored"]}</td>'
                      f'<td>{t["library_correct"]}/{t["library_scored"]}</td>'
                      f'<td>{t["paired_scored"]}</td><td>{t["gains"]}</td><td>{t["losses"]}</td></tr>')
    chunks.append('</table><h2>Final library</h2>'
                  f'<p>{len(notes)} files present across ten planned teaching episodes.</p><ol>')
    for slot in slots:
        name = html.escape(slot['family'] or slot['filename'])
        note = notes.get(slot['note_id'])
        saved = anchor(directory, root / note['file'], note['title']) if note else 'Missing file'
        chunks.append(f'<li>{name} · {saved}</li>')
    chunks.append('</ol><h2>Scenes</h2><table><tr><th>Scene</th><th>Reference</th>'
                  '<th>Cold</th><th>Library</th><th>Selected notes</th><th>Evidence</th></tr>')
    for r in rows:
        scene = directory / r["folder"]
        selected = [anchor(directory, root / notes[key]["file"], notes[key]["title"])
                    for key in r["selected"]]
        evidence = [anchor(directory, scene / "first.jpg", "Observation"),
                    anchor(directory, scene / "identity.json", "Scorer")]
        for stage in ("cold", "retrieve", "decision"):
            for req in sorted((scene / stage).glob("*/request.json")):
                evidence.append(anchor(directory, req, stage + " request"))
                for reply in sorted(req.parent.glob("attempt-*/events.jsonl")):
                    evidence.append(anchor(directory, reply, stage + " events"))
        chunks.append(f'<tr><th>{html.escape(r["family"])} · {r["phase"]}</th>'
                      f'<td>{html.escape(r["expected"])}</td><td>{score(r["cold"])}</td>'
                      f'<td>{score(r["library"])}</td><td>{"<br>".join(selected) or "—"}</td>'
                      f'<td>{" · ".join(evidence)}</td></tr>')
    chunks.append("</table></main></html>")
    pending = directory / "index.tmp"
    pending.write_text("\n".join(chunks), encoding="utf-8")
    pending.replace(directory / "index.html")


def run_retention(root, families, render_initial, readers=3):
    """Return HTML and JSON paths relative to root. Caller reserves held-out seeds."""
    root = Path(root).resolve()
    directory = root / "retention"
    directory.mkdir(exist_ok=True)
    notes = library(root)
    families = list(families)
    if len(set(families)) != len(families) or not families:
        raise ValueError("Provide distinct family names.")
    if any(not re.fullmatch(r"[a-zA-Z0-9_-]+", family) for family in families):
        raise ValueError("Family names must be safe identifiers.")
    # Render on the caller's thread. Only audited model reads run in worker threads.
    futures = []
    with ThreadPoolExecutor(max_workers=readers) as pool:
        for family in families:
            for phase in PHASES:
                trial, frame = render_initial(family, phase)
                futures.append(pool.submit(probe, directory / f"{family}-{phase}",
                                           family, phase, trial, Path(frame), notes))
        rows = [future.result() for future in futures]
    totals = summary(rows)
    public_notes = {k: {field: n[field] for field in ("title", "file", "sha256")}
                    for k, n in notes.items()}
    by_filename = {Path(note["file"]).name: key for key, note in notes.items()}
    slots = []
    for i in range(10):
        filename = f"{i + 1:02}.md"
        key = by_filename.get(filename)
        slots.append({"family": families[i] if i < len(families) else None,
                      "filename": filename, "note_id": key, "status": "present" if key else "missing"})
    save(directory / "results.json", {"library": public_notes, "planned_notes": 10,
         "available_notes": len(notes), "library_slots": slots, "summary": totals, "scenes": rows})
    report(directory, rows, notes, totals, slots)
    return Path("retention/index.html"), Path("retention/results.json")
