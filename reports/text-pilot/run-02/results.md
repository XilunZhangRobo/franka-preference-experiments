# Text pilot 02

A fresh GPT‑6.2 Astra agent given only the robot's written preference notes matched the simulated person's choices on all 33 probes in each of two passes. Without user history, Astra matched 19 in the first pass and 21 in the second. A separate agent given the behavior descriptions also matched all 33 in each pass. In this suite, the short notes preserved the decision-relevant information in the descriptions. Both history conditions reached the same score.

## What each agent received

1. **Calibration.** A fresh Astra agent tried one original scene from each case family with no user history. It matched 7 of 10 private targets. The revision then introduced more discriminating conditions, such as a binder clip for paused work, right-to-left material staging, and an immediate completion update during solo work. The bedside lamp case remained as a ceiling and context check. [Calibration prompt and reply](transcripts/calibration.md).
2. **Simulated person.** The person Astra received ten private preferences and a separate negative control. It turned scripted actions into 21 camera-style captions. The captions describe such behavior as picking up a wedding print and swapping two blocks. The person agent supplied no spoken correction or statement of intent to the robot. [Private role prompts](transcripts/human.md) and [exact captions](inputs/observations.md).
3. **Audit.** A fresh Astra read only the captions. For each case, it answered “What happened?”, “Why might the person have done that?”, and “What could I use next time?” It wrote ten short preference notes and declined to update memory after the unrelated windowsill wipe. The coordinator copied the ten `Note:` paragraphs verbatim into the notes file. [Exact protocol](inputs/audit-protocol.md), [audit prompt and reply](transcripts/audit.md), and [written notes](inputs/notes.md).
4. **Decisions.** Three fresh Astra agents each chose between the same two feasible actions in 33 trials. The cold agent had no person history. The observation agent had the captions. The note-only agent had only the ten written notes as personal context. The revised choices and private grading key were locked before these decision agents answered. A second set of three fresh agents repeated the comparison with the cases interleaved and every A/B label swapped. A few clauses were adjusted to introduce the relevant noun before the reordered options. [Decision protocol](inputs/decision-protocol.md), [first-pass scenes and replies](transcripts/decisions-first.md), and [counterbalanced scenes and replies](transcripts/decisions-counterbalanced.md).

Each letter identifies a separate simulated person. Matching a trial's letter to memory was supplied by the coordinator. The agent had to decide whether the content applied in the current scene. The audit had no access to the decision probes. The decision agents had no access to the private brief or expected labels. The captions describe a scripted earlier action, which can differ from the choice the cold agent made on a later probe.

## Results

The two cold columns are independent responses. Both history conditions matched every target in both passes. Counterbalanced choices in [decisions.tsv](decisions.tsv) use the original A/B labels, so each row can be compared directly to the [grading key](grading-key.tsv).

| Case | What the decisions test | Cold first | Cold repeat | Observations or notes, each pass |
| --- | --- | ---: | ---: | ---: |
| P. Keepsakes | Keep a wedding print and an original family letter where they are, but move a laminated print | 3/3 | 3/3 | 3/3 |
| Q. Paused work | Treat a binder clip as a cue to preserve the layout, but shelve a completed kit | 2/3 | 2/3 | 3/3 |
| R. Creative finish | Stage personal gifts and displays, then leave the final choices to the person. Finish a routine return parcel | 2/3 | 2/3 | 3/3 |
| H. Receiving hand | Offer four different objects to the left if both hands are free, then follow an extended right hand in two occupied-left cases | 2/6 | 2/6 | 6/6 |
| O. Materials order | Stage items right-to-left in use order from the person's position. Center unordered group supplies | 1/3 | 1/3 | 3/3 |
| M. Approach | Approach from the person's left-front after the chair turns. Use the clear right side when the left is blocked | 1/3 | 2/3 | 3/3 |
| D. Daily essentials | Leave frequently used items visible at their point of use and store infrequent items | 3/3 | 3/3 | 3/3 |
| F. Completion updates | Give a short update during solo work and defer it during conversation | 1/3 | 1/3 | 3/3 |
| E. Lighting | Choose a bedside lamp for reading, a desk lamp for sketching alone, and overhead for a group | 3/3 | 3/3 | 3/3 |
| C. Food texture | Choose tender warm sides across vegetables and firm broccoli in a chilled salad | 1/3 | 2/3 | 3/3 |
| **All trials** | | **19/33** | **21/33** | **33/33** |

| Probe type | Cold first | Cold repeat | Observations first and repeat | Notes first and repeat |
| --- | ---: | ---: | ---: | ---: |
| Apply the preference, including near and cross-task transfers | 8/22 | 10/22 | 22/22 in each | 22/22 in each |
| Respect an exception | 11/11 | 11/11 | 11/11 in each | 11/11 in each |

### Handedness

Both fresh cold agents picked the recipient's right hand for the marker, screwdriver, lidded mug, and towel. The right-hand answer moved between A and B. Both agents described at least some of these choices as tie-breakers. This establishes a repeated default under this forced-choice setup. Each agent saw all four cases together, so the four choices within a pass are correlated. The earlier [handoff probe](../handoff-probe.md) found that when a centered offer was allowed, the cold agent preferred to wait for reach.

Both note-only agents picked left for all four objects when both hands were free, and right for both screwdriver and mug when the person was using the left hand and extending the right. The towel and screwdriver were absent from the captions. The mug and marker test nearer transfer, while the occupied-mug trial tests the exception on another object. The observation agents made the same choices.

### Lighting

The seed caption reports the person's actual intervention in the scripted scene. The person turns off the overhead light and switches on the bedside lamp while reading. A second caption shows a participant switching from a local lamp to overhead lighting during a group activity. All agents chose bedside for reading, desk for solo sketching in another setting, and overhead for a group in the living room. The note-only agents showed no blanket use of focused lamps in this test. The cold agents also chose correctly across all three scenes, so lighting offers no measured personalization gain in this suite.

The [matched lighting check](lighting-check/results.md) follows up on this ceiling. Two fresh agents received identical scenes and different notes derived from separate users' earlier actions. They chose opposite fixtures for both solo tasks and overhead for the group.

### Where the behavior changed

Both history conditions consistently fixed the shorter-route choice for the clipped mat, the decision to finish the gift box, all four no-cue handoffs, both material layouts, the shorter right-front delivery, both solo completion updates, and firm green beans as a warm side. Tender carrots and the chair-rotation transfer already came out correctly in one of the two cold runs. The constants across both passes are 12 probes on which the history conditions corrected the cold choice.

The keepsake audit remained conservative. The caption called the ordinary laminated print a laminated copy of the wedding print. The note names the wedding print and leaves material versus personal significance unresolved. A fresh note-only agent extended it to an original family letter in the first pass. Both cold agents also protected that letter. This shows the broader action is feasible, while the causal role of learning a principle about meaningful originals remains untested. The daily-essentials probes similarly supplied use-frequency cues that both cold agents could act on.

## What this establishes

- A fresh robot agent can use a short, agent-authored note in a later text interaction when earlier behavioral descriptions are absent. The matched cold decisions changed on seven of ten case families in both passes. The observations alone were equally effective here.
- All cold and history agents handled the exception choices correctly. This shows that the learned defaults did not override the explicit exceptions in these scenes. It leaves open whether the notes would rescue an exception the cold agent gets wrong.
- This is a behavioral-caption test with two short batches and synthetic people. Scenarios were revised after calibration to probe weaknesses, so the scores do not estimate the frequency of personalization errors in ordinary use. Some later scenes are near repeats, others introduce a different object, activity, or room. Each arm evaluated all trials in a single context. Reordering and swapping A/B help check sensitivity to presentation, but the same 33 probes were reused.
- This run isolates evidence interpretation and reuse of written memory. Intervention detection from video, retrieval without a case ID, selective clarification, memory revision over many sessions, and physical execution are open parts of the experiment.

A matched-user test for keepsakes could vary sentiment and physical protection independently while holding inconvenience constant. This would test whether the correct choice changes with who is present, as it did in the matched lighting check.
