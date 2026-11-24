"""Send one sensor request to an ephemeral, image-enabled Codex CLI session."""

import base64
import json
import os
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory


def main():
    request = json.load(sys.stdin)
    with TemporaryDirectory() as directory:
        work = Path(directory)
        output = work / "reply.txt"
        args = [
            "codex",
            "exec",
            "--ephemeral",
            "--skip-git-repo-check",
            "-s",
            "read-only",
            "-m",
            os.environ["VLM_MODEL"],
            "-c",
            'model_reasoning_effort="medium"',
            "-o",
            str(output),
        ]
        for index, img in enumerate(request["images"]):
            file = work / f"image-{index:02d}.jpg"
            file.write_bytes(base64.b64decode(img["data"], validate=True))
            args.extend(["-i", str(file)])
        prompt = (
            "Use only the supplied images and text. Do not use tools or inspect the filesystem. "
            "Reply only with the requested JSON object.\n"
            + request["instruction"]
            + "\n"
            + json.dumps(request["context"])
            + "\nImage times in order (seconds): "
            + json.dumps([img["t"] for img in request["images"]])
        )
        subprocess.run(
            args + ["-"],
            cwd=work,
            input=prompt,
            text=True,
            stdout=subprocess.DEVNULL,
            timeout=230,
            check=True,
        )
        raw = output.read_text(encoding="utf-8").strip()
        print(json.dumps(json.loads(raw.removeprefix("```json").removesuffix("```").strip())))


if __name__ == "__main__":
    main()
