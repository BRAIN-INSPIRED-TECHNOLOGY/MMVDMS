# Demo App User Guide

## 1. Start the app

```bash
pip install -r requirements.txt
python -m apps.flask_demo
```

Open `http://localhost:5000`.

## 2. Typical workflow
1. Import multiple images.
2. Annotate shared keypoints in each image.
3. Calibrate intrinsics/extrinsics, then configure camera parameters in app.
4. Trigger **Compute 3D** to obtain `_3d_position`.
5. Enter distance mode and select point pairs to measure 3D distance.
6. Export JSON/CSV/line-overlay image when needed.

## 3. Calibration before using app

### Intrinsics (Zhang)
```bash
python examples/fit_intrinsics_zhang.py \
  --images "data/calib/*.jpg" \
  --board-cols 9 \
  --board-rows 6 \
  --square-size 0.025 \
  --out "data/camera_intrinsics.json"
```

### Extrinsics
```bash
python examples/fit_extrinsics_robust.py \
  --intrinsics "data/camera_intrinsics.json" \
  --fit-csv "data/obs_fit.csv" \
  --test-csv "data/obs_test.csv" \
  --out "data/camera_extrinsic_params.json" \
  --with-xyz-offset
```

More details: [calibration.md](./calibration.md)

## 4. Camera parameter JSON format

### Intrinsics
```json
{
  "camera_matrix": [[fx, 0, cx], [0, fy, cy], [0, 0, 1]],
  "distortion_coefficients": [[k1, k2, p1, p2, k3]]
}
```

### Extrinsics
```json
{
  "yaw_offset": 0.0,
  "pitch_offset": 0.0,
  "roll_offset": 0.0,
  "dX": 0.0,
  "dY": 0.0,
  "dZ": 0.0
}
```

## 5. API endpoints
- `POST /api/images/upload`: upload image batch (`images` field).
- `GET /api/images/list`: list uploaded images.
- `GET /api/images/<image_id>/content`: image bytes.
- `GET /api/annotations/<image_id>`: get annotation points.
- `POST /api/annotations/<image_id>`: save annotation points.
- `POST /api/compute/3d`: compute 3D points.
- `GET /api/export/csv`: export CSV.
- `GET /api/annotations/<image_id>/export_json`: export JSON.

## 6. Current limitations
- Memory-only storage: restart clears uploaded images and labels.
- Reliable triangulation needs at least two valid observations per keypoint.
- Accuracy depends on calibration quality and baseline geometry.
