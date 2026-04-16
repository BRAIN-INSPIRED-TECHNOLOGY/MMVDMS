# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Copyright contributors to the Leinao project
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Mapping, Optional, Sequence, Tuple

import cv2
import numpy as np
import pandas as pd
from scipy.optimize import least_squares

from ..transforms import cam_ray_to_ecef, lla_to_ecef

REQUIRED_COLUMNS = (
    "u",
    "v",
    "cam_lat",
    "cam_lon",
    "cam_alt",
    "kp_lat",
    "kp_lon",
    "kp_alt",
    "gimbal_yaw",
    "gimbal_pitch",
    "gimbal_roll",
)


@dataclass(frozen=True)
class ExtrinsicFitConfig:
    use_xyz_offset: bool = False
    yaw_bound_deg: float = 30.0
    pitch_bound_deg: float = 30.0
    roll_bound_deg: float = 30.0
    xyz_bound_m: float = 20.0
    loss: str = "soft_l1"
    f_scale: float = 2.0
    max_nfev: int = 500


def load_intrinsics_json(intrinsics_path: str | Path) -> Tuple[np.ndarray, np.ndarray]:
    with open(intrinsics_path, "r", encoding="utf-8") as f:
        payload = json.load(f)

    camera_matrix = np.asarray(payload["camera_matrix"], dtype=np.float64)
    dist_coeffs = _normalize_distortion(payload.get("distortion_coefficients", [0.0] * 5))
    return camera_matrix, dist_coeffs


def load_observations(csv_path: str | Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path)

    missing = [name for name in REQUIRED_COLUMNS if name not in df.columns]
    if missing:
        raise ValueError(f"CSV missing required columns: {missing}")

    for name in REQUIRED_COLUMNS:
        df[name] = pd.to_numeric(df[name], errors="coerce")

    before = len(df)
    df = df.dropna(subset=list(REQUIRED_COLUMNS)).reset_index(drop=True)
    if df.empty:
        raise ValueError("No valid rows after converting required columns to numeric values.")

    if len(df) < before:
        print(f"[WARN] Dropped {before - len(df)} invalid rows from {csv_path}")

    return df


def fit_extrinsics(
    intrinsics_path: str | Path,
    fit_csv: str | Path,
    config: Optional[ExtrinsicFitConfig] = None,
) -> np.ndarray:
    cfg = config or ExtrinsicFitConfig()
    camera_matrix, dist_coeffs = load_intrinsics_json(intrinsics_path)
    fit_df = load_observations(fit_csv)

    if cfg.use_xyz_offset:
        x0 = np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0], dtype=np.float64)
        bounds = (
            np.array(
                [
                    -cfg.yaw_bound_deg,
                    -cfg.pitch_bound_deg,
                    -cfg.roll_bound_deg,
                    -cfg.xyz_bound_m,
                    -cfg.xyz_bound_m,
                    -cfg.xyz_bound_m,
                ],
                dtype=np.float64,
            ),
            np.array(
                [
                    cfg.yaw_bound_deg,
                    cfg.pitch_bound_deg,
                    cfg.roll_bound_deg,
                    cfg.xyz_bound_m,
                    cfg.xyz_bound_m,
                    cfg.xyz_bound_m,
                ],
                dtype=np.float64,
            ),
        )
    else:
        x0 = np.array([0.0, 0.0, 0.0], dtype=np.float64)
        bounds = (
            np.array([-cfg.yaw_bound_deg, -cfg.pitch_bound_deg, -cfg.roll_bound_deg], dtype=np.float64),
            np.array([cfg.yaw_bound_deg, cfg.pitch_bound_deg, cfg.roll_bound_deg], dtype=np.float64),
        )

    result = least_squares(
        _residuals_point_to_ray,
        x0,
        args=(fit_df, camera_matrix, dist_coeffs, cfg.use_xyz_offset),
        method="trf",
        bounds=bounds,
        loss=cfg.loss,
        f_scale=cfg.f_scale,
        max_nfev=cfg.max_nfev,
    )

    if cfg.use_xyz_offset:
        return result.x.astype(np.float64)
    return np.array([result.x[0], result.x[1], result.x[2], 0.0, 0.0, 0.0], dtype=np.float64)


def evaluate_extrinsics(
    params6: Sequence[float],
    intrinsics_path: str | Path,
    test_csv: str | Path,
) -> Dict[str, float]:
    p = _normalize_params(params6)
    yaw_offset, pitch_offset, roll_offset, d_x, d_y, d_z = p

    camera_matrix, dist_coeffs = load_intrinsics_json(intrinsics_path)
    test_df = load_observations(test_csv)

    angle_errors_deg = []
    point_to_ray_errors_m = []

    for row in test_df.itertuples(index=False):
        ray_cam = _undistort_ray(float(row.u), float(row.v), camera_matrix, dist_coeffs)

        yaw = float(row.gimbal_yaw) + yaw_offset
        pitch = float(row.gimbal_pitch) + pitch_offset
        roll = float(row.gimbal_roll) + roll_offset

        ray_world = cam_ray_to_ecef(yaw, pitch, roll, float(row.cam_lat), float(row.cam_lon), ray_cam)
        ray_world = ray_world / np.linalg.norm(ray_world)

        cam_origin = lla_to_ecef(float(row.cam_lat), float(row.cam_lon), float(row.cam_alt))
        cam_origin = cam_origin + np.array([d_x, d_y, d_z], dtype=np.float64)
        target = lla_to_ecef(float(row.kp_lat), float(row.kp_lon), float(row.kp_alt))

        distance = _point_to_ray_distance(target, cam_origin, ray_world)
        point_to_ray_errors_m.append(distance)

        target_dir = target - cam_origin
        target_dir = target_dir / np.linalg.norm(target_dir)
        cos_angle = float(np.clip(np.dot(target_dir, ray_world), -1.0, 1.0))
        angle_errors_deg.append(float(np.degrees(np.arccos(cos_angle))))

    return {
        "angle_rmse_deg": float(np.sqrt(np.mean(np.square(angle_errors_deg)))),
        "angle_mae_deg": float(np.mean(np.abs(angle_errors_deg))),
        "point_to_ray_rmse_m": float(np.sqrt(np.mean(np.square(point_to_ray_errors_m)))),
        "point_to_ray_mae_m": float(np.mean(np.abs(point_to_ray_errors_m))),
        "sample_count": float(len(test_df)),
    }


def format_extrinsics_payload(params6: Sequence[float]) -> Dict[str, float]:
    yaw_offset, pitch_offset, roll_offset, d_x, d_y, d_z = _normalize_params(params6)
    return {
        "yaw_offset": yaw_offset,
        "pitch_offset": pitch_offset,
        "roll_offset": roll_offset,
        "dX": d_x,
        "dY": d_y,
        "dZ": d_z,
    }


def save_extrinsics_json(params6: Sequence[float], output_path: str | Path) -> Dict[str, float]:
    payload = format_extrinsics_payload(params6)
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return payload


def calibrate_and_save(
    intrinsics_path: str | Path,
    fit_csv: str | Path,
    output_path: str | Path,
    config: Optional[ExtrinsicFitConfig] = None,
    test_csv: str | Path | None = None,
) -> Dict[str, Mapping[str, float]]:
    params6 = fit_extrinsics(intrinsics_path=intrinsics_path, fit_csv=fit_csv, config=config)
    payload = save_extrinsics_json(params6=params6, output_path=output_path)

    result: Dict[str, Mapping[str, float]] = {"params": payload}
    if test_csv:
        result["metrics"] = evaluate_extrinsics(
            params6=params6,
            intrinsics_path=intrinsics_path,
            test_csv=test_csv,
        )
    return result


def _normalize_distortion(raw: object) -> np.ndarray:
    if isinstance(raw, np.ndarray):
        return raw.astype(np.float64).reshape(-1)[:5]
    if isinstance(raw, list):
        if len(raw) == 5 and not any(isinstance(v, list) for v in raw):
            return np.asarray(raw, dtype=np.float64)
        if raw and isinstance(raw[0], list):
            return np.asarray(raw[0], dtype=np.float64).reshape(-1)[:5]
    return np.asarray([0.0, 0.0, 0.0, 0.0, 0.0], dtype=np.float64)


def _normalize_params(params6: Sequence[float]) -> Tuple[float, float, float, float, float, float]:
    arr = np.asarray(list(params6), dtype=np.float64).reshape(-1)
    if arr.size < 6:
        raise ValueError("params6 must contain at least 6 numeric values.")
    return (float(arr[0]), float(arr[1]), float(arr[2]), float(arr[3]), float(arr[4]), float(arr[5]))


def _undistort_ray(
    u: float,
    v: float,
    camera_matrix: np.ndarray,
    dist_coeffs: np.ndarray,
) -> np.ndarray:
    pts = np.array([[[u, v]]], dtype=np.float64)
    undistorted = cv2.undistortPoints(pts, camera_matrix, dist_coeffs)
    x_n, y_n = undistorted[0, 0]
    ray = np.array([x_n, y_n, 1.0], dtype=np.float64)
    return ray / np.linalg.norm(ray)


def _point_to_ray_distance(point: np.ndarray, origin: np.ndarray, direction: np.ndarray) -> float:
    vec = point - origin
    t = float(np.dot(vec, direction))
    if t < 0.0:
        return float(np.linalg.norm(vec))
    return float(np.linalg.norm(vec - t * direction))


def _residuals_point_to_ray(
    params: np.ndarray,
    fit_df: pd.DataFrame,
    camera_matrix: np.ndarray,
    dist_coeffs: np.ndarray,
    use_xyz_offset: bool,
) -> np.ndarray:
    if use_xyz_offset:
        yaw_offset, pitch_offset, roll_offset, d_x, d_y, d_z = [float(v) for v in params]
    else:
        yaw_offset, pitch_offset, roll_offset = [float(v) for v in params]
        d_x = d_y = d_z = 0.0

    residuals = []

    for row in fit_df.itertuples(index=False):
        ray_cam = _undistort_ray(float(row.u), float(row.v), camera_matrix, dist_coeffs)

        yaw = float(row.gimbal_yaw) + yaw_offset
        pitch = float(row.gimbal_pitch) + pitch_offset
        roll = float(row.gimbal_roll) + roll_offset

        ray_world = cam_ray_to_ecef(yaw, pitch, roll, float(row.cam_lat), float(row.cam_lon), ray_cam)
        ray_world = ray_world / np.linalg.norm(ray_world)

        cam_origin = lla_to_ecef(float(row.cam_lat), float(row.cam_lon), float(row.cam_alt))
        cam_origin = cam_origin + np.array([d_x, d_y, d_z], dtype=np.float64)
        target = lla_to_ecef(float(row.kp_lat), float(row.kp_lon), float(row.kp_alt))

        residuals.append(_point_to_ray_distance(target, cam_origin, ray_world))

    return np.asarray(residuals, dtype=np.float64)

