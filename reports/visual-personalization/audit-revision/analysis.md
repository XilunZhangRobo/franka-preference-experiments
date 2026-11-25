# Audit and clarification study

A default change to selective-v1 is inconclusive. The observed combination of question burden, written transfer and control scores, matched-fork decisions, and quiet-scene behavior does not establish a consistent advantage on this small sample.

[Locked plan](plan.json) · [Frozen selection](selection.json)

Question rates and correct counts use the full planned denominator. Missing results appear separately. An interrupted episode means the robot asked the person at least once. In a scene cell, the first arrow compares fresh decisions using draft and post-answer notes. The second follows the prospective robot from tentative to final action. ✓ marks a correct action and × a miss.

An audit answer affects both eligible probes. A prospective answer affects its own probe. A gain changes an incorrect choice to correct; a loss reverses it. Fresh note readers can differ through sampling. These comparisons cannot isolate a question’s causal effect.

## Development scenes

| Policy | Completed/planned | Missing results | Episodes interrupted | Audit questions | Prospective questions |
|---|---|---|---|---|---|
| legacy | 4/4 | 0 | 4/4 (100%) | 4/4 (100%) | 2/8 (25%) |
| selective-v1 | 4/4 | 0 | 0/4 (0%) | 0/4 (0%) | 0/8 (0%) |

| Policy | Probe | Draft correct | Post-answer correct | Tentative correct | Final correct |
|---|---|---|---|---|---|
| legacy | transfer | 0/4 | 1/4 | 2/4 | 3/4 |
| legacy | control | 4/4 | 4/4 | 4/4 | 4/4 |
| selective-v1 | transfer | 1/4 | 1/4 | 1/4 | 1/4 |
| selective-v1 | control | 4/4 | 4/4 | 4/4 | 4/4 |

| Policy | Answer stage | Affected probes | Changed choice / affected | Gains / affected | Losses / affected | Gains / planned | Losses / planned |
|---|---|---|---|---|---|---|---|
| legacy | audit | 8 | 1/8 (12%) | 1/8 (12%) | 0/8 (0%) | 1/8 (12%) | 0/8 (0%) |
| legacy | prospective | 2 | 1/2 (50%) | 1/2 (50%) | 0/2 (0%) | 1/8 (12%) | 0/8 (0%) |
| selective-v1 | audit | 0 | 0/0 (no opportunities) | 0/0 (no opportunities) | 0/0 (no opportunities) | 0/8 (0%) | 0/8 (0%) |
| selective-v1 | prospective | 0 | 0/0 (no opportunities) | 0/0 (no opportunities) | 0/0 (no opportunities) | 0/8 (0%) | 0/8 (0%) |

| Policy vs legacy | Probe | Decision | Paired scenes | Gains | Losses |
|---|---|---|---|---|---|
| selective-v1 | transfer | Written note | 4 | 1 | 1 |
| selective-v1 | transfer | Selective final | 4 | 0 | 2 |
| selective-v1 | control | Written note | 4 | 0 | 0 |
| selective-v1 | control | Selective final | 4 | 0 | 0 |

legacy exceeded the study’s soft one-in-five asking guide on completed opportunities (audit 4/4 (100%); prospective 2/8 (25%)).

| Policy | Scene | Audit | Transfer choices | Control choices | Evidence |
|---|---|---|---|---|---|
| legacy | gift-finishing | Asked | A × → A × / B ✓ → B ✓ (asked) | A ✓ → A ✓ / A ✓ → A ✓ | [Draft](dev/legacy/cases/gift-finishing/draft.md) · [Post-answer note](dev/legacy/cases/gift-finishing/post-answer.md) · [Calls](dev/legacy/cases/gift-finishing/transcript.json) · [Scores](dev/legacy/cases/gift-finishing/result.json) · [Inputs](dev/legacy/cases/gift-finishing/identity.json) |
| legacy | private-storage | Asked | B × → B × / B × → B × | B ✓ → B ✓ / B ✓ → B ✓ | [Draft](dev/legacy/cases/private-storage/draft.md) · [Post-answer note](dev/legacy/cases/private-storage/post-answer.md) · [Calls](dev/legacy/cases/private-storage/transcript.json) · [Scores](dev/legacy/cases/private-storage/result.json) · [Inputs](dev/legacy/cases/private-storage/identity.json) |
| legacy | cleaning-scent | Asked | B × → B × / B × → A ✓ (asked) | A ✓ → A ✓ / A ✓ → A ✓ | [Draft](dev/legacy/cases/cleaning-scent/draft.md) · [Post-answer note](dev/legacy/cases/cleaning-scent/post-answer.md) · [Calls](dev/legacy/cases/cleaning-scent/transcript.json) · [Scores](dev/legacy/cases/cleaning-scent/result.json) · [Inputs](dev/legacy/cases/cleaning-scent/identity.json) |
| legacy | lighting | Asked | B × → A ✓ / A ✓ → A ✓ | A ✓ → A ✓ / A ✓ → A ✓ | [Draft](dev/legacy/cases/lighting/draft.md) · [Post-answer note](dev/legacy/cases/lighting/post-answer.md) · [Calls](dev/legacy/cases/lighting/transcript.json) · [Scores](dev/legacy/cases/lighting/result.json) · [Inputs](dev/legacy/cases/lighting/identity.json) |
| selective-v1 | gift-finishing | Silent | A × → A × / A × → A × | A ✓ → A ✓ / A ✓ → A ✓ | [Draft](dev/selective-v1/cases/gift-finishing/draft.md) · [Post-answer note](dev/selective-v1/cases/gift-finishing/post-answer.md) · [Calls](dev/selective-v1/cases/gift-finishing/transcript.json) · [Scores](dev/selective-v1/cases/gift-finishing/result.json) · [Inputs](dev/selective-v1/cases/gift-finishing/identity.json) |
| selective-v1 | private-storage | Silent | B × → B × / B × → B × | B ✓ → B ✓ / B ✓ → B ✓ | [Draft](dev/selective-v1/cases/private-storage/draft.md) · [Post-answer note](dev/selective-v1/cases/private-storage/post-answer.md) · [Calls](dev/selective-v1/cases/private-storage/transcript.json) · [Scores](dev/selective-v1/cases/private-storage/result.json) · [Inputs](dev/selective-v1/cases/private-storage/identity.json) |
| selective-v1 | cleaning-scent | Silent | A ✓ → A ✓ / A ✓ → A ✓ | A ✓ → A ✓ / A ✓ → A ✓ | [Draft](dev/selective-v1/cases/cleaning-scent/draft.md) · [Post-answer note](dev/selective-v1/cases/cleaning-scent/post-answer.md) · [Calls](dev/selective-v1/cases/cleaning-scent/transcript.json) · [Scores](dev/selective-v1/cases/cleaning-scent/result.json) · [Inputs](dev/selective-v1/cases/cleaning-scent/identity.json) |
| selective-v1 | lighting | Silent | B × → B × / B × → B × | A ✓ → A ✓ / A ✓ → A ✓ | [Draft](dev/selective-v1/cases/lighting/draft.md) · [Post-answer note](dev/selective-v1/cases/lighting/post-answer.md) · [Calls](dev/selective-v1/cases/lighting/transcript.json) · [Scores](dev/selective-v1/cases/lighting/result.json) · [Inputs](dev/selective-v1/cases/lighting/identity.json) |

Archived original isolated episodes on these same families (4/4 available). The original learner retained its conversation. The fresh legacy replay above is the matched policy comparison.

| Archived original probe | Cold | Written note | Episode learner |
|---|---|---|---|
| transfer | 0/4 | 3/4 | 3/4 |
| control | 4/4 | 4/4 | 4/4 |

## Withheld original scenes

| Policy | Completed/planned | Missing results | Episodes interrupted | Audit questions | Prospective questions |
|---|---|---|---|---|---|
| legacy | 6/6 | 0 | 6/6 (100%) | 5/6 (83%) | 5/12 (42%) |
| selective-v1 | 6/6 | 0 | 2/6 (33%) | 1/6 (17%) | 2/12 (17%) |

| Policy | Probe | Draft correct | Post-answer correct | Tentative correct | Final correct |
|---|---|---|---|---|---|
| legacy | transfer | 4/6 | 5/6 | 5/6 | 6/6 |
| legacy | control | 6/6 | 6/6 | 6/6 | 6/6 |
| selective-v1 | transfer | 5/6 | 5/6 | 5/6 | 4/6 |
| selective-v1 | control | 6/6 | 6/6 | 6/6 | 6/6 |

| Policy | Answer stage | Affected probes | Changed choice / affected | Gains / affected | Losses / affected | Gains / planned | Losses / planned |
|---|---|---|---|---|---|---|---|
| legacy | audit | 10 | 1/10 (10%) | 1/10 (10%) | 0/10 (0%) | 1/12 (8%) | 0/12 (0%) |
| legacy | prospective | 5 | 1/5 (20%) | 1/5 (20%) | 0/5 (0%) | 1/12 (8%) | 0/12 (0%) |
| selective-v1 | audit | 2 | 0/2 (0%) | 0/2 (0%) | 0/2 (0%) | 0/12 (0%) | 0/12 (0%) |
| selective-v1 | prospective | 2 | 1/2 (50%) | 0/2 (0%) | 1/2 (50%) | 0/12 (0%) | 1/12 (8%) |

| Policy vs legacy | Probe | Decision | Paired scenes | Gains | Losses |
|---|---|---|---|---|---|
| selective-v1 | transfer | Written note | 6 | 1 | 1 |
| selective-v1 | transfer | Selective final | 6 | 0 | 2 |
| selective-v1 | control | Written note | 6 | 0 | 0 |
| selective-v1 | control | Selective final | 6 | 0 | 0 |

legacy exceeded the study’s soft one-in-five asking guide on completed opportunities (audit 5/6 (83%); prospective 5/12 (42%)).

| Policy | Scene | Audit | Transfer choices | Control choices | Evidence |
|---|---|---|---|---|---|
| legacy | paused-work | Asked | A ✓ → A ✓ / A ✓ → A ✓ | B ✓ → B ✓ / B ✓ → B ✓ (asked) | [Draft](holdout/legacy/cases/paused-work/draft.md) · [Post-answer note](holdout/legacy/cases/paused-work/post-answer.md) · [Calls](holdout/legacy/cases/paused-work/transcript.json) · [Scores](holdout/legacy/cases/paused-work/result.json) · [Inputs](holdout/legacy/cases/paused-work/identity.json) |
| legacy | approach-side | Asked | A ✓ → A ✓ / A ✓ → A ✓ (asked) | A ✓ → A ✓ / A ✓ → A ✓ | [Draft](holdout/legacy/cases/approach-side/draft.md) · [Post-answer note](holdout/legacy/cases/approach-side/post-answer.md) · [Calls](holdout/legacy/cases/approach-side/transcript.json) · [Scores](holdout/legacy/cases/approach-side/result.json) · [Inputs](holdout/legacy/cases/approach-side/identity.json) |
| legacy | completion-update | Asked | B × → A ✓ / A ✓ → A ✓ | B ✓ → B ✓ / B ✓ → B ✓ | [Draft](holdout/legacy/cases/completion-update/draft.md) · [Post-answer note](holdout/legacy/cases/completion-update/post-answer.md) · [Calls](holdout/legacy/cases/completion-update/transcript.json) · [Scores](holdout/legacy/cases/completion-update/result.json) · [Inputs](holdout/legacy/cases/completion-update/identity.json) |
| legacy | vegetable-texture | Asked | B ✓ → B ✓ / B ✓ → B ✓ (asked) | A ✓ → A ✓ / A ✓ → A ✓ (asked) | [Draft](holdout/legacy/cases/vegetable-texture/draft.md) · [Post-answer note](holdout/legacy/cases/vegetable-texture/post-answer.md) · [Calls](holdout/legacy/cases/vegetable-texture/transcript.json) · [Scores](holdout/legacy/cases/vegetable-texture/result.json) · [Inputs](holdout/legacy/cases/vegetable-texture/identity.json) |
| legacy | receiving-hand | Asked | A ✓ → A ✓ / A ✓ → A ✓ | A ✓ → A ✓ / A ✓ → A ✓ | [Draft](holdout/legacy/cases/receiving-hand/draft.md) · [Post-answer note](holdout/legacy/cases/receiving-hand/post-answer.md) · [Calls](holdout/legacy/cases/receiving-hand/transcript.json) · [Scores](holdout/legacy/cases/receiving-hand/result.json) · [Inputs](holdout/legacy/cases/receiving-hand/identity.json) |
| legacy | material-order | Silent | B × → B × / B × → A ✓ (asked) | A ✓ → A ✓ / A ✓ → A ✓ | [Draft](holdout/legacy/cases/material-order/draft.md) · [Post-answer note](holdout/legacy/cases/material-order/post-answer.md) · [Calls](holdout/legacy/cases/material-order/transcript.json) · [Scores](holdout/legacy/cases/material-order/result.json) · [Inputs](holdout/legacy/cases/material-order/identity.json) |
| selective-v1 | paused-work | Asked | A ✓ → A ✓ / A ✓ → B × (asked) | B ✓ → B ✓ / B ✓ → B ✓ | [Draft](holdout/selective-v1/cases/paused-work/draft.md) · [Post-answer note](holdout/selective-v1/cases/paused-work/post-answer.md) · [Calls](holdout/selective-v1/cases/paused-work/transcript.json) · [Scores](holdout/selective-v1/cases/paused-work/result.json) · [Inputs](holdout/selective-v1/cases/paused-work/identity.json) |
| selective-v1 | approach-side | Silent | A ✓ → A ✓ / A ✓ → A ✓ | A ✓ → A ✓ / A ✓ → A ✓ | [Draft](holdout/selective-v1/cases/approach-side/draft.md) · [Post-answer note](holdout/selective-v1/cases/approach-side/post-answer.md) · [Calls](holdout/selective-v1/cases/approach-side/transcript.json) · [Scores](holdout/selective-v1/cases/approach-side/result.json) · [Inputs](holdout/selective-v1/cases/approach-side/identity.json) |
| selective-v1 | completion-update | Silent | B × → B × / B × → B × | B ✓ → B ✓ / B ✓ → B ✓ | [Draft](holdout/selective-v1/cases/completion-update/draft.md) · [Post-answer note](holdout/selective-v1/cases/completion-update/post-answer.md) · [Calls](holdout/selective-v1/cases/completion-update/transcript.json) · [Scores](holdout/selective-v1/cases/completion-update/result.json) · [Inputs](holdout/selective-v1/cases/completion-update/identity.json) |
| selective-v1 | vegetable-texture | Silent | B ✓ → B ✓ / B ✓ → B ✓ (asked) | A ✓ → A ✓ / A ✓ → A ✓ | [Draft](holdout/selective-v1/cases/vegetable-texture/draft.md) · [Post-answer note](holdout/selective-v1/cases/vegetable-texture/post-answer.md) · [Calls](holdout/selective-v1/cases/vegetable-texture/transcript.json) · [Scores](holdout/selective-v1/cases/vegetable-texture/result.json) · [Inputs](holdout/selective-v1/cases/vegetable-texture/identity.json) |
| selective-v1 | receiving-hand | Silent | A ✓ → A ✓ / A ✓ → A ✓ | A ✓ → A ✓ / A ✓ → A ✓ | [Draft](holdout/selective-v1/cases/receiving-hand/draft.md) · [Post-answer note](holdout/selective-v1/cases/receiving-hand/post-answer.md) · [Calls](holdout/selective-v1/cases/receiving-hand/transcript.json) · [Scores](holdout/selective-v1/cases/receiving-hand/result.json) · [Inputs](holdout/selective-v1/cases/receiving-hand/identity.json) |
| selective-v1 | material-order | Silent | A ✓ → A ✓ / A ✓ → A ✓ | A ✓ → A ✓ / A ✓ → A ✓ | [Draft](holdout/selective-v1/cases/material-order/draft.md) · [Post-answer note](holdout/selective-v1/cases/material-order/post-answer.md) · [Calls](holdout/selective-v1/cases/material-order/transcript.json) · [Scores](holdout/selective-v1/cases/material-order/result.json) · [Inputs](holdout/selective-v1/cases/material-order/identity.json) |

Archived original isolated episodes on these same families (6/6 available). The original learner retained its conversation. The fresh legacy replay above is the matched policy comparison.

| Archived original probe | Cold | Written note | Episode learner |
|---|---|---|---|
| transfer | 3/6 | 4/6 | 6/6 |
| control | 6/6 | 6/6 | 6/6 |

## Matched ambiguity on the new tray task

Color and location are two private preferences for one visible teaching history. They share one visual draft per policy. A tentative probe decision can also be shared when its input is identical. Profile counts below are paired branches.

| Policy | Completed/planned | Missing results | Episodes interrupted | Audit questions | Prospective questions |
|---|---|---|---|---|---|
| legacy | 2/2 | 0 | 2/2 (100%) | 2/2 (100%) | 0/4 (0%) |
| selective-v1 | 2/2 | 0 | 0/2 (0%) | 0/2 (0%) | 0/4 (0%) |

| Policy | Probe | Draft correct | Post-answer correct | Tentative correct | Final correct |
|---|---|---|---|---|---|
| legacy | transfer | 1/2 | 2/2 | 2/2 | 2/2 |
| legacy | control | 2/2 | 2/2 | 2/2 | 2/2 |
| selective-v1 | transfer | 1/2 | 1/2 | 1/2 | 1/2 |
| selective-v1 | control | 2/2 | 2/2 | 2/2 | 2/2 |

| Policy | Answer stage | Affected probes | Changed choice / affected | Gains / affected | Losses / affected | Gains / planned | Losses / planned |
|---|---|---|---|---|---|---|---|
| legacy | audit | 4 | 1/4 (25%) | 1/4 (25%) | 0/4 (0%) | 1/4 (25%) | 0/4 (0%) |
| legacy | prospective | 0 | 0/0 (no opportunities) | 0/0 (no opportunities) | 0/0 (no opportunities) | 0/4 (0%) | 0/4 (0%) |
| selective-v1 | audit | 0 | 0/0 (no opportunities) | 0/0 (no opportunities) | 0/0 (no opportunities) | 0/4 (0%) | 0/4 (0%) |
| selective-v1 | prospective | 0 | 0/0 (no opportunities) | 0/0 (no opportunities) | 0/0 (no opportunities) | 0/4 (0%) | 0/4 (0%) |

| Policy vs legacy | Probe | Decision | Paired scenes | Gains | Losses |
|---|---|---|---|---|---|
| selective-v1 | transfer | Written note | 2 | 0 | 1 |
| selective-v1 | transfer | Selective final | 2 | 0 | 1 |
| selective-v1 | control | Written note | 2 | 0 | 0 |
| selective-v1 | control | Selective final | 2 | 0 | 0 |

selective-v1 reached the color fork without asking at audit or decision; its final choice was correct.

selective-v1 reached the location fork without asking at audit or decision; its final choice was incorrect.

| Policy | Scene | Audit | Transfer choices | Control choices | Evidence |
|---|---|---|---|---|---|
| legacy | color | Asked | A ✓ → A ✓ / A ✓ → A ✓ | B ✓ → B ✓ / B ✓ → B ✓ | [Draft](challenge/legacy/cases/color/draft.md) · [Post-answer note](challenge/legacy/cases/color/post-answer.md) · [Calls](challenge/legacy/cases/color/transcript.json) · [Scores](challenge/legacy/cases/color/result.json) · [Inputs](challenge/legacy/cases/color/identity.json) |
| legacy | location | Asked | A × → B ✓ / B ✓ → B ✓ | B ✓ → B ✓ / B ✓ → B ✓ | [Draft](challenge/legacy/cases/location/draft.md) · [Post-answer note](challenge/legacy/cases/location/post-answer.md) · [Calls](challenge/legacy/cases/location/transcript.json) · [Scores](challenge/legacy/cases/location/result.json) · [Inputs](challenge/legacy/cases/location/identity.json) |
| selective-v1 | color | Silent | A ✓ → A ✓ / A ✓ → A ✓ | B ✓ → B ✓ / B ✓ → B ✓ | [Draft](challenge/selective-v1/cases/color/draft.md) · [Post-answer note](challenge/selective-v1/cases/color/post-answer.md) · [Calls](challenge/selective-v1/cases/color/transcript.json) · [Scores](challenge/selective-v1/cases/color/result.json) · [Inputs](challenge/selective-v1/cases/color/identity.json) |
| selective-v1 | location | Silent | A × → A × / A × → A × | B ✓ → B ✓ / B ✓ → B ✓ | [Draft](challenge/selective-v1/cases/location/draft.md) · [Post-answer note](challenge/selective-v1/cases/location/post-answer.md) · [Calls](challenge/selective-v1/cases/location/transcript.json) · [Scores](challenge/selective-v1/cases/location/result.json) · [Inputs](challenge/selective-v1/cases/location/identity.json) |

## Robot-only negative control

This robot-only rehearsal offers one audit opportunity per policy and no probes.

| Policy | Completed/planned | Missing results | Episodes interrupted | Audit questions | Prospective questions |
|---|---|---|---|---|---|
| legacy | 1/1 | 0 | 1/1 (100%) | 1/1 (100%) | 0/0 (no opportunities) |
| selective-v1 | 1/1 | 0 | 0/1 (0%) | 0/1 (0%) | 0/0 (no opportunities) |

legacy wrote a spurious preference note on the quiet case (draft empty, final present).

selective-v1 wrote a spurious preference note on the quiet case (draft present, final present).

| Policy | Scene | Audit | Transfer choices | Control choices | Evidence |
|---|---|---|---|---|---|
| legacy | silence | Asked | — | — | [Draft](challenge/legacy/cases/silence/draft.md) · [Post-answer note](challenge/legacy/cases/silence/post-answer.md) · [Calls](challenge/legacy/cases/silence/transcript.json) · [Scores](challenge/legacy/cases/silence/result.json) · [Inputs](challenge/legacy/cases/silence/identity.json) |
| selective-v1 | silence | Silent | — | — | [Draft](challenge/selective-v1/cases/silence/draft.md) · [Post-answer note](challenge/selective-v1/cases/silence/post-answer.md) · [Calls](challenge/selective-v1/cases/silence/transcript.json) · [Scores](challenge/selective-v1/cases/silence/result.json) · [Inputs](challenge/selective-v1/cases/silence/identity.json) |

## Exact policy prompts

[legacy prompt file](policies/legacy.json)

[selective-v1 prompt file](policies/selective-v1.json)
