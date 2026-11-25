"""Command-line entry points for acquisition, rendering, model calls and review."""

import argparse
import os
import sys
from pathlib import Path


def main(argv=None):
    # Enable headless rendering on Linux when the caller has no display.
    if not os.getenv("DISPLAY") and os.name == "posix":
        os.environ.setdefault("MUJOCO_GL", "egl")
    from .rendering import CLASSIC, CYCLES, DEFAULT_SAMPLES, DEVICES, use_blender_runtime
    from .study import BUILDERS, execute, read_json, record

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
    rec.add_argument(
        "--renderer",
        choices=("cycles", "mujoco"),
        default="cycles",
        help="RGB renderer for every video frame and learner image (default: cycles)",
    )
    rec.add_argument(
        "--samples", type=int, help=f"Cycles samples per pixel (default: {DEFAULT_SAMPLES})"
    )
    rec.add_argument("--device", choices=DEVICES, help="Cycles device (default: CPU)")
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
    ev.add_argument(
        "--note-policy", type=Path, help="JSON file with opt-in note and decision prompts"
    )
    ev.add_argument("--answer", help="Answer used only if the auditor asks a clarification")
    act = subs.add_parser("execute", help="Replay a selected probe action and measure its endpoint")
    act.add_argument("bundle", type=Path)
    act.add_argument("phase", choices=["transfer", "exception"])
    act.add_argument("letter", choices=["A", "B"])
    act.add_argument("--out", type=Path, required=True)
    act.add_argument(
        "--device", choices=DEVICES, help="Override the recorded Cycles device for this replay"
    )
    qa = subs.add_parser("audit", help="Run kinematic playback and paused-work physics checks")
    qa.add_argument("--seeds", type=int, nargs="+", default=[0, 1])
    qa.add_argument("--family", choices=sorted(BUILDERS), action="append")
    qa.add_argument("--out", type=Path, required=True)
    summary = subs.add_parser(
        "summarize", help="Report paired gains, losses and missing planned runs"
    )
    summary.add_argument("manifest", type=Path)
    summary.add_argument("--out", type=Path, required=True)
    arguments = sys.argv[1:] if argv is None else argv
    args = parser.parse_args(arguments)
    if args.command == "assets":
        from .assets import fetch

        print(fetch())
    elif args.command == "list":
        print("\n".join(BUILDERS))
    elif args.command == "record":
        if args.samples is not None and args.samples < 1:
            parser.error("--samples must be positive")
        if args.renderer == "cycles":
            use_blender_runtime(arguments)
        elif args.samples is not None or args.device is not None:
            parser.error("--samples and --device apply to Cycles recordings")
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
            renderer=CYCLES if args.renderer == "cycles" else CLASSIC,
            samples=args.samples or DEFAULT_SAMPLES,
            device=args.device or "CPU",
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
            note_policy=args.note_policy,
        )
    elif args.command == "execute":
        config = read_json(args.bundle / "examiner/run.json")
        if config.get("renderer", CLASSIC) == CYCLES:
            use_blender_runtime(arguments)
        elif args.device:
            parser.error("--device applies to Cycles recordings")
        execute(args.bundle, args.phase, args.letter, args.out, device=args.device)
    elif args.command == "audit":
        from .quality import audit

        if not audit(args.out, args.seeds, args.family or list(BUILDERS)):
            raise SystemExit("Checks failed. See checks.json.")
    elif args.command == "summarize":
        from .analysis import summarize

        summarize(args.manifest, args.out)


if __name__ == "__main__":
    main()
