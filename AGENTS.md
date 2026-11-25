# Working on preference experiments

Use [the experiment lifecycle](docs/experiment-lifecycle.md) when changing a scene, protocol, scorer, camera, or claim. Run exploratory seeds freely. Reserve the locked evaluation split for a recorded experiment.

- Keep simulator state, phase names, descriptive filenames, scorer keys, and expected actions outside model-visible inputs. Review the serialized model request.
- Preserve a reproduction command, asset and code revisions, and raw observations for each reported run. Document how a reviewer can make a faulty implementation fail its tests.
- Treat simulated motions and synthetic counterexamples as evidence about this simulator. Claims about physical behavior require paired measurements on the named hardware and task.
- On headless Linux export `MUJOCO_GL=egl` before running tests. Run `python -m unittest discover -s tests` after changing behavior. For scene changes, also inspect representative rendered teaching, transfer, and exception clips from the evaluation camera.
- For experiment reports, follow [Matt’s recording and navigation preferences](docs/experiment-lifecycle.md#how-matt-reviews-experiment-recordings).
