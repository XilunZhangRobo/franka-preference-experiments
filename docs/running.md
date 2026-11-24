# Running a visual preference experiment

Run these commands in the activated environment from the README. Each output path must be new so earlier evidence survives a rerun.

The CLI records in Cycles by default. For fast native runs, pass `--renderer mujoco`. Keep the renderer, resolution and sampling settings matched across experimental conditions. [Recording settings](cycles.md)

## Record matched stimuli

```bash
franka-prefs list
franka-prefs record paused-work --seed 0 --feedback retry --out runs/undo
franka-prefs record paused-work --seed 0 --feedback other --out runs/other
franka-prefs record paused-work --seed 0 --feedback retry-only --out runs/speech
franka-prefs record paused-work --seed 0 --feedback silent --out runs/silent
franka-prefs record paused-work --seed 0 --feedback none --out runs/no-feedback
franka-prefs record paused-work --seed 0 --feedback incidental --out runs/pencil
franka-prefs record paused-work --seed 0 --profile reverse --feedback retry --out runs/opposite
```

In the first two runs, the person restores just the mat Astra moved. The direct alternative is “No, the other mat.” `retry-only` and `other-only` remove the return gesture. `none` shows the same first robot move without a response. `incidental` shows the person moving a pencil while the mat stays on the shelf. In the opposite profile the person uses the clip to mark an item for filing, which flips the preferred ambiguous choice. Scope controls can share the same answer under both profiles.

The teaching action is deliberately scripted to elicit a correction. It is a standardized stimulus. The measured cold baseline requires a fresh agent to choose a probe action. `--accepted` plays the accepted teaching action, allowing an ordinary successful interaction. Use `--transfer-seed` and `--order-seed` to cross surface color, position and option label with the preference. In the development layout with training seed 0, transfer seed 107 and option-order seed 1, selecting the same color or letter as in the first example fails. Reserve different layouts for confirmatory evaluation.

## Deliver the observations and write the note

For an image-capable model available to your local Codex CLI, use a separate ephemeral session per call. The model gets the sensor images as attachments and instructions to use only those images and the supplied text. The development Cycles run used this path with a medium reasoning effort.

```bash
export VLM_MODEL=gpt-6.2-astra
franka-prefs evaluate runs/undo --adapter franka-prefs-codex --out runs/codex-result
```

For an HTTP endpoint, use the following variant.

```bash
franka-prefs evaluate runs/opposite --adapter franka-prefs-vlm --out runs/opposite-result
franka-prefs evaluate runs/undo --adapter franka-prefs-vlm --shuffled runs/opposite-result/memory.md --out runs/undo-result
```

The included transport uses a multimodal Chat Completions endpoint you configure through `VLM_BASE_URL` and `VLM_MODEL`. Supply `VLM_API_KEY` if the endpoint requires one. An example base URL for a locally served model is `http://127.0.0.1:8000/v1`. The endpoint must accept image inputs and JSON-object responses. Another trusted adapter can read one JSON request on stdin and write one JSON object to stdout. The process starts fresh for each call, receives image bytes, timestamps, prompts and the relevant memory, and receives no scene names, filenames, poses or grader keys. The adapter is a trusted component with normal host permissions.

1. At task completion, sample the RGB stream and infer the interval of potential intervention. Reach duration determines the interval. The frozen observation budget for detection is up to 30 samples, so fast events can be missed. The synthetic speech transcript is a separate sensory channel.
2. Review the selected interval with sampled earlier context. Ask internally what happened, why the person may have acted, and what to reuse. If no interval is detected, user speech can still trigger an audit. Ordinary nearby movement can produce an empty note.
3. Save the inferred text to `memory.md`. If the auditor proposes a question, the result includes it. A supplied `--answer` is used only when a question was asked. A subsequent interaction can refine an existing note with `--prior`.
4. For each probe, start a fresh decision call in the cold, matched and optional mismatched conditions. The task image and option order stay identical within each pair. Simulator poses stay in the examiner record. The call logs retain prompts, content hashes and raw replies, with the sensor packet supplying the original bytes. A failure preserves the partial calls and error in its output directory.

The recorder archives research footage for reproducibility. The personalized memory consumed by the next trial is just the written note. The evaluator supplies the designated note to measure transfer. Learned note retrieval, automatic response to clarification and streaming intervention detection are separate research problems.

## Execute, assess and calibrate

```bash
franka-prefs execute runs/undo transfer A --out runs/action-a
franka-prefs audit --out runs/qa --seeds 0 1
python -m unittest discover -s tests -v
```

Use the letter returned by the decision model to replay its choice. Inspect the trajectory and endpoint in the output. MuJoCo inverse kinematics drives scripted primitives and the avatar follows seeded target motions. The primary recording path uses kinematic attachments. The independent paused-work contact model steps gravity, friction, loose components and settling with a prescribed carrier; its metrics characterize that separate model.

A real, rectified camera profile can be passed with `record --calibration rig.json --size WIDTH HEIGHT`. Reprojection can be validated with `python -m visual_prefs.calibration rig.json held-out-corners.json`. Profile schema and coordinate conventions are in [calibration.py](../visual_prefs/calibration.py).

For an experiment-level scorecard, lock a JSON list before running the evaluation. Include each planned trial even when a run fails. Paths are relative to the manifest file.

```json
[{"id":"p01-s107","family":"paused-work","bundle":"undo","evaluation":"undo-result","conditions":["cold","matched","mismatched"]}]
```

`franka-prefs summarize runs/plan.json --out runs/scorecard` reports paired gains, losses, ties and missing outcomes per family and phase. The full row table retains the planned denominator.
