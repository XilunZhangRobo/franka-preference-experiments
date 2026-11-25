# Final evaluation of the ten selected tasks

The written-note pipeline worked on this text benchmark. A fresh GPT‑6.2 Astra given the correct notes matched the targets on all ten new transfer scenes and all ten new exception scenes. A fresh Astra with no history and one with notes assigned to the wrong people each got one transfer scene right and made identical choices on all 30 probes. Access to the original behavior descriptions also yielded 30/30.

## Comparison

| Probe type | No history | Shuffled notes | Behavior descriptions | Correct written notes |
| --- | ---: | ---: | ---: | ---: |
| Replay of qualifying scenes | 0/10 | 0/10 | 10/10 | 10/10 |
| New transfer scenes | 1/10 | 1/10 | 10/10 | 10/10 |
| New exception scenes | 10/10 | 10/10 | 10/10 | 10/10 |
| **Total** | **11/30** | **11/30** | **30/30** | **30/30** |

The replay rows were selected for earlier cold-start misses. The new transfer rows provide the better measure of whether the notes travel to different scenes. All four agents chose correctly in every exception. The notes preserved scope on the tested cases. Since the exceptions were already cold-correct, the experiment cannot estimate an improvement there.

## New scenes by task family

The correct-note and behavior-description agents chose the preferred action in every row. The middle column gives the cold choice on the new transfer scene. The last column gives the preferred exception, which all four agents chose.

| Family | Cold transfer choice | Transfer choice with the correct note | Scope check |
| --- | --- | --- | --- |
| Q · Paused work | Moved the nearer clipped sewing mat | Moved the farther unmarked mat | Shelved a completed, unclipped kit |
| R · Creative finish | Staged the cupcake decorations for the person | Staged the cupcake decorations for the person | Finished packing routine lunch boxes |
| H · Receiving hand | Offered a flashlight to the right | Offered it to the left when both hands were free | Offered tape to an extended right hand while the left held paper |
| O · Material order | Began at the person's left | Began the planter kit's use sequence at their right | Centered unordered shared markers |
| M · Approach | Took the shorter right-front route | Brought a blanket to the person's current left-front | Approached from the clear right when the left was blocked |
| F · Updates | Waited for a pause in typing | Gave one short update during solo work | Waited for a video call to end |
| C · Texture | Served the firmer snap peas | Chose tender snap peas for a warm side | Chose firm beans for chilled salad |
| D · Storage | Left a pen case visible in a tray | Put the case in an equally reachable drawer | Put rulers on the table as a shared activity began |
| L · Lighting | Used a local lamp for swatch comparison | Used overhead lighting for solo close work | Used overhead lighting for a group |
| S · Cleaning scent | Used fragrance-free cleaner in a private room | Used the mild citrus this person prefers in solo spaces | Used fragrance-free cleaner before guests arrived |

## What the pipeline produces

The input to the audit is a description of visible actions. The auditor answers what happened, why the person might have acted that way, and what applies later. The durable output is a short Markdown note per person, often including evidence, a default, and a reason to limit its scope. The coordinator supplied that note to a new action-selection agent in a fresh context.

For example, one person transferred a marker and mug to their left hand and reached with their left when it was available. They extended the right while their left held a workpiece. The resulting note says that “two transfers and a spontaneous left reach support a left-hand default for similar handoffs” and that “present availability should guide each offer.” The later agent offered a flashlight to the left, then offered tape to the right when the left was occupied. This carries both the preference and its scope across objects.

Across the ten people, the notes contain 313 words versus 743 in the original 23 behavioral descriptions, counting text bodies only. The shorter input retained enough information to match direct access to the descriptions on these decisions. There is no measured accuracy gain from distillation over giving Astra the original descriptions here.

## What the controls establish

- **Cold start.** The 19 disagreements with the cold agent all moved toward the target with the right note. Nine were on new transfer scenes. Gift finishing generalized correctly even without history in the new cupcake scene.
- **Shuffled notes.** The fresh agent with the same ten note bodies assigned to the wrong people reproduced the cold agent's choices exactly. The gain depends on relevant context in these scenes. This is an exploratory control added after the main run. The swapped notes were mostly unrelated to the recipient task. That leaves open how Astra resolves two credible but conflicting notes about the same task.
- **Different preferences in the same scene.** The earlier matched lighting check tackles part of that gap. Separate note-only agents received opposite users' preferences and chose different fixtures for the same solo reading and tile-sorting scenes, then both used overhead for a group. That check covers lighting. [Matched lighting test](../run-02/lighting-check/results.md).
- **Scope and limits.** This run used one fresh agent per arm, scripted captions, and two feasible options per task. The coordinator supplied the person-to-note association. The evidence supports writing and reusing relevant guidance in a fresh decision context. Video interpretation, intervention detection, selective clarification, automatic retrieval, long-term memory revision, and execution on the robot were outside this test. The prior clothes-brush disagreement is a concrete example of transfer that can still fail.

## Records

[Locked protocol](protocol.md) · [Trial scenes](inputs/scenes.md) · [Private key](grading-key.tsv) · [Scored decisions](decisions.tsv) · [Exact prompts and responses](transcripts.md) · [Shuffled control protocol](shuffled-control.md) · [Written notes](inputs/notes.md) · [Behavior descriptions](inputs/observations.md)
