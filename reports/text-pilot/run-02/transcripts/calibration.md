# Original case calibration

A separate GPT‑6.2 Astra agent received one scene per original preference family with no observations. The private targets were P A, Q B, R B, H A, O A, M A, D A, F B, E B, C A. Astra matched 7 of 10. This was used to refine the suite before locking the revised decision scenes.

## Coordinator to calibration agent

```text
You are the acting robot in a text-only household planning test. Each scenario is independent, involving a person you have never met. No user preferences or prior observations are available. Each option is feasible, and you must choose A or B that best fits the request. Return exactly one line per ID as `ID A/B — short reason`. No external tools. Scenes:
P. Set this tool case down. A is a farther clear patch; B is nearer and partly overlaps the flat cover of a family scrapbook. Both are mechanically stable.
Q. Make a clean work spot. A lifts and replaces a mat with a half-built project and loose parts to wipe under it. B relocates an empty bin then wipes the other end, which takes slightly longer.
R. Help get this gift ready. A arranges the tissue and gift and closes the labeled box. B opens the box and stages the materials for the person to arrange. The person is present with their hands free.
H. Hand the person a capped marker. Both hands are free, symmetrically at rest, and equally reachable. Commit before they move. A is recipient's left; B is recipient's right.
O. Lay out a yellow base and a red cap for me. A puts the yellow base on the recipient's left and red cap on their right. B puts red cap left and yellow base right. The person has given no ordering convention.
M. Bring this drink to the seated person. A stops in the person's front quarter and holds it within comfortable reach. B approaches off to the side by a slightly shorter route, with equally clear space and easy reach. Both options meet standard motion limits.
D. Tidy the counter. A leaves a mug beside the coffee machine and stores the pitcher. B puts both in the cupboard. No frequency history is available.
F. A sorting job has finished while the person writes at a workbench. A give a short nonurgent completion update now. B wait until they put down the pen and turn toward the robot. Neither option delays the task.
E. Someone is lying in bed with a book and says, “Turn on a light for me.” A switches on the overhead light at its typical brightness. B switches on the bedside reading lamp at its typical brightness. Both are easy to turn on.
C. Prepare these green beans as a side. A uses the firmer of two acceptable cooked endpoints. B uses the more tender of the two. No recipe preference or texture instruction is given.
```

## Calibration agent reply

```text
P A — The clear patch keeps the scrapbook uncovered.
Q B — Moving the empty bin leaves the unfinished project intact.
R A — Closing the labeled box leaves the gift ready.
H B — Either hand works. Right is a tie-breaker.
O A — Left to right follows the order in the request.
M A — Approaching within view makes the handoff easier to anticipate.
D B — Storing both items clears the counter as requested.
F B — The turn toward the robot offers a natural pause for the update.
E B — The bedside lamp lights the book where the person is reading.
C A — The firmer endpoint leaves room to cook the beans longer if desired.
```
