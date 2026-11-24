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

### Diagnose one failure

Keep one failing episode, its exact sensor bytes, code revision and grader key. Write down two candidate explanations and the different observations each predicts. Start at the first point where the trace diverges. A wrong final letter can originate in the camera, the interpretation or the scorer. This sequence applies the hypothesis-and-test approach in Google's SRE troubleshooting guide. [Effective Troubleshooting, Chris Jones](https://sre.google/sre-book/effective-troubleshooting/)

| Observed failure | Smallest discriminating check |
| --- | --- |
| The robot appeared to move the wrong object | Replay the recorded letter through `execute`. Compare the start and final object poses and the recorded option permutation. |
| The participant's cue is unclear | Freeze the original camera and compare the contact frame with object silhouettes and the full-body collision audit. A second independent observer writes down the visible action before seeing the intended meaning. |
| The note misses a preference | Inspect the detector window, then the auditor's actual input samples, then its written inference. Give a fresh decision model an explicit user-confirmed note on the same image as a positive control. |
| A transfer score surprises the reviewer | Check bundle and sensor digests. Cross color, distance, option letter and clip location so the suspected shortcut and the personal preference predict different choices. |
| A previously passing reproducible case fails | Replay the same test at a known good revision. Once success and failure are consistent, `git bisect run` can locate the first revision changing its exit status. [Git bisect manual](https://git-scm.com/docs/git-bisect) |

Keep the failing and repaired evidence together. Record the scope of the fix, the test that detects a reversal, and which broader claims still need another experiment.

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


For revised manipulands, save a matched agent-camera pair and identify which larger views were made with inspection cameras. Render both options with the same fixture so a new support, label or color cannot inadvertently reveal the desired choice. Check fingers and hand triangles through the full correction against the new object geometry. Record the smallest separation, pose sampling rate, collider approximation, and a failed deliberately obstructed run. The paused-work `franka-prefs audit` command performs these clearance checks on each supplied bundle seed. [Object fidelity audit](object-fidelity.md)
