# Monocular Distance Principle and Multi-view Triangulation

## 1. Problem statement
This project estimates 3D point coordinates from 2D keypoints observed by a single camera across multiple views (different poses). The final coordinates are represented in the global ECEF frame.

Although each image is monocular, distance is recovered by combining multiple monocular observations with known camera pose (from metadata + offsets).

## 2. Camera model
For each image keypoint `(u, v)`:
1. Remove lens distortion via `cv2.undistortPoints`.
2. Convert to normalized camera ray:

$$
\mathbf{d}_{cam} = \frac{[x_n,\ y_n,\ 1]^T}{\|[x_n,\ y_n,\ 1]^T\|}
$$

## 3. Pose and coordinate transforms
The implementation builds a world ray direction from:
- gimbal yaw/pitch/roll
- user offsets (`yaw_offset`, `pitch_offset`, `roll_offset`)
- frame transforms: camera -> NED -> ECEF

World ray:

$$
\mathbf{d}_i = R_{ecef\leftarrow ned}(lat,lon) \cdot R_{body\leftarrow ned}(yaw,pitch,roll) \cdot R_{cam\leftarrow ned} \cdot \mathbf{d}_{cam}
$$

Ray origin in ECEF:

$$
\mathbf{O}_i = \text{ECEF}(lat_i, lon_i, alt_i) + [dX, dY, dZ]^T
$$

## 4. Triangulation as least squares
Each observation gives a 3D line:

$$
\mathbf{X} = \mathbf{O}_i + \lambda_i \mathbf{d}_i
$$

Instead of intersecting lines directly, we solve a least-squares system minimizing orthogonal distances to all rays:

$$
(I - \mathbf{d}_i\mathbf{d}_i^T)\mathbf{X} = (I - \mathbf{d}_i\mathbf{d}_i^T)\mathbf{O}_i
$$

Stack all observations:

$$
A\mathbf{X} = b
$$

Then solve with `numpy.linalg.lstsq`.

## 5. Distance computation
For two reconstructed points `X_a`, `X_b`:

$$
D = \|\mathbf{X}_a - \mathbf{X}_b\|_2
$$

This is the 3D Euclidean distance shown in the demo app.

## 6. Accuracy drivers
- Calibration quality (`camera_matrix`, distortion coefficients)
- Pose quality (metadata and extrinsics)
- Baseline geometry between views
- Annotation precision (sub-pixel helps)

## 7. Practical constraints
- A keypoint requires >= 2 valid observations.
- Near-parallel rays reduce depth stability.
- Current implementation uses memory store; no persistence layer.
