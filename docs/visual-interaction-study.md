# Two-agent visual preference study

A robot Astra chooses how to carry out a task from a Cycles camera image. A separate Astra plays the person, using a private preference and the camera sequence showing the chosen action. It selects a physical response. The simulator executes the response with the avatar. The robot then sees a time-ordered sample of the interaction and hears any simulated utterance. Its audit asks what happened, what the person might have meant, and what could carry over. Its visual-only draft and its note after any spoken clarification are saved separately.

The original profiles reproduce the ten qualifying text families. Three examples illustrate what counts as evidence.

| Task | Teaching interaction | New setting | Scope control |
| --- | --- | --- | --- |
| Paused work | Move a work mat. The person can put just that mat back. | Choose which fabric mat to move in a sewing room. | A closed kit can be shelved. |
| Receiving hand | Offer a flashlight. The person can receive it and switch hands. | Offer a remote. | One hand already holds an object. |
| Lighting | Choose a fixture for a solo puzzle. The person can switch fixtures. | Choose lighting for comparing tile patterns. | A group needs local light during a projected slide show. |

## Experimental conditions

1. **Isolated original.** Each family starts with a fresh robot and person. They continue their own conversation through teaching, transfer and the scope control. Every family is retained, including initial agreement or ambiguous feedback.
2. **Diagnostic contrast.** When a robot already agrees with the original person, a separate fresh episode illustrates correction. Two opposite profiles are defined in the simulator before the study. The examiner picks the profile that disagrees with this new robot’s observed first choice. This condition can demonstrate recovery from an error. Its initial error rate is determined by selection.
3. **Continuous original.** After the isolated runs, one robot thread and one person thread continue through all ten original families. The robot receives the written library accumulated so far. Each episode saves its starting library, final note, and inventory after the interaction. Closure of a previous episode supplies no answer key to the agents.
4. **Library retention.** On new layout seeds, a fresh reader sees note titles and chooses up to three. A fresh decision maker receives those full notes. Its paired cold counterpart receives the same image and actions with empty memory. Both choose before any clarification.

Every teaching task offers two physically implemented robot actions. The person chooses between two enacted responses. The examiner keeps the private profile, motion command and answer keys away from the robot. A person can answer a follow-up question in natural language. The archived images are the exact model observations. The continuous videos let a reviewer inspect motion between samples.

At each transfer and control, two additional fresh robot calls compare the same initial frame with empty memory or just the written note. The continuing learner can independently ask the person and execute its own decision. These measurements distinguish written transfer from a choice backed by conversation history and further clarification.

The supplementary mug handoff uses the isolated receiving-hand note on a lidded tumbler. It pairs two free hands with the same scene when the left hand holds folded paper. Each condition has a fresh cold reader and a fresh note-assisted reader. Both decisions are enacted on camera.

## Reproduce a run

Use the activated environment, installed Panda assets, and an authenticated Codex CLI with access to GPT-6.2 Astra. Rendering uses the project's Blender runtime. From the repository root on a machine with EGL, run the following commands with a new destination.

```bash
export MUJOCO_GL=egl OPENBLAS_NUM_THREADS=1
python -m visual_prefs.interaction_study runs/interaction-study --workers 4
python tools/interaction_analysis.py runs/interaction-study --visual-only
python tools/verify_interactions.py runs/interaction-study --videos
```

The run's `index.html` contains annotated videos, exact transcripts, camera observations and results. `library/` contains the continuing robot's actual Markdown notes. `retention/index.html` lists retrievals and paired decisions. `analysis.md` compares task families and identifies cases where a clarification changed the draft. The grader works from separate examiner records. A matched choice on an easy scope control can come from ordinary robot behavior. Results apply to this simulation, camera, person brief, and discrete action menu.

## Follow-up hypotheses

The note-writing backlog includes a proposed test of how a person’s opportunity to intervene affects the interpretation of an uneventful task. [Research note](personalization-research-notes.md)
