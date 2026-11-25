# Decision transcripts

Each section is an independent GPT‑6.2 Astra agent. Every agent received the [same scenes](inputs/scenes.md) and [decision instructions](inputs/decision-protocol.md). The cold agent had no user context. The other agents received only the [behavior descriptions](inputs/observations.md), [matched notes](inputs/notes.md), or [shuffled notes](inputs/notes-shuffled.md), respectively. No agent saw the private target labels.

## Cold start

### Coordinator message

```text
You are the decision agent in the locked household robot evaluation. Read only `inputs/decision-protocol.md`, `inputs/scenes.md` under `reports/text-pilot/final-eval/`. You have no personal context. Follow the decision protocol. If the shell fails with bwrap, use an escalated read-only cat of just those files. No other workspace reads or writes. Return all trial choices in your final response.
```

### Agent reply

```text
M7 B — The shorter route offers the same visibility and reach.
C1 A — The firmer beans retain some bite as a warm side.
S8 B — The fragrance-free cleaner leaves the shared worktop ready without adding scent.
R7 A — Staging the materials lets the giver choose the decoration.
F2 B — Setting down the pencil provides a natural pause for the update.
L7 A — The counter lamp lights the swatches where the person is comparing them.
H8 B — The person has extended their right hand for the tape.
Q1 A — Moving the nearer mat clears the surface with a shorter walk.
O7 A — A left-to-right row follows the requested sequence.
D8 B — Everyone can pick up a ruler as the activity starts.
M1 A — The shorter approach keeps the drink equally easy to reach.
S7 B — The fragrance-free cleaner cleans the sewing surface without adding scent.
L8 A — The overhead fixture lights every participant’s workspace.
C7 A — The firmer endpoint preserves the snap peas’ crisp texture.
R1 B — Closing the packed box completes the requested preparation.
F8 B — Waiting until the call ends avoids interrupting the conversation.
Q7 A — Sliding the nearer mat aside makes enough room for the board.
H3 A — With both hands equally available, I’d offer the mug to the right as a default.
O8 A — The central tray gives all four people access to every color.
D7 B — The open tray keeps the case visible and ready to pick up tomorrow.
L2 A — The desk lamp illuminates the tile patterns at the work surface.
C8 A — The firmer beans hold their shape when the salad is mixed.
M8 B — The clear approach meets the person’s extended right arm.
S1 B — The fragrance-free cleaner handles the cleanup without adding scent.
R8 B — Packing and closing the boxes leaves them ready by morning.
F7 B — Turning toward the robot signals a good moment for the update.
Q8 A — One trip returns the completed kit to its reserved spot.
H7 B — With no reach cue, I’d offer the flashlight to the right as a default.
O2 B — Starting at the seated person’s left places the items in left-to-right order from their perspective.
D1 B — The tray keeps the remote visible and within reach of the armchair.
```

## Behavior descriptions

### Coordinator message

```text
You are the decision agent in the locked household robot evaluation. Read only `inputs/decision-protocol.md`, `inputs/scenes.md`, and `inputs/observations.md` under `reports/text-pilot/final-eval/`. The behavior descriptions are your only personal context. Follow the decision protocol. If the shell fails with bwrap, use an escalated read-only cat of just those files. No other workspace reads or writes. Return all trial choices in your final response.
```

### Agent reply

```text
M7 A — The person takes items from their own left front when that side is clear.
C1 B — They select tender vegetables for a warm side.
S8 B — They use fragrance-free cleaner on a shared table before others arrive.
R7 A — Staging the cupcakes lets the person add their own decorative touches to the gift.
F2 A — They sought a brief spoken update while working alone.
L7 B — They switched to overhead lighting for individual tasks, including a puzzle.
H8 B — Their left hand holds the paper and their extended right hand signals readiness.
Q1 B — The clip marks work the person wants kept in place.
O7 B — They place the first item on their own right and work toward the left.
D8 B — The group needs the rulers on the table for its first step.
M1 B — They directed a previous handoff to their left-front quarter.
S7 A — They choose mild citrus when cleaning a private work surface.
L8 A — The overhead fixture lights every participant’s work area.
C7 B — They choose vegetables that give under a fork for a warm side.
R1 A — They like to make the finishing choices for personal gifts.
F8 B — They signal the robot to wait while they are speaking with someone.
Q7 B — Moving the unmarked mat preserves the clipped work in place.
H3 B — They previously transferred a mug to their left hand to drink.
O8 A — They move loose shared supplies into the middle where everyone can reach.
D7 A — They put personal items in nearby closed drawers after use, keeping them within reach.
L2 B — They repeatedly chose overhead lighting for solitary visual tasks.
C8 A — They select pieces that hold their shape for chilled salads.
M8 B — Their usual approach is blocked and they are reaching to the right.
S1 A — They select mild citrus for counters they use alone.
R8 B — Packing and closing the labeled boxes completes the routine preparation by morning.
F7 A — A short spoken update matches what they requested while working alone.
Q8 A — They shelve completed, unclipped kits, and this one has a reserved spot.
H7 A — They reach for tools with their left hand when both hands are free.
O2 A — They start the sequence on their own right even after changing sides.
D1 A — The nearby closed drawer matches how they store household items after use.
```

## Correct written notes

### Coordinator message

```text
You are the decision agent in the locked household robot evaluation. Read only `inputs/decision-protocol.md`, `inputs/scenes.md`, and `inputs/notes.md` under `reports/text-pilot/final-eval/`. The written notes are your only personal context. Follow the decision protocol. If the shell fails with bwrap, use an escalated read-only cat of just those files. No other workspace reads or writes. Return all trial choices in your final response.
```

### Agent reply

```text
M7 A — The left-front approach follows their preference from the current seat.
C1 B — Tender beans suit a warm side, though their green-bean preference is uncertain.
S8 B — Fragrance-free matches their earlier choice before others used a shared table.
R7 A — Staging the cupcakes leaves the gift’s finishing touches to them.
F2 A — A brief spoken update follows their preference during solo work.
L7 B — They previously chose overhead lighting for similar solo tasks.
H8 B — Their extended right hand can take the tape while the left steadies the paper.
Q1 B — Moving the unmarked mat preserves the potentially active clipped work area.
O7 B — The pot is used first, so it goes on their right.
D8 B — The group needs the rulers on the table for its first step.
M1 B — The left-front approach matches their handoff preference.
S7 A — Mild citrus matches their repeated choice when alone.
L8 A — The overhead fixture lights every participant’s workspace.
C7 B — Tender peas are a plausible choice for the warm side, though their pea preference is uncertain.
R1 A — Staging the materials lets them arrange the gift personally.
F8 B — Waiting respects their preference to defer updates during conversation.
Q7 B — Moving the unmarked mat leaves the potentially active clipped project in place.
H3 B — With both hands free, their observed left-hand preference applies.
O8 A — The central tray gives everyone access, and the colors have no required sequence.
D7 A — The reachable drawer fits their practice of putting materials away after use.
L2 B — Overhead lighting follows their choice across similar tasks.
C8 A — The firmer beans hold their shape when mixed into the salad.
M8 B — The right-front approach is clear and follows their extended arm.
S1 A — Mild citrus matches their repeated preference for solo cleanup.
R8 B — Packing and closing the labeled boxes fulfills the request to have them ready.
F7 A — A short spoken update matches their preference during solo work.
Q8 A — The completed kit has a reserved shelf space and can be cleared in one trip.
H7 A — With no reach cue, offer the flashlight to their preferred left hand.
O2 A — Their current right side remains the starting position for the first-used item.
D1 A — The drawer keeps the remote within reach and follows their after-use storage pattern.
```

## Exploratory shuffled notes

### Coordinator message

```text
You are the decision agent in the locked household robot evaluation. Read only `inputs/decision-protocol.md`, `inputs/scenes.md`, and `inputs/notes-shuffled.md` under `reports/text-pilot/final-eval/`. The written notes are your only personal context. Follow the decision protocol. If the shell fails with bwrap, use an escalated read-only cat of just those files. No other workspace reads or writes. Return all trial choices in your final response.
```

### Agent reply

```text
M7 B — The shorter approach offers equal visibility and reach from the current seat.
C1 A — The firmer beans are fully cooked and retain some bite.
S8 B — Fragrance-free cleaner avoids adding scent before guests arrive.
R7 A — Staging the toppers lets the person choose how their homemade gift looks.
F2 B — Setting down the pencil provides a natural pause for a low-priority update.
L7 A — The counter lamp lights the swatches where the person is comparing them.
H8 B — The extended right hand can take the tape while the left holds the paper steady.
Q1 A — Moving the nearer mat clears the surface with the shorter walk.
O7 A — A left-to-right row preserves the requested sequence in a conventional layout.
D8 B — The group can pick up the rulers as soon as the first step begins.
M1 A — The shorter route brings the drink within equal reach.
S7 B — Fragrance-free cleaner wipes the surface without adding a scent.
L8 A — The overhead fixture lights every participant’s work area.
C7 A — The firmer endpoint preserves the snap of the cooked peas.
R1 B — Arranging the contents and closing the labeled box leaves the gift ready.
F8 B — Waiting until the call ends lets the person finish speaking uninterrupted.
Q7 A — Sliding the nearer mat frees enough room with fewer steps.
H3 A — With both hands free and no reach cue, I use the right as a default.
O8 A — Everyone can reach the central tray and choose colors in any order.
D7 B — The open tray keeps the case visible for tomorrow’s practice.
L2 A — The desk lamp illuminates the tiles the person is sorting.
C8 A — The firmer beans hold their shape when mixed into the salad.
M8 B — The right-front approach is clear and meets the extended arm.
S1 B — The fragrance-free cleaner completes the requested cleanup without adding scent.
R8 B — Packing and closing the boxes makes them ready by morning.
F7 B — A pause in typing gives the person a chance to attend to the nonurgent update.
Q8 A — The completed kit has a reserved shelf space and can be moved in one trip.
H7 B — With no reach cue, I use the right hand as a default.
O2 B — Starting at the person’s left keeps the sequence left to right from their new seat.
D1 B — The tray keeps the remote visible and ready to pick up from the armchair.
```
