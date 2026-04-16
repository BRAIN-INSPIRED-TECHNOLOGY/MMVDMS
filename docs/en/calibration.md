# Calibration Guide

This document describes the calibration workflow for `mvtriangulation`.

## 1. Overview
The project provides two calibration components under `src/mvtriangulation/calibration`:
- `intrinsics_zhang.py`: Zhang intrinsics calibration from chessboard images.
- `extrinsics.py`: robust extrinsics fitting from observation CSV.

Recommended order:
1. Calibrate intrinsics first.
2. Fit extrinsics using the calibrated intrinsics.
3. Use both parameter files in triangulation.

## 2. Intrinsics Calibration (Zhang)

Entry script:
- `examples/fit_intrinsics_zhang.py`

Command:
```bash
python examples/fit_intrinsics_zhang.py \
  --images "data/calib/*.jpg" \
  --board-cols 9 \
  --board-rows 6 \
  --square-size 0.025 \
  --out "data/camera_intrinsics.json"
```

Arguments:
- `--images`: chessboard image glob pattern.
- `--board-cols`: number of inner corners per row.
- `--board-rows`: number of inner corners per column.
- `--square-size`: physical square size (meters).
- `--out`: output intrinsics JSON path.
- `--disable-sb`: optional, force legacy corner detector.

Output JSON format:
```json
{
  "camera_matrix": [[fx, 0, cx], [0, fy, cy], [0, 0, 1]],
  "distortion_coefficients": [[k1, k2, p1, p2, k3]]
}
```

## 3. Extrinsics Fitting

Entry script:
- `examples/fit_extrinsics_robust.py`

Command:
```bash
python examples/fit_extrinsics_robust.py \
  --intrinsics "data/camera_intrinsics.json" \
  --fit-csv "data/obs_fit.csv" \
  --test-csv "data/obs_test.csv" \
  --out "data/camera_extrinsic_params.json" \
  --with-xyz-offset
```

Expected CSV columns:
- `u`, `v`
- `cam_lat`, `cam_lon`, `cam_alt`
- `kp_lat`, `kp_lon`, `kp_alt`
- `gimbal_yaw`, `gimbal_pitch`, `gimbal_roll`

Output JSON format:
```json
{
  "yaw_offset": -5.586365220297482,
  "pitch_offset": 0.5234572103265054,
  "roll_offset": -0.7682335373168965,
  "dX": 0.0,
  "dY": 0.0,
  "dZ": 0.0
}
```

## 4. Programmatic API

```python
from mvtriangulation.calibration import (
    ZhangIntrinsicsConfig,
    calibrate_from_image_pattern,
    ExtrinsicFitConfig,
    calibrate_and_save,
)

intr_cfg = ZhangIntrinsicsConfig(board_cols=9, board_rows=6, square_size=0.025)
calibrate_from_image_pattern(
    image_pattern="data/calib/*.jpg",
    config=intr_cfg,
    output_path="data/camera_intrinsics.json",
)

ext_cfg = ExtrinsicFitConfig(use_xyz_offset=True)
calibrate_and_save(
    intrinsics_path="data/camera_intrinsics.json",
    fit_csv="data/obs_fit.csv",
    test_csv="data/obs_test.csv",
    output_path="data/camera_extrinsic_params.json",
    config=ext_cfg,
)
```

## 5. Practical Notes
- Keep chessboard images diverse in orientation and image position.
- Reject blurry frames and low-contrast corners.
- Ensure all calibration images have the same resolution.
- For extrinsics fitting, use balanced samples across distance and view angles.
- Validate with a separate test set (`--test-csv`) before deployment.
