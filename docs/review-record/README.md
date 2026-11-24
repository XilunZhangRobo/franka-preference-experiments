# Blinded development review

The five decision calls and one observation call used fresh GPT-6.2-Astra agents. The observer could read one teaching packet and examine its images. Each decision reader saw only the designated probe packet(s), plus the literal memory in its instruction if assigned one. The operating environment was shared and access restrictions were given by instruction. The shipped model-adapter protocol separately passes only image bytes and approved text.

`rgb.zip` contains sensor-only evidence exactly as staged under the neutral IDs p, q, r and z. p is the teaching interaction, q and r are the first transfer and scope probes, and z is the color/letter conflict probe. The first observer was given an overview made from uniformly sampled frames, plus access to the individual images. `transcripts.json` preserves the prompts and replies. `sha256.json` identifies each archived input. These files archive the development run before the later forearm clearance repair. [Interpretation and scoring](../development-audit.md)

`cycles-sensors.zip` contains the complete sensor and examiner bundle from the later Cycles evaluation. Extract it into a new directory. The archived results in `cycles-evaluation/` bind to its sensor and run digests. The original local Codex transport was subsequently packaged as `franka-prefs-codex`. Its six calls cover detection, audit and the two paired decisions.

`feedback-controls.json` records the separate four-condition experiment, including the plan, run fingerprints, per-call image hashes, raw replies, notes, and paired scorecard. Full original media for that run are also available in the generating checkout under `runs/release/feedback-check/` and `runs/release/feedback-controls-complete.zip`.
