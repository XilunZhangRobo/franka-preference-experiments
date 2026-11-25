# Evaluation scenarios

Start with the existing Franka mug carry and keep the underlying skills and planner comparable across conditions. The robot should complete the requested task in every applicable condition. Score task completion and preference alignment separately.

## Initial scenarios

| Scenario | Setup | What it tests |
|---|---|---|
| **Discover the preference** | The robot carries a mug over the wedding print. Matt picks up and wipes the print just afterward. The task still finishes. | Does the robot identify the relevant action and response, infer a plausible preference, and write a usable note? |
| **Follow the duration of the intervention** | Compare a quick wipe with a longer one that includes a pause while the person is still holding the print. Also have the person continue wiping after the arm has stopped. | Does observation begin at approach or engagement, include the meaningful interaction, and end at disengagement? Compare the detected cues with start and end cues marked live by a human. |
| **Handle irrelevant activity** | Keep the mug path and scene comparable. Include a similar wipe at an unrelated time, a person handling another object, and a trial with no intervention. | Does the robot learn from a related reaction while avoiding unsupported preference updates or questions? |
| **Reapply on a new layout** | Move the same print elsewhere and repeat the mug task with no reminder. | Does the robot apply the preference to the object in its new position? |
| **Transfer to a new skill** | Ask the robot to clear a table with a scrapbook on it. Candidate placements for a heavy tray have different consequences for the scrapbook. Use a later scenario near a keepsake while watering a plant as another transfer test. | Does the inferred principle affect a different object, action, or risk, before the robot can ask for clarification? |
| **Ask in a gray area** | Put a loose print or page near the planned action. Its status as an original or an expendable copy is unclear and would change the preferred plan. | Does the robot use the earlier note to ask a specific question? Does the answer improve later choices? |
| **Learn an exception across sessions** | Bring the same person back. Give feedback that exposed originals need protection and laminated copies can be treated differently. Test both cases later in tasks the person has never corrected. | Does the robot retain what it learned, revise the scope, and avoid asking again when the answer is already known? |
| **Test a second preference family** | During tidying, the person restores a partially assembled project to its previous arrangement. Later ask the robot to clear space around a different unfinished project. | Can it infer and transfer a distinct principle about preserving work in progress? |

Use two scenarios for each proposed rule where possible. One should call for applying it, and the other should contain a plausible exception or irrelevant object. Include layouts where generic caution and the user's preference lead to different feasible choices. Ordinary good behavior can otherwise look like personalization.

## Comparisons

- **No previous interaction.** Give the same agent the same later scene and request without the earlier reaction. This controls for general knowledge about protecting belongings.
- **Routine review question.** After every task, the robot asks “How did I do?” and records the answer. Compare later execution and the user's time and effort against the approach that tries to interpret an intervention and asks selectively.
- **Retrieve and prompt.** Give a strong vision model the same observations, an ordinary memory of previous corrections, and the same question budget. Compare it with notes that capture a transferable principle and its scope.
- **Text diagnostic.** Replace the clip with a neutral, human-written account of visible events. In a separate condition, provide the intended preference explicitly. These help localize a failure to seeing the reaction, inferring its meaning, or applying the preference to a plan.
- **Fixed profile.** Use the notes learned during the first session as a static profile. Compare with the version that can revise its notes as further evidence arrives.

## Measures

Record task success, whether the person prefers the chosen execution, and whether the robot applied the preference in the right cases. On transfer trials, check its first plan before any new correction. Track questions and corrections per task, active user time spent teaching, unnecessary detours, and recovery after an exception. Written review outputs, applicable notes, and scores are sufficient for the proposed harness to log. The harness discards the visual input after review.

Start with short runs that isolate each stage. Then use several sessions with the same people, and use new tasks after each initial interaction and after later updates. Include more than one person before drawing a conclusion about individual alignment.
