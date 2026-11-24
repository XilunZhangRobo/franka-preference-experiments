"""Identify the private scoring key and the exact public sensor bundle."""

import json
from hashlib import sha256


def fingerprint(bundle):
    examiner = bundle / "examiner"
    key = (examiner / "run.json").read_bytes()
    manifest = (examiner / "sensor-sha256.json").read_bytes()
    sensor = bundle / "sensor"
    recorded = json.loads(manifest)
    actual = {
        p.relative_to(sensor).as_posix(): sha256(p.read_bytes()).hexdigest()
        for p in sensor.rglob("*")
        if p.is_file()
    }
    if actual != recorded:
        raise ValueError("Sensor bytes differ from the examiner manifest")
    identity = {
        "run_sha256": sha256(key).hexdigest(),
        "sensor_manifest_sha256": sha256(manifest).hexdigest(),
    }
    return identity, json.loads(key), recorded
