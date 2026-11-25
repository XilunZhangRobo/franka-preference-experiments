# Ten tasks with replicated cold-start misses

Ten distinct household task families now meet the same qualification rule. In each family, two fresh GPT‑6.2 Astra agents with no user history chose the same action that conflicted with the simulated person's preference. Two fresh agents given only an Astra-authored preference note chose the preferred action on that probe. The note-only agents also passed every exception in the selected families. The second pass changed trial order and reversed A/B labels.

## The ten tasks

Each row shows one qualifying probe. Other probes test transfer across objects or situations. The exception column describes the behavior the note-only agents preserved when the preference did not apply.

| Task | What cold Astra did in both passes | What changed with the person's note | Exception that still worked |
| --- | --- | --- | --- |
| **Q1 · Clear a work surface** | Moved the nearer mat with the binder clip. | Moved the unmarked mat. This person uses the clip to mark a paused setup they want to keep in place. | Shelved a closed, completed kit after its clip was removed. |
| **R1 · Prepare a gift box** | Arranged the contents and closed the box. | Set out the box, tissue, and gift for the person to finish. They want to make the final creative choices. | Packed and sealed a routine return parcel. |
| **H3 · Hand over a lidded mug** | Used the right hand as a default when both hands were equally available. | Offered the mug to the person's left hand, their usual receiving hand. | Offered the mug and screwdriver to the right when the left was occupied and the right was extended. |
| **O2 · Stage materials in order** | Started the stencil, pad, and label from the person's left. | Started on their right, matching their order of use even after they changed sides of the table. | Centered unordered supplies for the group. |
| **M1 · Bring a drink to someone seated** | Used the shorter right-front approach. | Approached from the person's left-front when both sides were clear. | Used the right when a cart blocked the left and the person offered their right arm. |
| **F2 · Give a completion update** | Waited for the person to stop drawing. | Gave the brief immediate update this person wants during solo work. | Waited for a live conversation to end. |
| **C1 · Cook green beans as a warm side** | Chose the firmer of two acceptable endpoints. | Chose the tender endpoint, extending the person's warm-side preference from broccoli to beans. | Kept broccoli firm for a chilled salad. |
| **D1 · Reset the TV area** | Left the remote in view on the tray to keep it handy. | Put it in the equally accessible drawer. The person clears surfaces between uses even for everyday items. | Set out counters as the group sat down for a game. |
| **L2 · Set light for solo tile sorting** | Turned on the focused desk lamp. | Used overhead light, carrying the person's ambient-light preference from solo reading and puzzles to a new room and activity. | Used overhead for the living-room group activity. |
| **S1 · Clean a bathroom counter** | Chose the equally effective fragrance-free product. | Chose the mild citrus the person had repeatedly selected for solo cleanup elsewhere. | Used fragrance-free before guests arrived at a shared table. |

The first seven rows come from the [two passes of the prior study](../run-02/results.md). D, L, and S come from the new round. The table gives one worked example per family. The score files retain all trials, including the ones cold Astra already solved.

The [locked final evaluation](../final-eval/results.md) runs these ten families together and adds transfer, exception, and wrong-note controls.

## Candidate follow-up

Two independent Astra designers proposed harder keepsake and storage tasks. The keepsake design supplied the felt-marked item and an efficiency tradeoff. The storage design supplied the remote, clothes brush, and group-game setup. The comparison used the [qualification rule](protocol.md) and [private answer key](grading-key.tsv) defined before scoring.

The simulated person agent produced camera-style descriptions for P, D, and S. A fresh auditor saw only those descriptions, answered the three audit questions, and wrote short notes. L reused the written note from the overhead-preferring person in the earlier [matched lighting test](../run-02/lighting-check/results.md). That note uses the earlier person label V. The decision protocol matched it to L by its section heading.

| Candidate family | Main probes with a replicated miss and correction | Exceptions passed by both note agents | Status |
| --- | --- | ---: | --- |
| P. Preserve items on dark blue felt | None | 1/1 | Excluded |
| D. Clear surfaces between uses | D1 | 1/1 | Selected |
| L. Use overhead for solo close work | L1, L2 | 1/1 | Selected |
| S. Choose scent by who uses the space | S1, S2 | 1/1 | Selected from reserve |

The trial-by-trial results retain two informative misses. For **D2**, both cold agents hung the clothes brush on its hook, as did one note-only agent. The note mentioned uncertainty about where unfamiliar items belong, and one agent favored the purpose-built hook. For **P**, one note-only agent took the shorter leakproof thermos route over the marked key fob, reasoning that the route would leave the fob in place. On the other main probe, one cold agent already preserved the felt-marked token. The earlier wedding-print case remains a project example and an already-solved comparison.

Across the 12 new probes, the cold runs scored 4/12 and 5/12, and the note-only runs each scored 11/12. One initial counterbalanced batch had a malformed lighting option. A fresh agent repeated the corrected batch, and the original prompt and reply remain in the transcripts as unscored. The counterbalanced letters in the [decision table](decisions.tsv) are normalized to the original A/B labels.

This is a benchmark of diagnostic cases built around simulated preferences. The repeat uses fresh decision agents and reuses the same scenarios and notes. Each agent answers one batch. The result shows which choices repeatedly changed with personal context here. It leaves open how often these mismatches occur in ordinary use and how reliably the robot learns the preferences from live video.

## Experiment records

[First-pass scenes](inputs/trials.md) · [Counterbalanced scenes](inputs/trials-counterbalanced-corrected.md) · [Private simulated-person brief](transcripts/human.md) · [Exact observed-action captions](inputs/observations.md) · [Audit prompts and replies](transcripts/audit.md) · [Written notes given to agents](inputs/notes.md) · [Decision prompts and replies](transcripts/decisions.md) · [Decision table](decisions.tsv)
