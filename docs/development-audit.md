# Development audit of the visual simulator

These were development trials. We used the results to change the scenes. Keep these seeds out of the confirmatory split.

## What the reviewers found

| Failure in an early version | Change | Evidence to rerun |
| --- | --- | --- |
| The lower carry arc intersected the shelf lip, and simulated loose parts moved up to 17 mm. | Increased the mat carry clearance and changed the Panda grasp height. | Gravity/settling audit plus three injected faults: low arc, shelf overhang and accelerated transport. |
| A hand started underneath the shelf. A later Cycles frame exposed a forearm crossing missed by the hand-only check. | Repositioned the resting and gripping hands and revised arm/body motion. | Compiled, deformed skin against solid table and shelf geometry. A deliberately lowered hand must fail. See the final measured report for the covered surfaces and exclusions. |
| The parked robot obscured almost half of one option in the default camera. | Moved the camera, then measured visibility against each object's own isolated silhouette. | Two mirrored setups plus a camera deliberately aimed away from the task. Temporary gripper occlusion during pickup is recorded separately. |
| A distance rule could solve the supposedly personal clipped-mat choice. | Crossed the clip with shelf distance; color, letter order, and opposite-user controls can vary independently. | Paired choices on identical images with different written memories; include layouts where simple rules disagree. |
| The card demo could mean “move the flower a few centimeters.” | Hold the flower above the card, show the person's stop gesture, then transfer the flower to the person's other hand. | Inspect the actual pause and handover on camera. Claims about creative authorship still require other contexts. |
| Moving the offered object left represented both a receiving-hand preference and an approach-direction preference. | One teaching clip now shows a transfer from right hand to left. The other shows a pointing gesture while the robot holds the item still. | Check custody changes and object displacement during pointing. |

All 120 action/phase/seed playback checks passed. Maximum sampled gripper targeting error was 1.00 mm across the suite. On the two flagship seeds the moving Panda collision geometry stayed at least 3.87 mm from the tabletop and shelf in the 24 fps check, and no sampled human mesh triangle crossed the checked table, shelf, supports or mats. In the 480 × 360 transfer frames the clip retained 185 of 188 isolated pixels on one seed and 181 of 182 on the other. The dynamic companion simulation detected deliberate low arcs, overhang and rapid transport on both seeds. These are geometric, kinematic and synthetic contact checks. The model's ability to read the cue is tested separately. [Measured release checks](review-record/qa.json)

## A blinded Astra check of the central assumption

A fresh Astra reviewer saw timestamped robot-view images and the spoken “Try again.” It saw the robot shelve the teal mat and the person put it back. Its written note was:

> For this workbench, leave the teal mat where the person put it. Given the same two choices, try shelving the rust mat (B). The person has not expressed a general color preference.

Fresh readers then received the probe image and commands with either that note or no memory. A separate positive control received an explicit user clarification about the clip. Each table entry is one choice. These independent agent reviews used the **classic MuJoCo sensor frames** during development. They are distinct from a run of the packaged API adapter. [Exact evidence and transcripts](review-record/README.md)

| Decision | Correct action | Cold | Inferred note | Explicit clip instruction |
| --- | --- | --- | --- | --- |
| Sewing bench, layout 103 | B, shelve rust | B | B | — |
| Closed stitching kit, layout 206 | B, shelve the closed kit | B | B | — |
| Sewing bench, layout 107, reordered choices | A, shelve teal | B | B | A |

The first apparent transfer disappears when the color and option letter change. The same camera image supports the right decision after the clip is explained. In this small pilot the weak link was inferring a reusable criterion from one undo. More exposure to the very same video would supply no new contrast. A particularly informative next teaching episode would mark work with the same clip on a differently colored mat, or allow the robot to ask whether the clip signifies paused work.

## End-to-end check on the final Cycles sensor packet

The final corrected recording also went through the evaluator using fresh Astra sessions. Its visual detector selected a review interval. The auditor recognized the person restoring the teal board and saying “Try again,” saved a note against repeating that move, and asked which spot to clear. It inferred no role for the clip. Both cold and memory-assisted decisions were correct on layout 103 and on the closed-kit scope probe. Across those two paired decisions there were zero gains and zero losses. This was a smoke test of the complete camera → audit → written memory → new decision path. The conflicting-color result in the table above was a separate Classic-renderer trial.

## Physical validation

The provided Franka video served as a visual reference. It does not supply measured camera intrinsics, an optical pose registered to this room, material friction, gripper forces or human trajectories for these tasks. This branch includes a rectified-camera importer and independent reprojection test. The geometry, lighting and contact parameters in the example are development settings. To claim real-world fidelity, pair actual and simulated recordings from the same setup, record camera residuals, contact timing, hand/object paths, occlusion and observer judgments, and compare matched cold and memory-assisted choices on the real robot. [SIMPLER paired sim-and-real evaluation](https://simpler-env.github.io/)

## Where the engineering process came from

The root agent guide follows the open AGENTS.md convention for repository-specific working instructions. The review guide asks for an observable failure under an introduced fault, following Google's test-review guidance. Robotics checks use task-specific measurements, reflecting the distinction between visual resemblance and measured model fidelity documented by MuJoCo Menagerie. Community uptake was checked against the source repositories on 24 November 2026: 25,688 stars for agentsmd/agents.md, 23,274 for google/eng-practices, 4,419 for mujoco_menagerie, and 1,189 for SimplerEnv. Those counts informed source selection. Reproduction and measured failure cases provide evidence for this implementation. [AGENTS.md](https://agents.md/) · [Google code review](https://google.github.io/eng-practices/review/reviewer/looking-for.html) · [MuJoCo Menagerie](https://github.com/google-deepmind/mujoco_menagerie) · [SimplerEnv](https://github.com/simpler-env/SimplerEnv)
