"""Account for paired choices and missing runs in a prespecified experiment manifest."""

from collections import defaultdict
from hashlib import sha256
from pathlib import Path

from .evidence import fingerprint
from .study import new_directory, read_json, write_json


def summarize(manifest, output):
    """Manifest is a list of {id, family, bundle, evaluation, conditions} relative to the file."""
    manifest = Path(manifest)
    planned = read_json(manifest)
    ids = [run["id"] for run in planned]
    if len(set(ids)) != len(ids) or not ids:
        raise ValueError("Specify unique planned run IDs.")
    evaluations = [(manifest.parent / run["evaluation"]).resolve() for run in planned]
    if len(set(evaluations)) != len(evaluations):
        raise ValueError("Independent planned runs must use distinct evaluation paths")
    rows, pairs = (
        [],
        defaultdict(
            lambda: {"both_correct": 0, "both_wrong": 0, "gain": 0, "loss": 0, "missing": 0}
        ),
    )
    for run in planned:
        bundle = manifest.parent / run["bundle"]
        result = manifest.parent / run["evaluation"] / "results.json"
        config_path = bundle / "examiner/run.json"
        config = read_json(config_path) if config_path.exists() else None
        if config and config["family"] != run["family"]:
            raise ValueError(f"Wrong family in bundle for {run['id']}")
        conditions = run["conditions"]
        if "cold" not in conditions or len(conditions) != len(set(conditions)):
            raise ValueError("Each planned comparison needs a cold arm and unique conditions.")
        measured = {}
        failure = result.parent / "failure.json"
        status = "failed" if failure.is_file() else "missing"
        if result.is_file():
            if config is None:
                raise ValueError(f"Missing scorer key for {run['id']}")
            response = read_json(result)
            identity, config, _ = fingerprint(bundle)
            if response.get("bundle") != identity:
                raise ValueError(f"Evaluation bundle identity mismatch for {run['id']}")
            status = response["status"]
            for row in response["decisions"]:
                key = (row["phase"], row["condition"])
                if (
                    key in measured
                    or row["choice"] not in config["phases"][row["phase"]]["choices"]
                ):
                    raise ValueError(f"Invalid decision in {run['id']}: {key}")
                measured[key] = row["choice"] == config["phases"][row["phase"]]["answer"]
        for phase in ("transfer", "exception"):
            for condition in conditions:
                value = measured.get((phase, condition))
                rows.append(
                    {
                        "id": run["id"],
                        "family": run["family"],
                        "phase": phase,
                        "arm": condition,
                        "evaluation_status": status,
                        "rendered": config is not None,
                        "scored": value is not None,
                        "correct": value,
                    }
                )
                if condition != "cold":
                    cold = measured.get((phase, "cold"))
                    label = (
                        "missing"
                        if None in (cold, value)
                        else {
                            (False, True): "gain",
                            (True, False): "loss",
                            (True, True): "both_correct",
                            (False, False): "both_wrong",
                        }[(cold, value)]
                    )
                    pairs[(run["family"], phase, condition)][label] += 1
    with new_directory(output) as dest:
        write_json(
            dest / "summary.json",
            {
                "manifest_sha256": sha256(manifest.read_bytes()).hexdigest(),
                "rows": rows,
                "paired": [
                    {"family": k[0], "phase": k[1], "arm": k[2], **v} for k, v in pairs.items()
                ],
            },
        )
