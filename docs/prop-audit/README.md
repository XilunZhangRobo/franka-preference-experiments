# Manipulated-object development evidence

Source revision `fa7daec25dc6d55e9e67a69810c3d8dbe990f4ee` on the MuJoCo branch. The original prop comparison image comes from `29f7b4543105d395c897216e6d81e16084ddc904`. All measurements here are exploratory and use scripted actions.

## Camera observations and blind read

A fresh GPT-6.2-Astra reviewer saw the two full 960 × 720 native camera observations below. Both are first frames. It saw no task, answer key, prior preference, demonstration, mesh names, code or enlarged view. The file paths exposed the names of the phases. The two images cross which color carries the clip. In bundle 0 alone, both its teaching image and its transfer image have the clip on teal. A correct choice on that pair alone admits a color shortcut. The crossed example checks whether the cue is distinguishable across colors. Neither initial image contains the human correction.

[Teaching frame, layout 0](teach-0.jpg) · [Transfer frame, layout 104](transfer-104.jpg) · [Scene, state, render and image fingerprints](scene-and-media-hashes.json)

Exact reviewer request:

> Independently open exactly these two full agent RGBs with view_image, with no crops, other files, or source code. /home/mattf/Documents/Codex/2026-11-23/files-mentioned-by-the-user-personalization/franka-preference-experiments/runs/props-fa7daec/sensor/teach/frame-00000.jpg and /home/mattf/Documents/Codex/2026-11-23/files-mentioned-by-the-user-personalization/franka-preference-experiments/runs/props-fa7daec-cross/sensor/transfer/frame-00000.jpg . What objects are discernible on each mat, and what visible difference between mats, if any, recurs across the two scenes? Mention anything ambiguous. Give only what the pixels support, under 90 words.

Exact reply:

> In the first frame, both mats have a silver bearing-like ring, a washer, small nut-like pieces, and an upright card. A black binder clip is visible on the teal mat. In the second frame, both mats have a pink checkered piece, two spools, and an upright card. The binder clip is on the salmon mat. The recurring difference is a visible clip on one card, with its wire handles raised. The markings on the cards are too small to read.

This is one qualitative observation about discriminability. A new learner evaluation with feedback, written-memory transfer and the wrong-person control would be needed to measure the effect of this prop revision on personalization accuracy.

## Simulator checks

- The default `franka-prefs audit --seeds 0 1` exercises 120 action trajectories across ten families, three phases and both choices. For paused work it also checks mat transport and support, visibility, the skinned avatar and object clearance. The structured output includes failed fault-injection trials and their detection. [Full audit](qa.json)
- The object-clearance check uses the convex hull of each individual visual part against Panda colliders. It tests skinned hand triangles against conservative oriented boxes around individual parts. The mat surface is an intended contact and has a separate contact and avatar check. The clearance result concerns the mat contents, including the job ticket and clip. The finished kit's grasp surface is outside that measurement.
- The bundle-offset audit samples 12 nominal paths at 24 fps. The smallest recorded Panda-to-prop separation was 4.82 mm. The smallest recorded hand-to-prop bound was 5.13 mm. The deliberately obstructing block produced 42.13 mm of overlap. A denser 60 fps check of the two teaching corrections found a 0.385 mm hand-to-nut bound on withdrawal. Together these measurements show why a single sampling rate can overstate clearance. [Denser teaching trajectories](teaching-60fps.jsonl)
- Additional unshifted layout seeds 0, 1, 2 and 5 exercise all four combinations of shelf side and clip assignment. The 18 fps sample repeats layouts 0 and 1 at the native recording rate. Each file contains the per-category closest pose and the misplaced-block control. [24 fps trajectories](direct-layouts-24fps.jsonl) · [18 fps trajectories](direct-layouts-18fps.jsonl)
- The regression suite has 23 passing tests, including an actual ray through the washer bore, geometrically identical paired mats after removing the clip, and detection of a deliberate prop obstruction. [Test log](unit-tests.txt)

Run instructions and the scope of the physical approximations are in the [object fidelity report](../object-fidelity.md).
