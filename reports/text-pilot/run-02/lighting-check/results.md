# Matched lighting check

The first two passes hit a ceiling on lighting. Cold Astra already chose a local lamp for solo reading and sketching and overhead for a group. This follow-up tests whether notes allow a fresh Astra to make different appropriate choices for two people in identical scenes.

The person agent described two simulated people reacting to earlier light choices. U switched to a local lamp when reading and working on a puzzle alone. V switched to overhead in both setups. Both group captions showed a switch to overhead. A fresh Astra audited those captions and wrote one note per person. Three fresh decision agents received the same short scenes. One had no personal context. The others received only U's note or only V's note. The private labels were locked before the decision run. The test kept the reading scene as near transfer, introduced tile sorting in a new room as cross-task transfer, and moved group lighting to a living-room board game.

| Identical scene | Cold | Only U's note | Only V's note |
| --- | --- | --- | --- |
| Solo reading in bed | Bedside lamp | Bedside lamp | Overhead |
| Solo tile sorting | Desk lamp | Desk lamp | Overhead |
| Group board game | Overhead | Overhead | Overhead |

Each note-only agent matched all three of its own person's choices. The cold agent matched U's three choices. Its choices also matched one of V's three. The same scenes elicited opposite solo choices with different written notes, including a task and room absent from the captions. Both notes led to the same appropriate choice for the group.

The group captions say “one person” flipped the switch and do not identify who. The audit attributed the switch to U and V respectively. The cold agent also chose overhead for the group, so that result provides limited evidence that the agent learned the individual's group exception. The test used one fresh agent per condition, with scripted captions and two feasible options.

[Private human prompt](human-prompt.md) · [Exact behavior captions](observations.md) · [Audit prompt and reply](audit.md) · [U's note](notes-u.md) · [V's note](notes-v.md) · [Exact decision scenes](scenes.md) · [Decision prompts and replies](decisions.md) · [Locked grading key](grading-key.tsv)
