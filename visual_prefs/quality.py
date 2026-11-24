"""Exercise every primitive in both directions and publish failures alongside passes."""

import traceback

import numpy as np

from .contact import audit_contact, audit_robot_clearance
from .human_qa import audit_human
from .playback import Playback
from .study import PHASES, new_directory, scene_for, write_json
from .visibility import audit_visibility


def audit(out, seeds, families):
    rows, physical, visual, human = [], [], [], []
    with new_directory(out) as dest:
        for seed in seeds:
            for family in families:
                for phase in PHASES:
                    layout = seed + 103 * PHASES.index(phase)
                    scene, case = scene_for(family, phase, layout, "standard")
                    for choice in case.options:
                        row = {
                            "seed": seed,
                            "layout_seed": layout,
                            "family": family,
                            "phase": phase,
                            "action": choice,
                        }
                        try:
                            play = Playback(scene, fps=8)
                            # Avatar mocap and prop instances are model-local and indexes remain
                            # identical for this scene. A fresh MjData starts each alternative.
                            schedule = case.robot[choice] + (
                                case.human if phase == "teach" and choice != case.expected else []
                            )
                            endpoints = {}
                            for step in schedule:
                                if step.style in ("lift", "slide", "hold", "offer"):
                                    endpoints[step.item] = step.target
                            for sample in play.play(case, choice, correct=phase == "teach"):
                                pass
                            misses = [
                                float(np.linalg.norm(play.data.mocap_pos[play.ids[name]] - target))
                                for name, target in endpoints.items()
                            ]
                            max_error = max(misses, default=0.0)
                            row.update(
                                passed=bool(
                                    max_error < 0.001 and np.isfinite(play.data.qpos).all()
                                ),
                                max_endpoint_error_m=max_error,
                                max_robot_pinch_error_m=play.peak_error,
                                frames=sample.index + 1,
                            )
                        except Exception:
                            row.update(passed=False, error=traceback.format_exc())
                        rows.append(row)
                print(f"audited {family} seed {seed}", flush=True)
            if "paused-work" in families:
                physical.append(audit_contact(seed))
                physical.extend(audit_robot_clearance(seed, p) for p in ("teach", "transfer"))
                visual.append(audit_visibility(seed))
                human.append(audit_human(seed))
        passed = all(r["passed"] for r in rows + physical + visual + human)
        write_json(
            dest / "checks.json",
            {
                "seeds": seeds,
                "passed": passed,
                "playback": rows,
                "paused_work_physics": physical,
                "visibility": visual,
                "human": human,
            },
        )
    return passed
