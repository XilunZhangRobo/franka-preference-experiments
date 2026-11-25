# Visual audit implementation

The first prototype uses an overhead camera, the Franka executor's task and motion events, and a vision-language model (VLM). The camera watches the live scene for an intervention. An approach or engagement starts an observation in RAM, and disengagement ends it. The audit runs once the interaction has ended and the task outcome has been checked. These are proposed interfaces.

## Runtime sequence

```text
start task and watch the live scene for an interaction cue
  -> person approaches or engages: begin an observation in RAM
  -> continue observing while the person is engaged
  -> person disengages: close the observation
  -> once the executor has ended and the goal has been checked, review it
  -> write or update a preference note when the evidence supports one
  -> release all frames and temporary motion data
```

1. **Watch the live scene.** Start a temporary task record with the request, expected outcome, and timestamped executor and motion events. For the mug task, define the start side and destination region. The watcher processes live frames to detect engagement cues. The task record supplies the earlier robot motion if the person reacts after the mug has already passed the print.
2. **Start observing at the cue.** Open an observation when the person approaches the active workspace or starts engaging with a relevant object. Retain frames from that cue onward in RAM. Approach is enough to start observing. The review can later determine that the activity was unrelated.
3. **Follow the intervention through disengagement.** Continue while the person is reaching, holding, wiping, repositioning, or otherwise engaged. Close the observation when the person releases the relevant object and withdraws, steps away, or clearly shifts to unrelated activity. A pause while the person still holds the print is part of the same interaction. For longer interactions, keep the onset and meaningful changes through the ending, and sample redundant frames more sparsely to bound memory use. If the view is lost, mark the observation incomplete. Separate interventions can produce separate observations.
4. **Check the outcome independently.** Once the executor reports that motion ended, check whether the request was satisfied. For the mug task, verify that the mug was released, is visible in the destination region, and has settled. Label the outcome successful, failed, or uncertain. If the person is still engaged when the executor ends, continue observing until disengagement. If they finish while the robot is still working, hold the completed observation in RAM until the task outcome is checked. A successful task can still have an audit.
5. **Review and persist only text.** Provide the VLM with the ordered intervention frames, the request, the task outcome, and the relevant earlier robot motion. For an overhead camera, an overlay of the mug's actual path can show its relation to the print in the first intervention frame. Write a preference note if the review finds relevant evidence. Release the frames and temporary motion data after the review. The harness does not create video or image files.

## Detecting a candidate intervention

Start with manually marked start and end cues. A keypress at each boundary supplies a timestamp, with no explanation of the behavior or preference. This checks whether the review can make sense of the interaction before measuring automatic boundary detection.

For the automatic version, recognize an approach or reach toward the active workspace as a start cue. Track hand-object engagement as the event develops. For example, the hand approaches the print, the print moves, and the hand makes wiping motions. Use withdrawal or a clear change in activity to identify the end. Relate the tracked object to the executed mug path so the system can notice a response to the robot passing overhead. The review determines whether the sequence supports an inference about the person.

Compare actual interventions with routine activity nearby. Log the observed start and end cues and their timestamps as text. On trials where the automatic detector misses or cuts off an event, compare its output with manually marked boundaries to distinguish detection errors from interpretation errors.

## The review output

| Question | Field in the written review | Wedding-photo example |
|---|---|---|
| **What happened?** | Observed sequence | The robot carried the mug over the wedding print. Matt picked up and wiped the print shortly afterward. |
| **Why might Matt have done that?** | Plausible explanation and uncertainty | He may have been trying to keep the print dry. The timing supports a relationship to the mug path. A spill is unverified if it is not visible. |
| **What could I use next time?** | Candidate preference and applicability | Matt appears to want extra care around personal keepsakes when an action could damage them. This concern could apply to liquid exposure or to placing something heavy on a keepsake. The evidence is strongest for the print and moisture. |

The model can return no preference update if the activity appears unrelated. When it finds a useful lesson, the harness creates or revises a short written note that separates observation, inference, scope, and any later confirmation. A decision about whether to ask the person comes after that review. The harness applies a well-supported preference directly in a clear case and asks when the answer would change a consequential choice or settle a recurring ambiguity.

## Reusing the result

On a later task, retrieve notes using the person, the current scene, and the likely effects of the plan. The retrieved note biases the choice among feasible actions. For example, it can favor carrying a drink around a keepsake or placing a tray on a clear surface while tidying. If the person gives more evidence later, update the note and its applicability conditions in text.

The first integration can use one camera, one fixed task, manual start and end cues, and a written note. Once the loop works end to end, automate both boundaries and test retrieval on a different task. [Evaluation scenarios](evaluation.md) describe the conditions that separate detection, interpretation, and transfer.
