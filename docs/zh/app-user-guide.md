# 演示 App 使用说明

## 1. 启动应用

```bash
pip install -r requirements.txt
python -m apps.flask_demo
```

浏览器访问：`http://localhost:5000`

## 2. 典型使用流程
1. 批量导入图像。
2. 在多张图像上标注同一批关键点。
3. 先完成内参/外参标定，再在应用中配置参数。
4. 点击 **计算 3D**，生成 `_3d_position`。
5. 进入测距模式，选择点对计算空间距离。
6. 按需导出 JSON、CSV、连线叠加图。

## 3. 标定准备（建议先做）

### 内参标定（张正友法）
```bash
python examples/fit_intrinsics_zhang.py \
  --images "data/calib/*.jpg" \
  --board-cols 9 \
  --board-rows 6 \
  --square-size 0.025 \
  --out "data/camera_intrinsics.json"
```

### 外参拟合
```bash
python examples/fit_extrinsics_robust.py \
  --intrinsics "data/camera_intrinsics.json" \
  --fit-csv "data/obs_fit.csv" \
  --test-csv "data/obs_test.csv" \
  --out "data/camera_extrinsic_params.json" \
  --with-xyz-offset
```

详细说明见：[calibration.md](./calibration.md)

## 4. 相机参数 JSON 格式

### 内参（Intrinsics）
```json
{
  "camera_matrix": [[fx, 0, cx], [0, fy, cy], [0, 0, 1]],
  "distortion_coefficients": [[k1, k2, p1, p2, k3]]
}
```

### 外参（Extrinsics）
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

## 5. 主要 API
- `POST /api/images/upload`：批量上传（字段名 `images`）。
- `GET /api/images/list`：获取图像列表。
- `GET /api/images/<image_id>/content`：获取图像内容。
- `GET /api/annotations/<image_id>`：读取标注点。
- `POST /api/annotations/<image_id>`：保存标注点。
- `POST /api/compute/3d`：计算 3D 结果。
- `GET /api/export/csv`：导出 CSV。
- `GET /api/annotations/<image_id>/export_json`：导出 JSON。

## 6. 当前限制
- 当前为内存存储，重启后数据会清空。
- 每个关键点至少需要两条有效观测才能稳定三角测量。
- 测距精度受标定精度和视角基线几何影响显著。
