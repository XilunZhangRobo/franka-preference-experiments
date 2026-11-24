# Preference experiment lifecycle

Use a short run card to distinguish exploration, locked evaluation, and physical validation. Exploration can begin with a single scene and seed.

## 1. Define a falsifiable claim

Record the family, unit of analysis, population of scenes, observed teaching cue, expected held-out action, and the exception where applying that preference would fail. Name at least one competing explanation and a trial on which it predicts a different action. For example, cross binder-clip position with distance to the shelf to distinguish preservation of active work from a distance rule.

## 2. Lock the comparison

Before viewing held-out outcomes, version the run card with commands, model and sampling settings, prompts, scoring rubric, thresholds, allowed exclusions and retry policy. Assign disjoint development and test seeds and record the split generator, seed list, and a hash of the manifest. Hold out object, layout, or context combinations required by the transfer claim. A new random seed can reproduce a familiar layout.

For each held-out scene, pair conditions on seed, camera, task, candidate actions and model settings. Randomize display order independently of correctness. Use a fresh model context per arm. Specify who provides the note and what evidence they see.

| Condition | Comparison it supports |
| --- | --- |
| No note | Estimate performance from the task and ordinary priors alone. |
| Matched note | Measure the change when this person's relevant history is available. |
| Wrong note | Substitute a plausible opposite preference and measure directional change in ambiguous scenes. |
| No feedback | Replay the teaching task with its corrective behavior and speech removed to measure learning from correction. |
| Incidental control | Match visible activity or note length while changing a cue unrelated to the target decision. |

Score ordinary transfer and exceptions separately. Label cases where the preferred action and ordinary default coincide. Declare which comparisons can identify personalization before interpreting their scores.

## 3. Inspect the protocol and challenge its tests

Save the exact model-visible request, ordered frames or clips, note, transcript with event times, raw response, parsed choice and scorer output. Keep a private manifest mapping opaque IDs to family, seed, condition, option permutation and answer key. Record content hashes, repository revision and local patch, asset revisions, dependencies, renderer, and model version. Check a serialized request for leaked keys, answer-bearing paths, privileged pose data or future feedback. Inspect representative frames at inference resolution.

Run the basic checks from the repository root.

```sh
franka-prefs assets
franka-prefs record paused-work --out runs/demo --seed 0 --feedback retry
python -m unittest discover -s tests
franka-prefs audit --out runs/qa --seeds 0 1
```

Ask a reviewer to inject a relevant fault in a disposable checkout, such as reversing left/right scoring, leaking a key into a prompt, or leaving a corrective frame in a no-feedback clip. Record which test failed and why. A clean run after restoring the implementation verifies recovery. Reviewers should inspect design, functionality, complexity and tests as well as the diff. [Google engineering code review](https://google.github.io/eng-practices/review/reviewer/looking-for.html)

## 4. Report enough evidence to advance

For every family, phase and condition, record planned, attempted, rendered, delivered, parsed and scored episode counts. List exclusions, retry counts and reasons. Report correct over planned and correct over scored, paired gains and losses versus controls, and uncertainty at the independently sampled unit. Repeated frames or retries belong to the same episode. Preserve failures and videos alongside successful examples. A synthetic fault can validate the scorer; a blinded run on held-out stimuli can support a behavioral result.

Advance a family from draft to visual pilot when a reviewer can decode the cue and actions from the delivered media and the confound checks distinguish the competing rules. Advance to a reported held-out result when the locked comparison and attrition record are available. After changing a scene, camera, action semantics or scoring, assign a new version, document the affected comparisons, recheck cue visibility and rerun affected pairs. If held-out results informed the change, reserve fresh test scenes for confirmation.

## 5. Calibrate a physical claim

Describe hardware, camera intrinsics/extrinsics, object dimensions and poses, robot and gripper geometry, and the task-specific quantity to compare. For camera registration, preserve the profile, measured corners, units, residuals and independent check points.

```sh
python -m visual_prefs.calibration profile.json corners.json
```

Pair simulated and physical trials by task and setup. Measure the relevant outcome in both, such as handoff timing, clearance or placement error. Specify tolerances in advance and report failed pairs and uncertainty. Record the hardware operator and reviewer who verified those measurements and the exact claim their sign-off covers. Kinematic playback, camera registration and use of a published robot model each establish different pieces of evidence. [SimplerEnv paired evaluation](https://simpler-env.github.io/) and [MuJoCo Menagerie model fidelity grades](https://github.com/google-deepmind/mujoco_menagerie)

Keep repository-specific instructions in the root agent guide so subsequent contributors can find these conventions. [AGENTS.md project](https://agents.md/)
