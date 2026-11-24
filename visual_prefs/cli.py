"""Command-line entry points for acquisition, rendering, model calls and review."""

import argparse
import os
from pathlib import Path


def main():
    # Enable headless rendering on Linux when the caller has no display.
    if not os.getenv("DISPLAY") and os.name == "posix":
        os.environ.setdefault("MUJOCO_GL", "egl")
    from .study import BUILDERS, execute, record

    parser = argparse.ArgumentParser(prog="franka-prefs")
    subs = parser.add_subparsers(dest="command", required=True)
    subs.add_parser("assets")
    subs.add_parser("list")
    rec = subs.add_parser("record", help="Render a teaching interaction and two fresh probe scenes")
    rec.add_argument("family", choices=sorted(BUILDERS))
    rec.add_argument("--out", required=True, type=Path)
    rec.add_argument("--seed", type=int, default=0)
    rec.add_argument(
        "--transfer-seed",
        type=int,
        help="Independently cross held-out layout with teaching history",
    )
    rec.add_argument("--order-seed", type=int, help="Independently counterbalance option letters")
    rec.add_argument("--profile", choices=["standard", "reverse"], default="standard")
    rec.add_argument(
        "--feedback",
        choices=["silent", "retry", "other", "retry-only", "other-only", "incidental", "none"],
        default="silent",
    )
    rec.add_argument(
        "--accepted",
        action="store_true",
        help="Play the accepted teaching action without a correction",
    )
    rec.add_argument("--camera", choices=["agent", "wide"], default="agent")
    rec.add_argument("--calibration", type=Path)
    rec.add_argument("--size", nargs=2, type=int, default=(960, 720), metavar=("WIDTH", "HEIGHT"))
    rec.add_argument("--fps", type=int, default=12)
    ev = subs.add_parser(
        "evaluate", help="Detect, audit, write a text memory, and measure two fresh choices"
    )
    ev.add_argument("bundle", type=Path)
    ev.add_argument(
        "--adapter",
        required=True,
        help="Trusted stateless command that consumes JSON with inline images",
    )
    ev.add_argument("--out", type=Path, required=True)
    ev.add_argument(
        "--prior", type=Path, help="A previously learned note for this simulated person"
    )
    ev.add_argument(
        "--shuffled", type=Path, help="A note actually learned from a different interaction"
    )
    ev.add_argument("--answer", help="Answer used only if the auditor asks a clarification")
    act = subs.add_parser("execute", help="Replay a selected probe action and measure its endpoint")
    act.add_argument("bundle", type=Path)
    act.add_argument("phase", choices=["transfer", "exception"])
    act.add_argument("letter", choices=["A", "B"])
    act.add_argument("--out", type=Path, required=True)
    qa = subs.add_parser("audit", help="Run kinematic playback and paused-work physics checks")
    qa.add_argument("--seeds", type=int, nargs="+", default=[0, 1])
    qa.add_argument("--family", choices=sorted(BUILDERS), action="append")
    qa.add_argument("--out", type=Path, required=True)
    summary = subs.add_parser(
        "summarize", help="Report paired gains, losses and missing planned runs"
    )
    summary.add_argument("manifest", type=Path)
    summary.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "assets":
        from .assets import fetch

        print(fetch())
    elif args.command == "list":
        print("\n".join(BUILDERS))
    elif args.command == "record":
        record(
            args.family,
            args.out,
            seed=args.seed,
            profile=args.profile,
            feedback=args.feedback,
            fps=args.fps,
            size=tuple(args.size),
            camera=args.camera,
            calibration=args.calibration,
            accepted=args.accepted,
            transfer_seed=args.transfer_seed,
            order_seed=args.order_seed,
        )
    elif args.command == "evaluate":
        from .protocol import evaluate

        evaluate(
            args.bundle,
            args.out,
            args.adapter,
            prior=args.prior,
            shuffled=args.shuffled,
            answer=args.answer,
        )
    elif args.command == "execute":
        execute(args.bundle, args.phase, args.letter, args.out)
    elif args.command == "audit":
        from .quality import audit

        if not audit(args.out, args.seeds, args.family or list(BUILDERS)):
            raise SystemExit("Checks failed. See checks.json.")
    elif args.command == "summarize":
        from .analysis import summarize

        summarize(args.manifest, args.out)


if __name__ == "__main__":
    main()
