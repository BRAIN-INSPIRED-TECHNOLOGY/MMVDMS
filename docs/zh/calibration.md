# 标定说明

本文说明 `mvtriangulation` 的标定流程。

## 1. 总览
项目在 `src/mvtriangulation/calibration` 下提供两类标定能力：
- `intrinsics_zhang.py`：基于棋盘格图像的张正友内参标定。
- `extrinsics.py`：基于观测 CSV 的鲁棒外参拟合。

推荐顺序：
1. 先完成内参标定。
2. 再基于内参拟合外参。
3. 将两份参数文件用于三角测量。

## 2. 内参标定（张正友法）

入口脚本：
- `examples/fit_intrinsics_zhang.py`

命令：
```bash
python examples/fit_intrinsics_zhang.py \
  --images "data/calib/*.jpg" \
  --board-cols 9 \
  --board-rows 6 \
  --square-size 0.025 \
  --out "data/camera_intrinsics.json"
```

参数说明：
- `--images`：棋盘格图像通配路径。
- `--board-cols`：每行内角点数。
- `--board-rows`：每列内角点数。
- `--square-size`：棋盘格单元实际尺寸（米）。
- `--out`：内参 JSON 输出路径。
- `--disable-sb`：可选，禁用 `findChessboardCornersSB`，使用传统角点检测。

输出 JSON 格式：
```json
{
  "camera_matrix": [[fx, 0, cx], [0, fy, cy], [0, 0, 1]],
  "distortion_coefficients": [[k1, k2, p1, p2, k3]]
}
```

## 3. 外参拟合

入口脚本：
- `examples/fit_extrinsics_robust.py`

命令：
```bash
python examples/fit_extrinsics_robust.py \
  --intrinsics "data/camera_intrinsics.json" \
  --fit-csv "data/obs_fit.csv" \
  --test-csv "data/obs_test.csv" \
  --out "data/camera_extrinsic_params.json" \
  --with-xyz-offset
```

CSV 必需字段：
- `u`, `v`
- `cam_lat`, `cam_lon`, `cam_alt`
- `kp_lat`, `kp_lon`, `kp_alt`
- `gimbal_yaw`, `gimbal_pitch`, `gimbal_roll`

输出 JSON 格式：
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

## 4. 代码调用方式

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

## 5. 工程建议
- 棋盘格图像需要有足够的姿态和位置变化。
- 剔除模糊、过曝、角点不清晰的图像。
- 标定图片分辨率必须一致。
- 外参拟合样本应覆盖不同距离和不同视角。
- 上线前建议使用独立测试集（`--test-csv`）验证。
