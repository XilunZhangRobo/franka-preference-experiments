# Methodology

The harness interprets a person's reaction in the context of the robot's own execution. It turns the best supported interpretation into written context that can influence decisions on later tasks.

[Visual audit implementation](audit-implementation.md) specifies how the robot follows an intervention, checks the task outcome, and writes the review.

## 1. Detect an intervention and review the execution

The live camera watcher starts an observation when the person approaches the workspace or engages with a relevant object. It follows the intervention until the person disengages. The harness holds those frames in RAM and reviews them after the task outcome is checked. At review time, provide the original request, the interaction sequence, and the relevant executed motion from the temporary task record. An overhead view or an overlay of the mug path can help the model connect the object and motion. Manual start and end cues can isolate review quality before testing automatic boundary detection.

The review asks the same questions for every task.

1. **What happened?** Describe the robot's action, the person's response, and their timing. State what the camera actually shows.
2. **Why might Matt have done that?** Consider whether the response was related to the robot's action and what it suggests the person cared about.
3. **What could I use next time?** Propose a general principle and the circumstances in which it would change a choice.

An ordinary nearby action can lead to a review that finds no useful preference evidence. A single relevant intervention can support a tentative principle. For example, seeing Matt wipe the print after the mug crossed it supports protecting that print from moisture. Combined with the scene context, it suggests a broader concern for personal keepsakes. The note can preserve the distinction between those two inferences.

## 2. Write and revise context

The robot keeps short, editable text notes. Camera frames and video are processed for the review and discarded. The durable note may contain the observation in words, the inferred preference, its scope, any exceptions, and whether it was inferred or confirmed. It contains no saved video, still images, or video references.

| Field | Example |
|---|---|
| Observation | Matt picked up and wiped the wedding print immediately after the mug passed over it. |
| Inferred principle | Matt appears to prefer extra care around personal keepsakes that a robot action could damage. |
| When it applies | The planned action could spill onto, scrape, or crush something that appears personally important to Matt. |
| Scope and confidence | The strongest evidence concerns keeping the wedding print dry. Application to other keepsakes is a broader inference. |
| Exceptions | None established yet. |

Subsequent interactions can add a note, make an existing one more general, narrow its scope, or record an exception. If Matt later says that exposed originals need protection and laminated copies are fine, the rule and its retrieval conditions can both be updated. The written evidence helps distinguish a correction to an earlier inference from a genuinely changed preference.

## 3. Retrieve notes and choose a plan

At the start of a task, check relevant notes using the person, the scene, and the likely effects of the robot's actions. Check again if the plan changes or a relevant object appears. A note about protecting keepsakes can be relevant during a mug carry, cleanup, or plant watering. The applicability condition is about what might happen to the object in the current plan.

The skill file analogy helps organize this. Shared skills describe ways the robot can carry, place, or wipe. Personal context describes what this person values and when it affects the choice. The harness binds the remembered concern to the current scene and uses the available skills to choose a feasible action. During a mug carry that could mean going around the print. During cleanup it could mean setting a heavy object on a clear surface.

## 4. Ask selectively

Apply a well-supported preference directly in a clear case. If plausible interpretations would change a current or likely future decision, ask the smallest question that would resolve the ambiguity. For example, “Does the same preference apply to this print?” The answer may be spoken, typed, or shown in context. Record the answer or its meaning in text. The robot can also take an easy detour while leaving the broader scope tentative.
