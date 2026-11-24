# Cycles recording and replay

`franka-prefs record` uses Blender Cycles to draw every recorded MuJoCo playback frame from the selected camera. The movie encoder and the learner’s JPEG sampler consume the same color-managed RGB frame. The shared simulation loop handles motion, task lights, observation timestamps, utterances and scoring. Each new Cycles bundle records the renderer version, sample count, device, color transform and source asset fingerprints under `examiner/`.

```bash
franka-prefs record paused-work --seed 0 --feedback retry --fps 12 --out runs/clean-agent
franka-prefs execute runs/clean-agent transfer A --out runs/clean-agent-transfer
```

The default is the full agent view at 960 × 720 and 64 samples per pixel using denoising. Use `--size 1920 1440` to double the linear resolution while keeping the same framing. CPU rendering works on Virgo. To use an accelerator with compatible Blender kernels and drivers, select a device with `--device`. Use `--renderer mujoco` for the fast OpenGL recorder. The interactive MuJoCo viewer also uses OpenGL. Cycles is an offline recording mode, and the MP4 plays at the specified simulation rate.

The paused-work example shows the robot moving a clipped project mat and the person returning it to the bench. The high-resolution still uses the same camera pose and field of view as the film. [Full interaction](media/workshop-cycles-agent.mp4) · [1920 × 1440 starting view](media/workshop-cycles-agent-2x.jpg) · [Transfer views for all ten task families](media/cycles-transfer-scenes.jpg)

For this seed, both renderers produced identical motion records and sample timestamps across all 94 teaching frames and both probe views. After video and JPEG compression, the 32 learner images differed from their corresponding Cycles movie frames by an average of 1.81 levels per 8-bit color channel. [Reproduction command, settings and measurements](prop-audit/cycles-recording.json)

When the active Python lacks `bpy`, the CLI uses `uv` to launch the project's isolated Blender runtime. First use can download dependencies. The character source is bundled with the package. Set up the usual Panda assets using `franka-prefs assets`. The `execute` CLI follows the source bundle's renderer and sample count, including older native bundles and converted Cycles packets. It accepts a device override when moving a Cycles bundle between machines.

## Inspect individual frames and replay existing runs

From the repository root, prepare the usual Panda assets using `franka-prefs assets` or set `FRANKA_PANDA_DIR` to the installed Menagerie Panda directory. The following command sets up an isolated Python environment for Blender 4.3.0 and renders teaching frame 96 at 18 fps.

```bash
uv run --no-project --python 3.11 --with bpy==4.3.0 --with 'numpy<2' \
  --with mujoco==4.0.1 --with pillow --with imageio-ffmpeg \
  python tools/render_cycles.py --family paused-work --phase teach --seed 0 \
  --feedback retry --fps 18 --frame 96 --camera agent --size 960 720 \
  --samples 40 --out runs/cycles
```

For a contiguous MP4 of the correction, use the same command with `--frame 80 --end-frame 116 --size 640 480 --samples 16 --out runs/cycles/correction`. Add `--verify-state runs/release/paused-work/examiner/teach.json` to verify the entire evaluated joint and mocap stream against the native recording before encoding the MP4. Endpoints are inclusive. Outputs include PNG frames and render.json with playback times, projection checks and settings. Use a fresh output directory for each sequence. CPU rendering is the default. A supported Cycles installation can use `--device OPTIX`, `CUDA`, `HIP`, `ONEAPI` or `METAL`.

Use the original run’s fps, seed, profile, feedback, dimensions, source revision and camera. The simulator applies the recorder’s layout-seed offset internally. Probe sensor packets contain a single initial view. Pass a probe’s internal `--choice` to render an executed action. On a teaching trial, the default action receives the configured feedback. For example, the supplied command reproduces the clock and task configuration of runs/paused-final/sensor/teach. A changed source scene or pose solver changes the replay. The scene XML digest can be compared with the examiner’s record on the same installation. The Blender camera currently supports the built-in ideal pinhole cameras. The direct recorder also supports the existing rectified calibration profile via the configured MuJoCo camera and shared pixel remap. The standalone replay and native-bundle converter use the built-in pinhole cameras.

## Geometry and appearance

- Panda surfaces use the compiled visual triangles, per-corner mesh normals, materials and MuJoCo world transforms. Collision proxies are hidden.
- Rocketbox body and face vertices come directly from MuJoCo’s evaluated skin buffer at each frame. For hair and eyelashes, Cycles uses the original alpha-textured cards from the packed Blender file with the same MuJoCo joint transforms and source skin weights. This preserves finer strands and lets light pass through the source alpha map.
- Furniture and props use their simulator dimensions and poses. Small edge bevels allow highlights on manufactured edges. The desk uses the same scanned diffuse texture with a Cycles box projection and a subtle bump derived from its brightness.
- Wide area emitters and a world fill give the skin, props and cabinet indirect illumination and contact shadows. These are rendering choices without measured room-light or material calibration.
- The camera uses the MuJoCo camera rotation directly, a vertical sensor fit, square pixels, and the original vertical field of view. The renderer projects geometry centers inside the camera frame with Blender and independently with the MuJoCo pinhole model, rejecting disagreement above 0.02 pixel.

Licenses and source details accompany the [Rocketbox human](../assets/human/README.md), [Panda acquisition code](../visual_prefs/assets.py) and [table material](../visual_prefs/data/materials/).

For an asset close-up, add `--detail-at-prop near` to a seed-0 teaching render at frame 0. This places an inspection camera at the starting mat. The diagnostic view is recorded in render.json and is available separately from the experiment's agent camera. Authored steel, plated wire and enamel carry their MuJoCo metallic and roughness values into the Cycles shader. [MuJoCo material attributes](https://mujoco.readthedocs.io/en/stable/XMLreference.html#asset-material)

## Convert an existing native recording

New Cycles recordings are already usable by the evaluator. For an existing native run, start with its completed recorder bundle. The converter takes its exact task, per-phase layout seeds, action choices, teaching feedback, option identifiers, and sample timestamps. For an existing Blender environment, run:

```bash
python tools/cycles_packet.py runs/release/paused-work \
  --out runs/release/paused-work-cycles --size 640 480 --samples 24
franka-prefs evaluate runs/release/paused-work-cycles \
  --adapter "$VLM_ADAPTER" --out runs/release/paused-work-cycles-evaluation
```

The first command requires the Blender Python dependencies shown above. The second uses the normal experiment environment and a trusted image-capable adapter command. Keep the original aspect ratio when overriding image dimensions. The converter rejects calibrated recordings until that camera model is supported in Cycles.

Every public packet keeps the source JSON byte for byte. All JPEGs, including the last listed sample and speech-timed samples, are rendered in Cycles. The evaluator reads these JPEGs directly. The packet converter produces no public video. A new private manifest records hashes of the actual learner-facing files. Private provenance records output size, sample count, renderer and source manifest digest. Conversion validates the source assets, scene XML, full playback event trace, joint and mocap states when the source provides a state digest, final prop positions, options and transcript. A discrepancy stops conversion before publication. The output path must be fresh.
