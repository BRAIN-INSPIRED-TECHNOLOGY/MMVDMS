# Monocular Multi-View Distance Measurement System

<p align="center">
  <img src="./apps/flask_demo/app/static/img/logo.png" alt="Leinao" height="180" width="800"/>
</p>

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/)

[Chinese README](./README.md) | [English Docs Index](./docs/en/README.md)

`Monocular Multi-View Distance Measurement System (MMVDMS)` is an open-source implementation for UAV multi-view monocular distance estimation. It fuses repeated observations of the same target across multiple monocular images with RTK-level pose metadata embedded in original images, reconstructs 3D keypoints, and computes spatial distances.

The project is applicable to power-line inspection, PV station verification, slope and mining patrol, facade measurement, engineering surveying, and disaster assessment scenarios that require spatial measurement from raw drone imagery.

With the built-in **DJI Mavic 3E** sample set, the current validation result is: `25` samples, ground-truth range `2.00m~6.01m`, and overall accuracy **`MAE=0.084m`, `RMSE=0.126m`, mean relative error `2.120%`**. The project also provides lightweight APIs and a unified point format, making it easy to integrate manual annotations, keypoint detection models, VLMs/LLMs, or private business systems.

> **Prerequisite**: RTK must be enabled during flight, and original JPEG images must keep EXIF/XMP metadata. Meter-level GPS error will significantly degrade triangulation results.

![Demo App](./apps/flask_demo/app/static/img/img.jpg)

## 1. Capabilities
- Reconstruct 2D keypoints of the same target under multi-view observations into 3D ECEF coordinates.
- Provide a demo app covering import, annotation, triangulation, distance measurement, and export.
- Provide calibration tools (`src/mvtriangulation/calibration`) for Zhang intrinsics calibration and robust extrinsics fitting.
- Parse DJI JPEG XMP metadata and automatically extract lat/lon/alt, gimbal pose, and RTK-related fields.
- Provide unified JSON/CSV/API formats for easy integration with keypoint models or private systems.

## 2. Repository Structure

```text
.
├── apps/
│   └── flask_demo/                    # Flask demo application
├── docs/
│   ├── en/
│   └── zh/
├── examples/
│   ├── demo_csv/                      # Example point data
│   ├── demo_images/                   # Example raw images (with XMP metadata)
│   ├── minimal_usage.py               # Script example: raw images + point CSV -> triangulation + distances
│   ├── fit_intrinsics_zhang.py        # Zhang intrinsics calibration example
│   └── fit_extrinsics_robust.py       # Extrinsics fitting example
├── src/
│   └── mvtriangulation/
│       ├── calibration/
│       ├── parsers/
│       ├── pipeline.py
│       ├── transforms.py
│       └── triangulator.py
├── CONTRIBUTING.md
├── LICENSE
├── README.md
├── README-en.md
└── requirements.txt
```

## 3. Install Dependencies

**Environment:** Python >= 3.8

```bash
pip install -r requirements.txt
```

## 4. Quick Start

The following two entries are independent: the **Demo App** is for interactive operation, and the **Full Script Example** is for batch/script workflows.

### 4.1 Demo App
```bash
python -m apps.flask_demo
# Optional camera preset: M3E / M3T / others
python -m apps.flask_demo --camera-model M3T
```

Open in browser: `http://localhost:5000`

### 4.2 Full Script Example
```bash
python examples/minimal_usage.py \
  --points-csv examples/demo_csv/keypoints_observation2.csv \
  --image-dir examples/demo_images \
  --camera-model m3e \
  --pair 1-2
```

Notes:
- `--points-csv` only provides point coordinates, e.g. `image,keypoint_id,x,y`.
- `--image-dir` provides original images; the script automatically extracts fields like `lat/lon/alt/gimbal_pitch/gimbal_yaw/gimbal_roll/gps_status/rtk_flag` from XMP.
- The script merges point coordinates and image metadata, performs triangulation, and outputs each point `_3d_position` (ECEF) and point-to-point distances.
- Available camera options: `m3e` (default), `m3t`, `others`.

## 5. Practical Guide

### 5.1 Pre-Capture Checklist

Before data collection, verify the following:

- **Drone setup**: RTK must be enabled and fixed with high-precision status; otherwise ranging results are usually unreliable.
- **Gimbal/lens consistency**: Keep the same lens, resolution, and photo mode within one mission batch; avoid digital zoom, crop-mode changes, or channel switching.
- **Image fidelity**: Keep original JPEG files; avoid recompression, social-app forwarding, screenshots, or re-export that may remove XMP.
- **Target setup**: The same real-world target must be repeatedly observed across multiple images.
- **Validation setup**: If accuracy validation is required, prepare tape/rod/known-length targets or GCPs to record ground truth.
- **Environment setup**: Avoid strong reflections, severe occlusion, extreme backlight, and wind-induced blur.

### 5.2 Default Camera Presets

The project provides two ready-to-use default intrinsics presets for **visible wide channels**. When using defaults, ensure task images are from the corresponding model and channel.

| Model (Visible Wide) | Reference Resolution | fx | fy | cx | cy | distortion_coefficients |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| DJI Mavic 3E | 5280x3956 | 3660.0 | 3660.0 | 2640.0 | 1978.0 | [0, 0, 0, 0, 0] |
| DJI Mavic 3T | 8000x6000 | 5500.0 | 5500.0 | 4000.0 | 3000.0 | [0, 0, 0, 0, 0] |

Recommendations:

- These values are suitable as initialization/baseline parameters, not measured calibration outputs.
- If your resolution differs from the table, scale `fx/fy/cx/cy` proportionally by width/height.
- Mavic 3T defaults target visible wide channel only (not thermal or tele).
- For production or high-accuracy needs, calibration in Section 5.4 is still recommended.

### 5.3 Inspect XMP Metadata in Image Text

For DJI original JPEGs, you can open the image as text and search for `xmp`, `xmpmeta`, or `drone-dji:` to quickly verify RTK, pose, and calibration fields.

Suggested process:

1. Open a raw `.JPG` directly with VS Code, Notepad++, or another text editor.
2. Search for `xmpmeta` or `drone-dji:`.
3. Check RTK status, gimbal angles, calibrated focal length, optical center, and distortion-related fields.

In `examples/demo_images/DJI_20250812143439_0034_V.JPG`, you can find entries such as:

```xml
drone-dji:GpsStatus="RTK"
drone-dji:RtkFlag="50"
drone-dji:GimbalPitchDegree="+19.90"
drone-dji:DewarpData="2022-06-08;3713.290000000000,...,-0.027064110000"
drone-dji:CalibratedFocalLength="3725.151611"
drone-dji:CalibratedOpticalCenterX="2640.000000"
drone-dji:CalibratedOpticalCenterY="1978.000000"
```

Field meanings:

- `GpsStatus`, `RtkFlag`, `RtkStdLon/Lat/Hgt`: RTK status and solution quality.
- `GimbalPitchDegree`, `GimbalYawDegree`, `GimbalRollDegree`: gimbal attitude angles used directly in ranging.
- `CalibratedFocalLength`, `CalibratedOpticalCenterX/Y`: key intrinsics terms.
- `DewarpData`: distortion/dewarp parameters; may be lost after certain maintenance and can require re-calibration.

Current code extracts `lat/lon/alt/gimbal_pitch/gimbal_yaw/gimbal_roll/gps_status/rtk_flag` by default. For more XMP fields, extend `src/mvtriangulation/parsers/dji_xmp.py`.

### 5.4 Intrinsics/Extrinsics Calibration for Other Models

If you use a non-default model, or your channel/resolution/lens/mounting differs from preset assumptions, run full calibration.

Recommended flow:

1. **Intrinsics first**: use chessboard images at the same resolution as production images, covering different distances, poses, and frame regions.
2. **Extrinsics fitting**: fit mounting offsets using observation CSV with ground truth.
3. **Independent validation**: validate with unseen samples before production use.

Intrinsics calibration (Zhang):

```bash
python examples/fit_intrinsics_zhang.py \
  --images "data/calib/*.jpg" \
  --board-cols 9 \
  --board-rows 6 \
  --square-size 0.025 \
  --out "data/camera_intrinsics.json"
```

Extrinsics fitting (robust least squares):

```bash
python examples/fit_extrinsics_robust.py \
  --intrinsics "data/camera_intrinsics.json" \
  --fit-csv "data/obs_fit.csv" \
  --test-csv "data/obs_test.csv" \
  --out "data/camera_extrinsic_params.json" \
  --with-xyz-offset
```

Calibration tips:

- Chessboard images must use the same resolution as production imagery.
- Cover center/corners, near/far distances, and pitch variations.
- Extrinsics fitting samples should cover different baselines, distances, and shooting directions.
- For non-DJI models, besides calibration you also need a metadata parser or explicit pose fields in input tables.

Reference:

- [English calibration guide](./docs/en/calibration.md)

### 5.5 How to Capture Valid Multi-View Data

To make multi-view monocular ranging work, the same physical target must be observed in at least two images.

- **At least 2 views per target**: practical recommendation is `3~6` for better robustness and outlier rejection.
- **Create true baseline**: do not only rotate gimbal in place; move the drone laterally/diagonally to create camera-center displacement.
- **Consistent keypoint IDs**: the same physical corner/bolt/feature should use the same `keypoint_id` across images.
- **Baseline-distance relationship**: current sample setting uses baseline `0.5m~2m` and target range `3m~15m`; farther targets generally need larger effective baselines.
- **Ensure visibility**: avoid occlusion, severe crop, or blur on keypoints.
- **Control image quality**: reduce motion blur, over/under exposure, and high-ISO noise.
- **Keep original metadata**: use original files directly in pipeline; avoid screenshot/export/recompression workflows.

### 5.6 Data Preparation and Execution

#### 5.6.1 Using the Demo App

Recommended workflow:

1. Start the app and upload original images (must retain XMP metadata).
2. Annotate the same physical target across images using consistent `keypoint_id`.
3. Load default camera presets or upload calibrated intrinsics/extrinsics JSON.
4. Click **Compute 3D**; the system reads XMP and performs triangulation.
5. In distance mode, pick point pairs and export CSV/JSON/overlay as needed.

If keypoints come from a model instead of manual annotation, use existing APIs:

- `POST /api/annotations/<image_id>`: write keypoints
- `POST /api/compute/3d`: compute 3D
- `GET /api/export/csv`: export results

#### 5.6.2 Using Script Workflow

Recommended input organization:

1. Keep a raw image directory with XMP metadata.
2. Output keypoints via labeling tool JSON, VLM, or keypoint detector.
3. Normalize to required format or CSV with at least `image,keypoint_id,x,y`; `image` must map to original filenames/paths.
4. Run script with point CSV and image directory.
5. Script extracts metadata (`lat/lon/alt/gimbal_pitch/gimbal_yaw/gimbal_roll/gps_status/rtk_flag`) and merges with points for triangulation.

Recommended CSV format:

```csv
image,keypoint_id,x,y,true_length
DJI_20250812143439_0034_V.JPG,1,2627.11,1558.45,6
DJI_20250812143439_0034_V.JPG,2,2597.85,3372.28,6
```

Command example:

```bash
python examples/minimal_usage.py \
  --points-csv examples/demo_csv/keypoints_observation2.csv \
  --image-dir examples/demo_images \
  --camera-model m3e \
  --pair 1-2
```

## 6. Field Case

### 6.1 Capture Conditions

The repository provides a validated field sample set:

- Model: DJI Mavic 3E (visible wide)
- Data source: `examples/demo_images/` and `examples/demo_csv/keypoints_observation2.csv`
- Number of target objects: 4 observation points (README metrics correspond to full sample set)
- Current script example points: 2 observation points (ID 1~2)
- Sample count: 25
- Ground-truth range: `2.00m~6.01m`
- Task target distance range: `3m~15m`
- Task baseline range: `0.5m~2m`

### 6.2 Example Target Images

| ID_0 | ID_1 | ID_2 | ID_3 |
| --- | --- | --- | --- |
| <img src="./apps/flask_demo/app/static/img/ID_0.jpg" alt="ID_0" width="220" /> | <img src="./apps/flask_demo/app/static/img/ID_1.jpg" alt="ID_1" width="220" /> | <img src="./apps/flask_demo/app/static/img/ID_2.jpg" alt="ID_2" width="220" /> | <img src="./apps/flask_demo/app/static/img/ID_3.jpg" alt="ID_3" width="220" /> |

## 7. Metrics and Validation Results

### 7.1 Metric Definitions

Notation: $d_i^{gt}$ is ground-truth distance of sample $i$, $d_i^{pred}$ is predicted distance, and $N$ is sample count.

| Metric | Mathematical Definition | Description |
| --- | --- | --- |
| `AE` | $AE_i = \left\lvert d_i^{pred} - d_i^{gt} \right\rvert$ | Absolute error of one sample, unit: m. |
| `RE` | $RE_i = \frac{\left\lvert d_i^{pred} - d_i^{gt} \right\rvert}{d_i^{gt}} \times 100\%$ | Relative error of one sample, unit: %. |
| `MAE` | $\mathrm{MAE} = \frac{1}{N}\sum_{i=1}^{N} \left\lvert d_i^{pred} - d_i^{gt} \right\rvert$ | Mean absolute error across all samples. |
| `RMSE` | $\mathrm{RMSE} = \sqrt{\frac{1}{N}\sum_{i=1}^{N}\left(d_i^{pred} - d_i^{gt}\right)^2}$ | Root mean square error (more sensitive to outliers). |
| `Bias` | $\mathrm{Bias} = \frac{1}{N}\sum_{i=1}^{N}\left(d_i^{pred} - d_i^{gt}\right)$ | Mean signed error; positive means over-estimation. |

### 7.2 Overall Results

| Model | Sample Count N | MAE(m) | RMSE(m) | Mean RE(%) | Bias(m) |
| --- | ---: | ---: | ---: | ---: | ---: |
| DJI Mavic 3E | 25 | 0.084 | 0.126 | 2.120 | +0.052 |

Additional stats:

- Minimum `AE=0.0002m`
- Maximum `AE=0.363m`
- Minimum `RE=0.0058%`
- Maximum `RE=6.053%`

### 7.3 Per-Target Results

| Target ID | Sample Count N | MAE(m) | RMSE(m) | Mean RE(%) | Bias(m) |
| --- | ---: | ---: | ---: | ---: | ---: |
| 0 | 13 | 0.024 | 0.032 | 0.879 | -0.012 |
| 1 | 3 | 0.158 | 0.176 | 2.628 | +0.068 |
| 2 | 4 | 0.240 | 0.257 | 4.006 | +0.240 |
| 3 | 5 | 0.071 | 0.075 | 3.533 | +0.060 |

### 7.4 Sample Details

| No. | Target ID | Ground Truth (m) | Predicted (m) | RE(%) | Max Baseline (m) | Min Baseline (m) |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 0 | 2.75 | 2.725 | 0.918 | 2.674 | 2.108 |
| 2 | 0 | 2.75 | 2.744 | 0.210 | 7.358 | 1.983 |
| 3 | 0 | 2.75 | 2.711 | 1.424 | 3.027 | 1.370 |
| 4 | 0 | 2.75 | 2.716 | 1.242 | 2.995 | 2.150 |
| 5 | 0 | 2.75 | 2.738 | 0.431 | 3.230 | 2.066 |
| 6 | 0 | 2.75 | 2.759 | 0.313 | 2.848 | 2.615 |
| 7 | 0 | 2.75 | 2.815 | 2.355 | 9.904 | 2.672 |
| 8 | 0 | 2.75 | 2.753 | 0.107 | 7.051 | 0.450 |
| 9 | 0 | 2.75 | 2.734 | 0.570 | 6.118 | 4.906 |
| 10 | 0 | 2.75 | 2.708 | 1.525 | 5.195 | 4.102 |
| 11 | 0 | 2.75 | 2.690 | 2.181 | 5.941 | 2.291 |
| 12 | 0 | 2.75 | 2.746 | 0.137 | 3.920 | 3.289 |
| 13 | 0 | 2.75 | 2.750 | 0.006 | 2.149 | 1.355 |
| 14 | 1 | 6.01 | 6.085 | 1.240 | 3.925 | 2.592 |
| 15 | 1 | 6.01 | 6.274 | 4.387 | 6.108 | 4.182 |
| 16 | 1 | 6.01 | 5.874 | 2.256 | 0.254 | 0.136 |
| 17 | 2 | 6.00 | 6.363 | 6.053 | 5.244 | 3.529 |
| 18 | 2 | 6.00 | 6.283 | 4.722 | 4.982 | 3.570 |
| 19 | 2 | 6.00 | 6.193 | 3.210 | 4.344 | 3.710 |
| 20 | 2 | 6.00 | 6.122 | 2.037 | 4.220 | 3.647 |
| 21 | 3 | 2.00 | 2.063 | 3.134 | 3.385 | 0.487 |
| 22 | 3 | 2.00 | 2.072 | 3.584 | 3.594 | 0.053 |
| 23 | 3 | 2.00 | 1.973 | 1.346 | 3.777 | 2.325 |
| 24 | 3 | 2.00 | 2.107 | 5.372 | 2.999 | 0.734 |
| 25 | 3 | 2.00 | 2.085 | 4.231 | 4.060 | 1.134 |

## 8. Integration and References

### 8.1 Integrating Keypoint Detection Models

The core ranging pipeline is not bound to one point source. As long as keypoints are converted to the unified format, third-party models can be integrated.

Two recommended integration paths:

1. **Write keypoints via Demo App APIs**
2. **Run offline script with raw image directory + point CSV**

In Demo App, each image annotation payload is:

```json
{
  "points": [
    { "keypoint_id": 0, "x": 1234.5, "y": 987.6 },
    { "keypoint_id": 1, "x": 1420.2, "y": 1050.8 }
  ],
  "meta": {
    "source": "detector"
  }
}
```

APIs:

- `POST /api/annotations/<image_id>`: write keypoints
- `POST /api/compute/3d`: compute 3D
- `GET /api/export/csv`: export results

For script workflow, normalize to:

- `image`
- `keypoint_id`
- `x`
- `y`

The script extracts pose/RTK metadata from raw images and merges automatically.

### 8.2 Core API

Core package path: `src/mvtriangulation`

Triangulation:

- `mvtriangulation.CameraTriangulator`
- `mvtriangulation.triangulate_dataframe`
- `mvtriangulation.build_camera_arrays`

Calibration:

- `mvtriangulation.ZhangIntrinsicsConfig`
- `mvtriangulation.calibrate_intrinsics_zhang`
- `mvtriangulation.ExtrinsicFitConfig`
- `mvtriangulation.fit_extrinsics`

Metadata parsing:

- `mvtriangulation.extract_dji_metadata_from_jpeg_bytes`

### 8.3 Documentation Entries

- Architecture: [docs/en/architecture.md](./docs/en/architecture.md)
- Demo app guide: [docs/en/app-user-guide.md](./docs/en/app-user-guide.md)
- Calibration guide: [docs/en/calibration.md](./docs/en/calibration.md)
- Monocular distance principle: [docs/en/monocular-distance-principle.md](./docs/en/monocular-distance-principle.md)

## 9. Constraints

- **RTK is required**: the algorithm relies on centimeter-level position and attitude data; standard GPS (meter-level) makes triangulation unreliable.
- **Current default metadata parser supports DJI format**: pose data is extracted from DJI JPEG EXIF/XMP; other vendors require custom parser implementation.
- Demo app currently uses in-memory storage; data is cleared on restart.
- Each keypoint requires at least two valid observations.
- Distance accuracy is sensitive to calibration quality and baseline geometry.

## 10. About Us

Hefei Leinao Intelligent Technology Co., Ltd., founded in September 2017, is a national-level specialized and innovative "Little Giant" enterprise focusing on brain-inspired AI technology R&D and industrial implementation. Relying on major research platforms including the National Engineering Laboratory for Brain-Inspired Intelligence Technology and Applications, the company is currently the only commercialization entity for the lab's technology transfer results. With the mission of "promoting cutting-edge intelligent technologies into real industries and accelerating digital-intelligent upgrades," the company continuously advances deep integration of AI and the real economy.

Its core business covers computing power, electric power, and compute-electricity-carbon synergy. Main products include:

1. Brain-inspired heterogeneous computing systems for unified heterogeneous scheduling and AI task optimization.
2. Brain-inspired multimodal foundation models for power-grid equipment health diagnosis, distribution defect identification, and new-energy intelligent O&M, covering generation, transmission, transformation, distribution, and consumption links.
3. Compute-electricity-carbon collaborative intelligence systems for dynamic matching and optimized scheduling of computing and power resources, extended to VPP operations and AI-based electricity trading services.

Leinao has delivered key technical services to energy enterprises, universities, and research institutes, with over 1,000 landed projects. Its smart-energy solutions support substations, wind farms, and PV plants in 24 provinces across China for efficient operation and low-manpower/unmanned O&M. The Wanjiang AI Technology Industrial Park led by Leinao is actively promoting East-West collaboration and integration of computing infrastructure.

Leinao is committed to becoming a global leading energy-intelligence service enterprise and a global AI ecosystem builder.

Business: `business@leinao.ai`  
Media: `media@leinao.ai`  
Careers: `HR@leinao.ai`

## 11. License and Contributing

- License: see [LICENSE](./LICENSE)
- Contribution guide: see [CONTRIBUTING.md](./CONTRIBUTING.md)
