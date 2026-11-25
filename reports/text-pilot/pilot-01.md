# Text pilot 01

Two Astra subagents played the robot and the person. The coordinator supplied the scenes, collected the robot's cold choices, and relayed the simulated person's observable actions. The robot received no private preference descriptions. The training motions were seeded execution records, so the wedding-photo intervention could be tested regardless of what the cold model might have done on that run.

The pilot tests inference from provided text, note writing, and later choices. It does not test camera perception, automatic event detection, or physical execution.

[Exact transcript](transcripts/pilot-01.md) records the role briefs, private inputs, and messages actually passed to each agent.

| Case | Cold choice | Choice after audit, before clarification | What we learned |
|---|---|---|---|
| **P · Wedding print** | **A.** Set the tool case on the farther clear surface. | **A.** Same placement. The robot said its drink-and-photo note did not apply. | The agent inferred concern about spills from the wipe, but wrote a rule narrower than the simulated user's preference for protecting meaningful originals. The cold choice already kept the scrapbook clear. |
| **Q · Unfinished work** | **B.** Move the empty bin and clean the other end. | **B.** Same action, now with the note cited. | The note captured protecting both layout and location. The cold model already chose to preserve the project. |
| **R · Personal finishing touch** | **A.** Arrange the gift and close the box. | **B.** Stage materials and leave the final arrangement to the person. | The robot used the intervention during card decoration to infer a preference that carried to a different task. |
| **S · Unrelated activity** | — | No note written. | Wiping a windowsill across the room gave no grounds for changing mug handling. |

In this single run, the plan agreed with the private brief on two of three cold choices and all three after the audit. Only the gift case changed. The same robot agent retained the earlier conversation throughout, and the same later scenes were used for the cold and post-audit choices. This is an exploratory result. It cannot separate the value of saved notes from the effect of having the earlier interaction in the model's context.

## What the agents actually said

The robot's first-pass notes are saved in [P](notes/p-keepsakes.md), [Q](notes/q-work-in-progress.md), and [R](notes/r-finishing-touch.md). On the unrelated-motion control it said, “Nothing observed connects it to the mug or print,” and wrote no note.

For the gray-area probe, the robot saw a print in a clear sleeve. Its short route crossed the print, while a detour would require moving an empty bin. It asked, “Would you like me to move the empty bin so I can carry the mug around this print?”

The simulated person replied, “No need to move the bin; that’s a laminated copy, so you can carry the mug over it.” The robot chose the direct route and produced a [revised note](notes/p-keepsakes-revised.md) confirming the exception for that print. The question resolved which route to take. The person volunteered the reason that made the answer reusable.

## Next controlled run

Start the transfer conditions in independent robot contexts. Give one the new scene alone, another the scene plus the behavior-only observation, and a third the scene plus the written note. This can separate generic knowledge, direct reuse of the interaction, and reuse of the note.

For the wedding case, distinguish the **person's concern** from the **action that revealed it** in the audit. Compare the original audit with one that asks what other kinds of action could affect the same concern. Score broader scope and wrong generalizations on new tasks, including cases where the generic model chooses a different feasible option and cases with a laminated duplicate. Keep the original behavior-only prompt as the control so any gain can be attributed to the review design.
