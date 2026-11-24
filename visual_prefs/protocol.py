"""Stateless multimodal calls. Only rendered observations and user text cross this boundary."""

import base64
import json
import os
import shlex
import subprocess
import tempfile
from hashlib import sha256
from pathlib import Path

import numpy as np

from .evidence import fingerprint
from .study import PHASES, new_directory, write_json

DETECT = (
    "These are time-ordered samples from a robot's camera during one task. Locate a person's "
    "intervention or feedback if one is visible. Ordinary nearby activity may be incidental. "
    "Return JSON with window, either [start_seconds,end_seconds] or null."
)
AUDIT = (
    "Review this interaction. What happened? Why might the person have acted that way? "
    "What could you use next time? Separate observations from hypotheses. Record a short "
    "reusable preference only to the degree the evidence warrants. A rejected action can "
    "be recorded even if its cause remains unknown. Return JSON with observation, "
    "interpretation, note and question as strings. Use an empty note for no preference "
    "evidence. Ask a focused question only if the uncertainty matters."
)
DECIDE = (
    "Choose an available action for this command using the current image and any user memory. "
    "Return JSON with choice (one supplied letter) and reason. Commit to one choice."
)


def samples(frames, limit):
    indices = np.linspace(0, len(frames) - 1, min(limit, len(frames))).round().astype(int)
    return [frames[i] for i in indices]


class Calls:
    def __init__(self, adapter, folder, manifest):
        self.manifest = manifest
        self.command = shlex.split(adapter)
        self.folder = folder
        self.count = 0

    def __call__(self, prompt, context, source, frames):
        self.count += 1
        images, refs = [], []
        for frame in frames:
            name = frame["file"]
            if not isinstance(name, str) or Path(name).name != name or not name.endswith(".jpg"):
                raise ValueError("Expected a local sensor JPEG filename")
            content = (source / name).read_bytes()
            digest = sha256(content).hexdigest()
            if digest != self.manifest.get(f"{source.name}/{name}"):
                raise ValueError("Delivered frame differs from sensor manifest")
            images.append(
                {"t": frame["t"], "mime": "image/jpeg", "data": base64.b64encode(content).decode()}
            )
            refs.append({"t": frame["t"], "sha256": digest, "file": frame["file"]})
        visible = {"instruction": prompt, "context": context}
        request = visible | {"images": images}
        log = self.folder / f"call-{self.count:02d}.json"
        provenance = {"request": visible | {"images": refs}}
        write_json(log, provenance)
        with tempfile.TemporaryDirectory() as cwd:
            run = subprocess.run(
                self.command,
                input=json.dumps(request),
                capture_output=True,
                text=True,
                cwd=cwd,
                timeout=300,
            )
        write_json(log, provenance | {"raw_reply": run.stdout, "exit_code": run.returncode})
        if run.returncode:
            raise RuntimeError(f"Adapter call {self.count} exited {run.returncode}")
        response = json.loads(run.stdout)
        if not isinstance(response, dict):
            raise ValueError("Adapter must emit a single JSON object.")
        return response


def audited_note(call, sensor, packet, prior="", answer=None):
    frames = packet["frames"]
    context = {"task": packet["command"], "speech": packet["speech_transcript"]}
    result = call(DETECT, context, sensor, samples(frames, 30))
    window = result["window"]
    if window is None and not any(e["speaker"] == "person" for e in context["speech"]):
        return prior, None
    if window is None:
        selected = samples(frames, 24)
    else:
        if not (
            isinstance(window, list)
            and len(window) == 2
            and all(isinstance(v, (int, float)) and np.isfinite(v) for v in window)
            and 0 <= window[0] <= window[1] <= frames[-1]["t"] + 0.25
        ):
            raise ValueError(f"Invalid visual interval {window!r}")
        before = [f for f in frames if f["t"] < window[0]]
        within = [f for f in frames if window[0] <= f["t"] <= window[1]]
        after = [f for f in frames if f["t"] > window[1]]
        selected = samples(before, 7) + samples(within, 18) + after[:1]
    reply = call(AUDIT, context | {"existing_note": prior}, sensor, selected)
    for key in ("observation", "interpretation", "note", "question"):
        if not isinstance(reply.get(key), str):
            raise ValueError(f"Missing audit text field {key}")
    if answer and reply["question"].strip():
        reply = call(
            AUDIT,
            context | {"existing_note": prior, "review": reply, "person_answer": answer},
            sensor,
            selected,
        )
        if not isinstance(reply.get("note"), str):
            raise ValueError("Expected revised note text.")
    return reply["note"].strip() or prior, reply


def evaluate(bundle, out, adapter, *, prior=None, shuffled=None, answer=None):
    root = Path(bundle)
    initial = Path(prior).read_text().strip() if prior else ""
    with new_directory(out, preserve_failures=True) as dest:
        identity, config, manifest = fingerprint(root)
        call = Calls(adapter, dest, manifest)
        decisions = []
        audit = None

        def checkpoint(status):
            write_json(
                dest / "results.json",
                {
                    "adapter": adapter,
                    "model": os.getenv("VLM_MODEL"),
                    "bundle": identity,
                    "status": status,
                    "audit": audit,
                    "decisions": decisions,
                },
            )

        def packet_for(source):
            data = (source / "packet.json").read_bytes()
            if sha256(data).hexdigest() != manifest.get(f"{source.name}/packet.json"):
                raise ValueError("Delivered packet differs from sensor manifest")
            return json.loads(data)

        try:
            teacher = root / "sensor/teach"
            note, audit = audited_note(call, teacher, packet_for(teacher), initial, answer)
            (dest / "memory.md").write_text(note + ("\n" if note else ""))
            conditions = {"cold": "", "matched": note}
            if shuffled:
                conditions["mismatched"] = Path(shuffled).read_text().strip()
            # Each decision starts a fresh adapter process with only the public inputs.
            for phase in PHASES[1:]:
                source = root / "sensor" / phase
                packet = packet_for(source)
                for condition, memory in conditions.items():
                    reply = call(
                        DECIDE,
                        {"task": packet["command"], "options": packet["options"], "memory": memory},
                        source,
                        packet["frames"],
                    )
                    if reply.get("choice") not in packet["options"]:
                        raise ValueError("Decision must name an available option.")
                    choice = reply["choice"]
                    decisions.append(
                        {
                            "phase": phase,
                            "condition": condition,
                            "choice": choice,
                            "matched_answer": choice == config["phases"][phase]["answer"],
                        }
                    )
                    checkpoint("partial")
        except Exception:
            checkpoint("failed")
            raise
        checkpoint("complete")
