# 单目测距与多视角三角测量原理

## 1. 问题定义
本项目使用“单个相机在多视角下的 2D 关键点观测”恢复 3D 点坐标，并将结果统一到 ECEF 全局坐标系。

虽然每张图像都是单目观测，但通过融合多帧视角与相机姿态信息，可以恢复空间深度并实现测距。

## 2. 相机成像模型
对每个关键点 `(u, v)`：
1. 使用 `cv2.undistortPoints` 去畸变。
2. 构造归一化相机射线：

$$
\mathbf{d}_{cam} = \frac{[x_n,\ y_n,\ 1]^T}{\|[x_n,\ y_n,\ 1]^T\|}
$$

## 3. 姿态与坐标变换
实现中将以下信息融合为世界射线方向：
- 云台姿态 yaw/pitch/roll
- 用户外参偏置（`yaw_offset`, `pitch_offset`, `roll_offset`）
- 坐标链路：camera -> NED -> ECEF

世界射线方向：

$$
\mathbf{d}_i = R_{ecef\leftarrow ned}(lat,lon) \cdot R_{body\leftarrow ned}(yaw,pitch,roll) \cdot R_{cam\leftarrow ned} \cdot \mathbf{d}_{cam}
$$

射线起点（相机光心）在 ECEF 下表示为：

$$
\mathbf{O}_i = \text{ECEF}(lat_i, lon_i, alt_i) + [dX, dY, dZ]^T
$$

## 4. 三角测量最小二乘求解
每条观测对应一条空间直线：

$$
\mathbf{X} = \mathbf{O}_i + \lambda_i \mathbf{d}_i
$$

工程上采用“到多条射线正交距离最小”的线性最小二乘形式：

$$
(I - \mathbf{d}_i\mathbf{d}_i^T)\mathbf{X} = (I - \mathbf{d}_i\mathbf{d}_i^T)\mathbf{O}_i
$$

将多观测堆叠成：

$$
A\mathbf{X} = b
$$

使用 `numpy.linalg.lstsq` 求解 3D 点 `X`。

## 5. 测距计算
对于两个重建点 `X_a` 和 `X_b`：

$$
D = \|\mathbf{X}_a - \mathbf{X}_b\|_2
$$

即演示界面显示的三维欧氏距离。

## 6. 影响精度的关键因素
- 相机标定质量（内参、畸变参数）
- 姿态与位置信息质量（元数据 + 外参偏置）
- 视角基线几何（避免射线近平行）
- 标注精度（亚像素级更优）

## 7. 工程约束
- 每个关键点至少需要 2 条有效观测。
- 射线近似平行时，深度方向不稳定。
- 当前实现采用内存存储，不做持久化。
