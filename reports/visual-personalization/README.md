# Robot personalization in MuJoCo

Download and extract the [MuJoCo branch ZIP](https://github.com/XilunZhangRobo/franka-preference-experiments/archive/refs/heads/mujoco.zip), then open `reports/visual-personalization/index.html` in a browser. In a Git checkout you can open the same file directly. All scenario pages, images and videos work offline.

Use **Open trials at** to jump directly to the robot action, human response, written note, transfer, or scope control. Choose one of the ten experiments and a fresh-start, continuous, or contrasting-preference trial. The 24 trials contain 96 phase players. The supplementary pages include four mug-handoff clips and two tray clips.

## What the robot learned

Four opening actions already matched the original person’s assigned preference: paused work, material order, vegetable texture and private storage. The following results use a new task with the same person after that opening scene. Each condition used one model decision per scene.

| First transfer, ten isolated trials | Tasks |
| --- | --- |
| Correct with empty memory | Paused work, approach side, vegetable texture. The written note changed the vegetable choice to an incorrect one. |
| Written note changed a miss into a match | Gift finishing, receiving hand, completion updates, lighting, cleaning scent. |
| Correct with the continuing agent only | Material order. The continuing agent chose the right side and confirmed it with the person. |
| Missed by all three conditions | Private storage. The continuing agent in the separate ten-task sequence later resolved it by asking. |

After the continuous learner accumulated ten notes, fresh agents using the finished library scored **9/10** on new layouts of familiar tasks, compared with **2/10** without notes. On scope controls, these agents scored **9/10** and **10/10** respectively. The report distinguishes first-time transfer from this later retrieval test.

## Rebuild and verify

From the repository root:

```sh
python3 reports/visual-personalization/build_consolidated_report.py
python3 reports/visual-personalization/export_offline_report.py /tmp/robot-personalization.zip
python3 reports/visual-personalization/verify_portable_report.py /tmp/robot-personalization.zip
```

The verifier also accepts `--firefox` for a browser playback test with Firefox and geckodriver installed. The publication includes the source report builders, rendered assets, trial transcripts, note revisions, and decision evidence. The original verification records describe the research archive on the experiment host. Public copies use local relative paths and consistent aliases for model session identifiers. Model choices, films and task scores are preserved.

[Simulation protocol](../../docs/visual-interaction-study.md) · [Text pilot](../text-pilot/final-eval/results.md)
