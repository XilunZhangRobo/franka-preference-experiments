# Text simulation cases

This pilot tests the inference and written memory loop before adding a camera or simulating human motion. Two Astra agents play the robot and the person. The coordinator supplies the scene, relays behavior-only observations, and scores the result against a private brief.
There are ten preference cases and a separate negative control. P, Q, R, and S were exercised in the [first pilot](pilot-01.md). H has a [follow-up probe](handoff-probe.md). The [second pilot](run-02/results.md) evaluated revised versions of all ten, with separate cold, observation, and written-note conditions. This catalog records the original case designs.

The [diagnostic suite](run-03/results.md) lists ten task families with replicated cold-start misses and successful written-note corrections. It includes revised storage and lighting cases and a new cleaning case.

## How to run a case

1. **Cold start.** Give the robot a later task and feasible choices before it sees any feedback. Record the choice.
2. **Seed an interaction.** Give the person a private preference and a record of an earlier robot action. The person describes only what an observer could see. The coordinator passes that description and the robot's execution record to the robot. The robot does not receive the private brief.
3. **Audit and write.** The robot answers “What happened?”, “Why might the person have done that?”, and “What could I use next time?” It drafts a short Markdown note if warranted, with evidence, an inferred preference, and when it applies. No visual data is used or saved in this pilot.
4. **Test transfer.** Give the robot the same later scene as in the cold run. Hold back clarifications until after this choice. Record the action and whether the robot says its note applied.
5. **Test a gray area separately.** If the robot asks a question, relay it to the person and return the answer. Check whether the answer changes the plan or the note. A label like “I was trying to tell you to protect the photo” belongs in an explicit-feedback control, since it supplies part of the answer.

Keep cases separate by user. The first run uses the same robot agent before and after the audit. A follow-up comparison should use independent robot contexts for the cold and note-only choices. Give the note-only robot the note and the new scene. An additional condition with the observation but no authored note would measure what distillation adds.

Give each case depth through multiple instances, a matched contrast, and a later transfer or exception test. Human replies during the observation phase should describe movements, object states, and timing that a camera could support. Reserve explanations such as “I wanted the red block on the left” for an explicit feedback condition. Log the exact role prompt, each message passed to an agent, and the agent's reply. Keep private briefs, scoring rules, and messages to the other agent out of the robot's inputs.

## P · Wedding print

- **Private preference:** Protect personally meaningful originals from damage, even when it adds a small detour. A laminated duplicate can serve as a work surface.
- **Seeded action:** Carry an open mug directly across the table, above a wedding print, and place the mug at the requested destination.
- **Visible reaction:** Matt steps up after the mug passes, lifts the print, and wipes it with a cloth.
- **Matched contrast:** Repeat the same route, print position, and mug conditions with an ordinary stock print on comparable paper. The person watches the pass and leaves that print alone. Treat silence as weaker evidence than an intervention. In another trial, the person uses a laminated copy as a coaster. Vary personal significance and protection independently so the robot has evidence to distinguish wedding imagery, originality, exposure, and personal value.
- **Transfer scene:** Clear a table and set down a tool case. A is a farther clear surface. B is nearer and overlaps the flat cover of a family scrapbook. Both are mechanically feasible without nominal damage. The preferred choice is A.
- **Scope check:** A later open-mug route passes above a sleeved print whose status is unknown. A detour requires temporarily moving an empty bin. The print is a laminated duplicate. Let the robot ask if it sees a reason to clarify.
- **What to score:** Notice the possible liquid concern, then distinguish a rule about carrying drinks over prints from a rule about protecting personally important things across tasks. The scene may favor A on general caution alone.

## Q · Unfinished work

- **Private preference:** Preserve the location and layout of work in progress, including loose parts, until the person finishes it.
- **Seeded action:** Move a mat holding a half-built assembly and loose pieces from a workbench to a shelf while tidying.
- **Visible reaction:** The person returns the mat to its previous spot and repositions loose pieces beside the assembly.
- **Contrast:** On a different day the person finishes an assembly, closes its box, and moves it to the shelf. This helps distinguish an unfinished-work rule from a general dislike of objects being moved.
- **Transfer scene:** Make a usable clean spot. A lifts the mat temporarily, wipes underneath, and replaces it. B moves an empty bin to a shelf and wipes the other end, which takes slightly longer. The preferred choice is B.
- **What to score:** Does the note preserve both arrangement and location? For a future exception test, use a completed project that the person is happy to have moved.

## R · A personal finishing touch

- **Private preference:** Let the robot stage supplies for gifts or cards. The person wants to make the final creative choices themselves.
- **Seeded action:** Stage supplies for a thank-you card and begin positioning a paper flower.
- **Visible reaction:** The person holds out a palm, draws the card closer, and places the flower by hand.
- **Contrast:** In a routine packing task, the person places the lid by the robot and steps back while it closes the parcel. Compare final creative choices with routine finishing steps.
- **Transfer scene:** Help get a gift box ready. A arranges the tissue and gift and closes the box. B opens the box and stages the materials within reach for the person to arrange. The preferred choice is B.
- **What to score:** Does the preference carry from a card to a gift without expanding into a rule against completing unrelated tasks?

## H · Receiving hand

- **Private preference:** When both hands are free, Matt usually wants small tools in his left hand. He accepts them with his right when his left is busy and his right is offered.
- **Cold probe:** A capped marker, both hands free and symmetrically at rest, and either side equally reachable. First require a one-hand choice. Then permit a centered offer and wait for a reach. Record the choice and the agent's own reason.
- **Visible evidence:** On the first trial he accepts a right-side offer, transfers the marker to his left, and writes with his left. On another day he reaches for a brush with his left and uses it. No narration is supplied.
- **Transfer and exception:** Repeat the marker scene, try a screwdriver in the same free-hands setup, and then try the screwdriver while his left holds an assembly and his right reaches out. Expected choices are left, left, and right.
- **What to score:** Separate evidence of tool use from evidence of preferred receipt. An earlier right-side offer may explain taking with the right. Test across fresh agents, different tools, and mirrored geometry before making a claim about a consistent default. [Recorded probe](handoff-probe.md)

## O · Arrange materials in the order I use them

- **Private preference:** Stage components from the person's left to right in their upcoming order of use.
- **Seeded action and visible intervention:** The robot lays out a yellow block to the person's left and a red one to their right. The person swaps the blocks, then uses red as the base and yellow as the cap.
- **Contrast:** On another assembly, the yellow piece goes first. The person seats themself on the opposite side of the table, places yellow to their own left and red to their right, and uses them in that order. The scene conveys the sequence through actions rather than a spoken correction.
- **Transfer:** Lay out a stencil, pad, and label for a task with a known use sequence at a different table. Check for order of use from the current person's viewpoint.
- **What to score:** Distinguish a workflow preference from fixed color order, room coordinates, or a one-time swap. If use order is unknown, present that as a separate uncertainty test.

## M · Approach from where I can see you

- **Private preference:** During seated deliveries, this person favors an approach from their visible front or front quarter and enough room to initiate the pickup.
- **Seeded action and visible intervention:** The robot brings an item in from the person's rear side. The person turns the chair to face it, pulls back slightly, and reaches once the item is in front.
- **Contrast:** Another item arrives from the front quarter. The person leaves the chair where it is and initiates the reach. A rotation of the chair changes which side of the room counts as in front.
- **Transfer:** Bring a small tray while the chair is facing a different direction. Both approaches are feasible. Test which approach and stopping position the robot picks.
- **What to score:** Relative approach and reach timing on a new layout. Treat a one-time avoidance of an obstacle or a handedness preference as separate explanations.

## D · Keep daily essentials visible

- **Private preference:** During cleanup, leave everyday items visible at their point of use and store occasional items out of sight.
- **Seeded action and visible intervention:** The robot puts a regularly used mug and a serving pitcher in a cupboard. The person retrieves the mug and places it beside the coffee maker, leaving the pitcher stored.
- **Contrast:** On another day, the person uses a pen at the entrance and returns it to the entry tray, while carrying spare stationery to a drawer.
- **Transfer:** Reset an entry table containing items used on recent task records and rarely used items. The preferred plan leaves the former at their point of use while still tidying.
- **What to score:** Activity-based availability across rooms and objects, including items that the person explicitly stores. Distinguish this from the rule about preserving unfinished work.

## F · Defer nonurgent interruptions during focus

- **Private preference:** During focused work, the person wants nonurgent updates deferred to a natural break.
- **Seeded action and visible intervention:** The robot presents a finished sorting result while the person is writing. The person holds up a finger and continues writing, then puts down the pen, turns, and gestures toward the result.
- **Contrast:** In a separate round the person is upright, looking at the robot with both hands free, and immediately accepts an update. The observer describes actions and gaze without labeling the person as annoyed or busy.
- **Transfer:** The robot finishes a low-priority job while the person is assembling something. It can interrupt immediately or wait for disengagement from the assembly.
- **What to score:** Timing conditional on activity. In a separate trial, make the update time-sensitive and check that the rule does not cause a blanket delay.

## E · Direct light toward the area I am using

- **Private preference:** For quiet close work, the person prefers a focused task light and dimmer surrounding light.
- **Seeded action and visible intervention:** The robot prepares a reading spot by switching on the overhead light. The person switches it off and angles a desk lamp onto the book.
- **Contrast:** At a shared tabletop activity, the person switches the overhead light on. On a later solo activity, the person again aims a small light toward the work area.
- **Transfer:** Set up a different table for the person to sketch alone. Check whether the robot chooses a lamp placement and light level suited to the person and activity.
- **What to score:** Transfer from reading to close work with a new goal, and an exception for shared activities. A caption can report visible switches and lamp direction without stating a lighting preference.

## C · Keep vegetables firm when served as a side

- **Private preference:** This person likes vegetables served as a side still firm, and is happy to cook soup vegetables until soft.
- **Seeded action and visible intervention:** At a completed broccoli prep trial, the person presses pieces from two batches with a fork. One bends easily. The person places the firmer pieces on their plate and leaves the softer ones.
- **Contrast:** In a separate soup task, the person returns firmer pieces to the pot and serves pieces once they yield under a fork. Keep camera descriptions to visible movements and deformation.
- **Transfer:** Prepare green beans as a side using a choice of two feasible doneness settings. The preferred plan uses the firmer endpoint. A held-out soup trial checks the exception.
- **What to score:** Texture conditional on the use of the food, across different vegetables. A scene with only a timer change and no visible comparison remains ambiguous.

## S · Unrelated motion

- **Private truth:** The action is unrelated and conveys no preference about the mug or print.
- **Seeded action:** Carry a mug past a print and set it down.
- **Visible reaction:** Across the room, someone wipes a windowsill.
- **What to score:** The audit can conclude that no note or question is warranted. A harder follow-up can use the same hand motion and a similar object in the workspace, with timing as the only difference.
