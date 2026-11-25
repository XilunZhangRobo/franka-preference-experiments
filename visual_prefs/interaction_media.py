"""Render an immutable experimental observation in a separate Blender process."""

import argparse
import fcntl
import os
from pathlib import Path

from .interaction_sim import prepare
from .study import new_directory, write_json


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("out", type=Path)
    parser.add_argument("family")
    parser.add_argument("phase")
    parser.add_argument("seed", type=int)
    parser.add_argument("choice")
    parser.add_argument("response")
    parser.add_argument("width", type=int)
    parser.add_argument("height", type=int)
    parser.add_argument("fps", type=int)
    parser.add_argument("samples", type=int)
    args = parser.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("MUJOCO_GL", "egl")
    with args.out.with_suffix(".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if args.out.exists():
            return
        trial = prepare(args.family, args.phase, args.seed)
        config = dict(
            size=(args.width, args.height),
            fps=args.fps,
            samples=args.samples,
            renderer="blender-cycles",
            device="CPU",
            camera="agent",
        )
        with new_directory(args.out) as stage:
            if args.choice == "initial":
                packet, measured = trial.initial(stage / "view", **config)
            else:
                packet, measured = trial.execute(
                    stage / "view",
                    args.choice,
                    None if args.response == "none" else args.response,
                    **config,
                )
            packet["options"] = trial.options
            write_json(stage / "view" / "packet.json", packet)
            write_json(stage / "measurement.json", measured)
            write_json(
                stage / "render.json",
                dict(
                    family=args.family,
                    phase=args.phase,
                    seed=args.seed,
                    choice=args.choice,
                    response=args.response,
                    **config,
                ),
            )


if __name__ == "__main__":
    main()
