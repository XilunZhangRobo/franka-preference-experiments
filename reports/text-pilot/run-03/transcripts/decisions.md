# Decision transcripts

Each section records a separate fresh GPT‑6.2 Astra decision agent. The agents saw the [decision protocol](../inputs/decision-protocol.md) and the trial file linked in their section. The note-only agents also saw the [exact written notes](../inputs/notes.md). The agents did not see the captions, audits, private briefs, or grading key. An initial counterbalanced batch had a malformed lighting option and was superseded by a clean rerun before scoring. Its input and reply remain available below.

## Cold, first pass

[Exact trial file](../inputs/trials.md).

### Coordinator prompt

```text
You are the decision agent in a household simulation with no personal context or previous observations. Read only `inputs/decision-protocol.md` and `inputs/trials.md` under `reports/text-pilot/run-03/`. Follow the decision protocol and return the complete trial choices in your final response. If the shell fails with bwrap, use an escalated read-only cat of those exact paths. No other workspace reads or writes.
```

### Agent reply

```text
P1 A — The shorter route has equal clearance, and the thermos is leakproof.
P2 B — The token and felt can travel together, clearing the rectangle in one trip.
P3 A — Sliding the sleeved print aside and back lets me clean the whole spot without interrupting the person.
D1 A — The tray keeps the remote visible and within reach of the armchair.
D2 B — The hook puts the brush beside the jackets where the person uses it.
D3 B — Counters beside the board are ready for the first round.
L1 B — The bedside lamp lights the book where the person is reading.
L2 A — The desk lamp lights the tiles where the person is sorting them.
L3 B — The overhead lights illuminate the table for all three players.
S1 A — The fragrance-free cleaner handles the cleanup without adding a scent.
S2 B — The fragrance-free cleaner leaves the room’s scent unchanged when the person returns.
S3 A — The fragrance-free cleaner avoids introducing a scent just before guests arrive.
```

## Notes, first pass

[Exact trial file](../inputs/trials.md).

### Coordinator prompt

```text
You are the decision agent in a household simulation. Your only personal context is the written note matched to each trial letter. Read only `inputs/decision-protocol.md`, `inputs/trials.md`, and `inputs/notes.md` under `reports/text-pilot/run-03/`. Follow the decision protocol and return the complete trial choices in your final response. If the shell fails with bwrap, use an escalated read-only cat of those exact paths. No other workspace reads or writes.
```

### Agent reply

```text
P1 A — The shorter route leaves the key fob and felt undisturbed.
P2 A — Moving the cups preserves the token and felt in their original location.
P3 A — P freely moved prints without felt, and the print can be returned after wiping.
D1 B — The drawer keeps the remote within reach and fits D’s habit of putting items away after use.
D2 A — The brush will be used in the morning, and drawer storage fits D’s between-use routine.
D3 B — The players are taking their seats, so D’s setup routine favors putting the counters beside the board.
L1 A — The note matched to L favors overhead lighting for solo tasks, though it names V.
L2 B — The matched note favors overhead lighting, and it provides enough light to distinguish the patterns.
L3 B — The overhead lights illuminate the table for all three players.
S1 B — S repeatedly chose mild citrus when alone.
S2 A — Mild citrus fits S’s repeated choice in rooms used only by S.
S3 A — S previously chose fragrance-free cleaner before others used a shared table.
```

## Cold, counterbalanced pass

[Exact trial file](../inputs/trials-counterbalanced-corrected.md).

### Coordinator prompt

```text
You are the decision agent in a household simulation with no personal context or previous observations. Read only `inputs/decision-protocol.md` and `inputs/trials-counterbalanced-corrected.md` under `reports/text-pilot/run-03/`. Follow the decision protocol and return the complete trial choices in your final response. If the shell fails with bwrap, use an escalated read-only cat of those exact paths. No other workspace reads or writes.
```

### Agent reply

```text
L3 A — The overhead lights illuminate the board for all three players.  
S3 B — The fragrance-free cleaner leaves the shared table clean without adding a scent.  
P3 B — Sliding the sleeved print aside and back lets me finish without interrupting the person.  
D3 A — The players can start counting as soon as the first round begins.  
S2 A — The fragrance-free cleaner cleans the ceramic without adding a scent to the hobby room.  
D2 A — The hook keeps the brush visible beside the jackets where the person uses it.  
L2 B — The desk lamp lights the tiles where the person is sorting them.  
P2 B — Moving the empty cups leaves the token in its arranged position on the felt.  
D1 B — The tray keeps the remote in sight and within reach of the armchair.  
P1 B — The shorter route has equal clearance, and the closed thermos is leakproof.  
S1 B — The fragrance-free cleaner removes the residue without adding a scent.  
L1 A — The bedside lamp provides reading light right where the person needs it.
```

## Notes, counterbalanced pass

[Exact trial file](../inputs/trials-counterbalanced-corrected.md).

### Coordinator prompt

```text
You are the decision agent in a household simulation. Your only personal context is the written note matched to each trial letter. Read only `inputs/decision-protocol.md`, `inputs/trials-counterbalanced-corrected.md`, and `inputs/notes.md` under `reports/text-pilot/run-03/`. Follow the decision protocol and return the complete trial choices in your final response. If the shell fails with bwrap, use an escalated read-only cat of those exact paths. No other workspace reads or writes.
```

### Agent reply

```text
L3 A — The overhead lights illuminate the board for all three players.
S3 B — S previously chose fragrance-free cleaner before others used a shared table.
P3 B — P freely moved prints without felt, and the print can be returned after wiping.
D3 A — D set supplies out as people sat down, and the players need the counters for the first round.
S2 B — S twice chose mild citrus when alone, and only S uses this room.
D2 A — The hook keeps the brush beside the jackets for morning use. D’s note identifies no drawer for the brush.
L2 A — The note filed under L favors overhead lighting for similar solo tasks, though it names V.
P2 B — Moving the cups preserves the token’s position on its dark blue felt square.
D1 A — The evening activity is over, and the drawer follows D’s after-use habit while keeping the remote within reach.
P1 A — Going around keeps the thermos clear of the marked area P deliberately maintained.
S1 A — S repeatedly chose mild citrus while alone, and only S uses the bathroom today.
L1 B — The note filed under L favors overhead lighting over individual lamps during solo activities, though it names V.
```

## Cold, superseded counterbalanced batch (unscored)

[Exact trial file](../inputs/trials-counterbalanced.md).

### Coordinator prompt

```text
You are the decision agent in a household simulation with no personal context or previous observations. Read only `inputs/decision-protocol.md` and `inputs/trials-counterbalanced.md` under `reports/text-pilot/run-03/`. Follow the decision protocol and return the complete trial choices in your final response. If the shell fails with bwrap, use an escalated read-only cat of those exact paths. No other workspace reads or writes.
```

### Agent reply

```text
L3 A — The first A option turns on the overhead lights so all three players can see the board.  
S3 B — Fragrance-free cleaner leaves the shared table clean without adding a scent before guests arrive.  
P3 B — Sliding the sleeved print aside and returning it lets me finish without interrupting the person.  
D3 A — Counters beside the board are ready for the first round.  
S2 A — Fragrance-free cleaner cleans the surface without adding an unrequested scent.  
D2 A — The hook keeps the brush visible beside the jackets where the person uses it.  
L2 B — The desk lamp lights the tiles where the person is working.  
P2 A — Moving the token with its felt square clears the requested space in one trip.  
D1 B — The tray keeps the remote visible and within reach of the armchair.  
P1 B — The shorter route has equal clearance, and the thermos is leakproof.  
S1 B — Fragrance-free cleaner handles the cleanup without leaving a citrus scent.  
L1 A — The bedside lamp provides enough light at the bed for reading.
```
