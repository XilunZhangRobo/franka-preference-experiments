"""Load the exact prompt strings and source-file digest for an opt-in note policy."""

import hashlib
import json
from pathlib import Path


def load_note_policy(path):
    if path is None:
        return None
    raw = Path(path).read_bytes()
    data = json.loads(raw)
    keys = ("audit", "refine", "selective", "decide", "answer")
    if not isinstance(data, dict) or any(
        not isinstance(data.get(key), str) or not data[key].strip() for key in keys
    ):
        raise ValueError(
            "Note policy requires nonempty audit, refine, selective, decide and answer strings"
        )
    return {"sha256": hashlib.sha256(raw).hexdigest(), "prompts": {key: data[key] for key in keys}}
