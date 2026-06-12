# StrideLab

Version: v0.1.0

[![Python](https://img.shields.io/badge/Python-3.12-3776AB.svg?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![Intel RealSense](https://img.shields.io/badge/PyRealsense-2.58+-0071C5.svg?style=flat&logo=intel&logoColor=white)](https://github.com/IntelRealSense/librealsense)
[![MediaPipe](https://img.shields.io/badge/Mediapipe-0.10.21-00C0FF.svg?style=flat&logo=google&logoColor=white)](https://mediapipe.dev/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.57.0-FF4B4B.svg?style=flat&logo=streamlit&logoColor=white)](https://streamlit.io/)
[![Plotly](https://img.shields.io/badge/Plotly-6.7.0-3F4F75.svg?style=flat&logo=plotly&logoColor=white)](https://plotly.com/)
[![License](https://img.shields.io/badge/License-Apache_2.0-blueviolet.svg?style=flat)](/LICENSE)

StrideLab is a gait capture-and-analysis pipeline for treadmill running research. A single Intel RealSense depth camera watches a person run on a treadmill from the side; MediaPipe BlazePose detects the body landmarks; the recorder writes them to disk; and the Workbench dashboard turns those recordings into biomechanical read-outs.

The whole pipeline lives in this one repository. It has two halves that share the same `core/` package:

| Stage | What it does | Entry points |
| --- | --- | --- |
| **Capture** | Drives the RealSense camera, runs pose estimation, deprojects landmarks to 3D, and serialises everything to a `.bin` file. | `recorder.py`, `calibrator.py`, `viewer.py` |
| **Analysis** (Workbench) | Loads a recording, cleans the signal, and computes gait and fatigue metrics in a Streamlit dashboard. | `workbench.py` |

A typical run is: **calibrate the camera → record a session → analyse it in Workbench.**

---

## The capture setup, and why it matters

The camera sits **perpendicular to the treadmill, looking at the runner from the side**. This is the classic 2D sagittal-plane viewpoint used in clinical gait labs that only have one camera. It has direct consequences for what the data can and cannot tell you:

- The camera's optical axis points at the runner's left–right (mediolateral) axis. In the recorded coordinates that axis is **Z, the depth axis**.
- What you see in the image — horizontal and vertical — is the runner's **anteroposterior** (forward/back) and **vertical** motion. In other words, **the image plane is the sagittal plane.**

The recorder stores two things for every landmark in every frame: the raw 2D pixel where MediaPipe found it (`px`, `py`), and a 3D world point in metres (`x`, `y`, `z`). The 3D point is produced by reading the depth at that pixel and back-projecting it through the RealSense lens intrinsics (`rs2_deproject_pixel_to_point`):

```
world_x = (px - cx) / fx * depth
world_y = (py - cy) / fy * depth
world_z = depth
```

The important detail hiding in that formula is that **all three world coordinates are multiplied by `depth`.** Depth from a single camera is noisy — it spikes when the sampling patch clips the background behind a limb, and it is fundamentally unreliable for the far-side leg, which is occluded by the near one. Because depth multiplies into X and Y as well, a bad depth reading throws the entire 3D point off. You can see this plainly if you rotate a reconstructed skeleton off-axis in the bundled `viewer.py`.

Workbench's response to this is deliberate and runs through the whole analysis engine:

1. **Metrics are computed from the raw pixels (`px`, `py`), not the 3D world coordinates.** Pixels are captured before any depth scaling, so they are immune to depth noise. For a side-on camera the pixel plane *is* the sagittal plane, which is exactly the plane the interesting motion lives in.
2. **The analysis focuses on the upper body** — trunk, head, shoulders, elbows — which sits close to the sagittal plane and tracks cleanly. Absolute lower-body joint angles (knee, hip, ankle) are intentionally **not** reported, because the side view cannot reconstruct them reliably.
3. **From the lower body, only depth-robust features survive** — specifically cadence, which comes from the *frequency* of the pelvis bobbing up and down. A frequency estimate barely cares about amplitude noise, so it stays trustworthy even when the absolute positions are jittery.
4. **Left/right symmetry is not reported.** From one side, the near limb occludes the far one and MediaPipe separates them partly using the unreliable depth, so per-side comparison from this rig won't be accurate enough.

If you ever feed Workbench a CSV that has no pixel columns (only world `x`, `y`), the engine falls back to using world `x`, `y` as the 2D coordinates — uniformly, so it never mixes the two coordinate spaces within a single calculation.

---

## Architecture

The repository keeps the processing maths separate from the interfaces, so both the capture core and the analysis engine can be tested and reused without their UIs in the way. Everything shared lives in `core/`.

### `core/` — capture modules

- **`core/camera.py`** — manages the Intel RealSense pipeline, frame alignment, and the on-chip hardware filters (decimation, disparity, spatial, temporal, hole-filling), plus laser power and exposure.
- **`core/pose.py`** — runs MediaPipe BlazePose and extracts the 2D landmark coordinates from each colour frame.
- **`core/depth.py`** — the 3D deprojection maths: sampling a robust depth at a pixel (`get_mean_depth`) and back-projecting it to a metric point (`deproject_pixel_to_point`).
- **`core/config.py`** — auto-generates and manages `settings.ini`, with standard path resolution that works both from source and from a frozen executable.

### `core/` — analysis modules

- **`core/workbench_logic.py`** — the math engine and the only file that knows how a recording is structured. It contains:
  - the landmark map and the `Joint` / `Frame` / `Session` data structures,
  - the binary and CSV readers (`read_bin`, `read_csv`, `load_recording`),
  - the DSP cleaning pipeline (`PipelineProcessor`),
  - the 2D kinematics (joint angles, trunk/head lean, torso scaling),
  - the per-frame metric builder (`compute_all_metrics`) and the summary statistics (`build_summary`),
  - the session-level derived metrics (`compute_cadence`, `compute_drift`),
  - and the time-windowing / baseline / fatigue functions (`build_time_mask`, `compute_baseline`, `compute_fatigue_curve`).
  It has no Streamlit dependency at all, which is why it can be exercised directly from a plain Python script.
- **`core/workbench_main.py`** — the Streamlit dashboard. It manages session state, draws the three workspaces (Data Quality, Gait Analysis, Fatigue Analysis), builds the Plotly figures, and wires the widgets to the engine. The heavy computation is wrapped in `@st.cache_data` so re-rendering on every widget change is cheap.

### Root applications

**Capture side:**

- **`recorder.py`** — the headless CLI for high-speed acquisition. It reads the camera and MediaPipe settings from `settings.ini`, opens the camera, and streams pose + depth to a `.bin` file, flushing each frame to disk so a recording survives an interrupt.
- **`calibrator.py`** — a DearPyGui tool for visually configuring the camera (preset, exposure, laser power, and every RealSense filter) with a live preview, then saving the result back to `settings.ini`.
- **`viewer.py`** — a DearPyGui playback tool for inspecting a captured `.bin`: scrub frames, play back at the recorded fps, and rotate the reconstructed 3D skeleton.

**Analysis side:**

- **`workbench.py`** — the desktop launcher for the dashboard. It builds the `streamlit run core/workbench_main.py` command line (headless, with the dashboard's theme colours baked in), starts the server, and opens the browser at `http://localhost:8501`. It also handles the frozen/`onedir` case, where the real code lives in a `libs/` subfolder next to the packaged executable, by fixing up `sys.path`, `PYTHONPATH`, and the working directory before launch.

---

## Recording formats

Workbench reads two formats, and both end up as the same in-memory DataFrame so the rest of the pipeline does not care which one you loaded. You can upload either through any of the three workspaces.

### Binary `.bin` (the native format)

This is what `recorder.py` writes. It is a flat, append-as-you-go binary stream:

| Section | Layout |
| --- | --- |
| Metadata length | `uint32` — number of bytes in the JSON block that follows |
| Metadata | UTF-8 JSON: capture date, full camera config (resolution, fps, exposure, laser power, preset, all the RealSense filter settings), and the MediaPipe settings (model complexity, confidence, target size) |
| Frame header | `double` timestamp (epoch seconds) + `uint32` joint count, repeated per frame |
| Joint record | `uint32` id, three `float`s (`x`, `y`, `z` in metres), two `int`s (`px`, `py` in pixels) — 24 bytes each, repeated per joint |

`read_bin` parses this into a DataFrame with a `timestamp` column and, for every landmark seen, `joint_N_x`, `joint_N_y`, `joint_N_z`, `joint_N_px`, `joint_N_py`. Only landmarks that had a valid depth reading are written for a given frame, so frames where a joint was lost simply omit it (it becomes `NaN` in the DataFrame).

### CSV

For data exported from other tools, or for re-loading something Workbench itself exported, `read_csv` accepts a CSV with a timestamp column plus joint columns in any of three naming conventions:

- `joint_25_x`, `joint_25_y`, `joint_25_z` (the binary recorder's convention),
- `j25_x`, … (compact),
- `left_knee_x`, … (named MediaPipe landmarks).

Pixel columns (`_px`, `_py`) are used if present; if the CSV only has world coordinates, those are used as the 2D source instead.

### Landmark naming

The 33 MediaPipe BlazePose landmarks are mapped to readable names (`nose`, `left_shoulder`, `right_hip`, `left_ankle`, …) in `POSE_LANDMARKS`, and every metric refers to joints by name rather than index.

---

## Capture workflow

The three capture tools all read and write the same `settings.ini`, which `core/config.py` creates with sensible defaults on first run.

### 1. Calibrate — `python calibrator.py`

Opens a live preview with controls for the camera preset, auto/manual exposure, laser power, and the RealSense filter chain (decimation, disparity, spatial, temporal, hole-filling). Tune until the depth and pose look clean, then save — the values are written back to `settings.ini` for the recorder to pick up.

### 2. Record — `python recorder.py`

A small CLI menu. Choose **Start Capture**, optionally name the output file (defaults to a timestamp) and set a duration (`0` for run-until-`Ctrl+C`). It loads the calibrated settings, opens the camera, and streams pose + depth to `recordings/<name>.bin`, logging progress as it goes.

### 3. Review — `python viewer.py`

Loads a `.bin` and lets you scrub and play back the captured skeleton, including rotating it in 3D — the quickest way to *see* the depth-noise problem described above before you take the recording into Workbench.

---

## The three workspaces (Workbench)

The dashboard opens on **Data Quality** and you move between the three areas with the selector at the top. They share a single loaded recording — upload once and all three see it. "Reset Workspace" clears the loaded data so you can start over.

### 1. Data Quality — clean the signal before you trust it

This is where you inspect a fresh recording and run the DSP pipeline. The cleaning steps are all in `PipelineProcessor` and you toggle them individually:

- **Validation** (`validate`) runs automatically on load. It counts zero values (tracking dropouts) and `NaN`s (gaps) across all joint channels and reports the percentages, so you immediately know how clean the recording is.

- **Teleport removal** (`remove_teleportation`) computes the per-frame Euclidean jump of each joint in 3D world space and nulls any frame where a joint moved further than the threshold (default 0.5 m) — the signature of a depth spike or a tracking error. Note that this acts on the *world* coordinates; a depth spike does not necessarily corrupt the pixel, so this step intentionally leaves the pixel signal alone.

- **Interpolation** (`repair`) replaces zeros and gaps with `NaN`, linearly interpolates across them (up to a 30-frame limit, ≈1 s at 30 fps), and fills anything still missing. It operates on the pixel channels as well as the world channels, so the signals the metrics are actually built from get repaired too.

- **Smoothing** (`smooth`) applies a centred rolling-mean filter with a configurable, odd-sized window to knock down high-frequency noise.

The "Inspect Node" plot overlays the raw and cleaned trace for any single joint channel so you can see exactly what the pipeline did. When you are happy with it, the cleaned data is what the other two workspaces use. You can export either the cleaned or the raw joint coordinates as CSV from here.

### 2. Gait Analysis — the kinematics

This is the main read-out. It computes every metric per frame, lets you view the time series at frame / per-second / per-minute resolution, toggle ±1σ envelopes and linear trend lines, and export the grouped data.

At the top it shows the **recording info** pulled from the metadata (date, duration, frame count, camera fps, resolution, preset, MediaPipe settings), then a row of **headline metric cards**, a **summary statistics table**, and the metric **plots**.

The headline cards are the single-value summaries for the whole recording:

- **Cadence** (steps/min) and **Step Frequency** (Hz) — see the metric reference below.
- **X-Drift Rate** (%torso/min) — how fast the runner is creeping forward or backward on the belt.
- **Vertical Oscillation** (%torso) — the peak-to-peak vertical travel of the pelvis.

The **Metrics Summary** table is `build_summary`: for every metric it gives the usual distribution stats (count/mean/std/min/quartiles/max) plus three extras computed at full frame resolution so they are not blurred by time-averaging — `rom` (range of motion = max − min), `peak_vel` (the largest frame-to-frame rate of change, in units per second), and `trend/min` (the linear slope over the session, fitted from per-second means). It exports to CSV.

The plots, in order: trunk and head lean together; shoulder swing (left/right) and elbow flexion (left/right) side by side; and the two pelvis-derived signals, vertical oscillation and X-drift. (The vertical-oscillation plot is most meaningful at the "Frames" grouping — at per-second/per-minute grouping the averaging flattens the bob out. The cadence number itself is always computed from full-resolution data and is unaffected by the grouping you choose.)

### 3. Fatigue Analysis — compare the session to an unfatigued baseline

This workspace answers the question the gait plots cannot: *how is the runner changing over time, relative to how they moved when they were fresh?* It is built around a treadmill protocol where the first minute or two is the person settling onto the belt, the next stretch is their steady unfatigued form, and everything after that is where fatigue may set in.

You drive it in two steps:

1. **Trim the session.** Two inputs — *Exclude warm-up (min)* (defaults to 2) and *Exclude cool-down (min)* — drop the adjustment period from the start and, optionally, a cool-down from the end.
2. **Pick the unfatigued baseline.** A range slider, bounded to the trimmed region, selects the window of steady running used as the reference. Everything after it is compared against it.

Under **Advanced options** you can change the comparison bin size (30 s / 1 min / 2 min), switch the deviation measure between z-score and % change, choose which metrics to track, and add arbitrary extra excluded regions (in minutes) to cut out mid-run glitches.

The maths behind it:

- `build_time_mask` marks every frame as included or excluded based on all the exclude regions.
- `compute_baseline` takes the mean and standard deviation of each metric over the baseline window (intersected with the included frames).
- `compute_fatigue_curve` bins the rest of the included session (per minute by default) and, for each bin and metric, reports the deviation from baseline three ways: the raw `delta`, the **% change** (`100 × delta / baseline_mean`), and the **z-score** (`delta / baseline_std`).

The z-score is the default because it is the more honest measure here: it expresses each change in units of that metric's own natural variability, and it does not blow up when a metric's baseline mean sits near zero (trunk lean near vertical, for instance). When a metric has no variability in the baseline window, its z-score is reported as blank rather than a divide-by-zero.

The output is a baseline reference table, a **deviation-over-time curve** (one line per metric, with the baseline window shaded green and the excluded regions shaded grey), and an **end-vs-baseline** summary comparing the final bin to the reference. The full fatigue curve exports to CSV.

---

## Metric reference

Every angle is measured in the 2D image (sagittal) plane from pixel coordinates. The image convention is +X to the right and +Y downward, so the upward direction is `-dy` and lean angles are `atan2(dx, -dy)`. Distance-type metrics are normalized by **torso length** — the median pixel distance between the shoulder midpoint and hip midpoint over the whole session — so values are comparable across people and across camera distances without needing metric depth.

| Metric (column) | What it is | How it's computed | Unit |
| --- | --- | --- | --- |
| `trunk_lean` | Forward/back trunk lean | Angle of the hip-midpoint → shoulder-midpoint segment from vertical | degrees |
| `head_lean` | Head/neck lean | Angle of the shoulder-midpoint → nose segment from vertical | degrees |
| `l_sho`, `r_sho` | Shoulder swing | Interior angle at the shoulder (hip–shoulder–elbow) | degrees |
| `l_elb`, `r_elb` | Elbow flexion | Interior angle at the elbow (shoulder–elbow–wrist) | degrees |
| `com_x` | Anteroposterior pelvis position | Hip-midpoint horizontal pixel ÷ torso length | torso lengths |
| `vert_osc` | Vertical pelvis position | Hip-midpoint vertical pixel ÷ torso length | torso lengths |
| Cadence / Step frequency | Stepping rate | FFT of `vert_osc`; the dominant frequency in the 0.5–4 Hz gait band is the step frequency (the pelvis rises and falls once per step), and cadence = 60 × that frequency | steps/min, Hz |
| X-drift | Belt creep | `com_x` low-passed over ~3 s to remove the per-stride wobble, then linearly fitted; reported as net change and rate | torso lengths, /min |

A couple of honest caveats on interpretation:

- The **sign of trunk and head lean** is positive toward image-right. Whether that corresponds to "forward" or "backward" depends on which way the runner faces in the frame, so read the direction against your own setup.
- **Shoulder and elbow** are reported per side, but from a single side view the near and far arms overlap; treat the two sides as two views of the same swing rather than an independent left/right comparison.

---

## Installation & Usage

### Setup

Use a virtual environment and install the pinned dependencies:

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

pip install -r requirements.txt
```

The capture side needs the Intel RealSense SDK (`pyrealsense2`), MediaPipe, OpenCV, and DearPyGui; the analysis side adds the scientific stack (NumPy, pandas, SciPy) and the dashboard (Streamlit, Plotly). A physical RealSense camera is only required for the capture tools — the Workbench dashboard runs on any machine that can read a `.bin` or `.csv`.

### Running the capture tools

```bash
python calibrator.py   # tune the camera, save settings.ini
python recorder.py      # record a session to recordings/*.bin
python viewer.py        # play back and inspect a recording
```

### Running the analysis dashboard

```bash
python workbench.py
```

This launches the Streamlit server and opens the dashboard in your browser at `http://localhost:8501`. Upload a `.bin` or `.csv` recording in any workspace to begin.

### Building standalone executables

Builds use PyInstaller in one-directory (`onedir`) mode, with all collected binaries and data moved into a `libs/` subfolder via `contents_directory='libs'` for faster startup and clean asset resolution. Run from the repository root:

**Windows** (x64, embedded icon, `asInvoker` manifest, distributed via an Inno Setup installer):

```bash
pyinstaller --clean tools/windows/build.spec
```

**Linux** (x64):

```bash
pyinstaller --clean tools/linux/build.spec
```

The build specs collect submodules for streamlit, pandas, numpy, scipy, sklearn, and plotly, and include Streamlit's package metadata, which it needs at runtime.

---

## Known limitations and design decisions

These are deliberate or known trade-offs, written down so they do not surprise you:

- **Depth is treated as untrustworthy on purpose.** Metrics are pixel-based for the reasons in the capture section above. The 3D world coordinates are still read, cleaned, and available, but the kinematics do not depend on them.
- **No lower-body joint angles and no left/right symmetry**, for the single-side-camera reasons above. Cadence is the one lower-body-derived metric, and it survives because it is a frequency.
- **Interpolation fills long gaps with zeros.** `repair` ends by filling anything still missing after interpolation with `0.0`. For tracking dropouts longer than its ~1 s interpolation limit, the affected frames become a `(0,0)` pixel and will produce meaningless metric values for that span rather than blanks. Keep an eye on the Data Quality report; very gappy recordings are flagged there.
- **The vertical-oscillation plot flattens at coarse time grouping** (the cadence number it informs does not — that is always computed at full resolution).
- **Teleport removal acts on world coordinates only**, so with the pixel-based metrics it currently has little effect on the numbers; pixel-domain jump cleaning is planned.

---

## Contribution & License

- **License**: distributed under the [Apache 2.0 License](/LICENSE).
- **Contributions**: pull requests are welcome. For major changes, please open an issue first. PRs containing unreviewed, generated AI content will be closed.
</content>
</invoke>
