# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Copyright contributors to the Leinao project
from __future__ import annotations

import glob
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

import cv2
import numpy as np


@dataclass(frozen=True)
class ZhangIntrinsicsConfig:
    board_cols: int
    board_rows: int
    square_size: float = 1.0
    use_findchessboard_sb: bool = True
    corner_refine_window: int = 11
    corner_refine_eps: float = 1e-3
    corner_refine_max_iter: int = 30

    @property
    def board_size(self) -> Tuple[int, int]:
        # OpenCV order: (columns, rows) = (corners per row, corners per column)
        return (int(self.board_cols), int(self.board_rows))


def collect_chessboard_observations(
    image_paths: Sequence[str | Path],
    config: ZhangIntrinsicsConfig,
) -> Dict[str, object]:
    if not image_paths:
        raise ValueError("image_paths is empty.")

    obj_points: List[np.ndarray] = []
    img_points: List[np.ndarray] = []
    used_images: List[str] = []
    rejected_images: List[str] = []
    image_size: Tuple[int, int] | None = None

    obj_template = _build_object_points(config)
    criteria = (
        cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER,
        int(config.corner_refine_max_iter),
        float(config.corner_refine_eps),
    )

    for path in image_paths:
        path_str = str(path)
        gray = cv2.imread(path_str, cv2.IMREAD_GRAYSCALE)
        if gray is None:
            rejected_images.append(path_str)
            continue

        if image_size is None:
            image_size = (int(gray.shape[1]), int(gray.shape[0]))
        elif image_size != (int(gray.shape[1]), int(gray.shape[0])):
            rejected_images.append(path_str)
            continue

        found, corners = _find_corners(gray, config)
        if not found:
            rejected_images.append(path_str)
            continue

        if not config.use_findchessboard_sb:
            win = (int(config.corner_refine_window), int(config.corner_refine_window))
            zero_zone = (-1, -1)
            corners = cv2.cornerSubPix(gray, corners, win, zero_zone, criteria)

        obj_points.append(obj_template.copy())
        img_points.append(corners.astype(np.float32))
        used_images.append(path_str)

    if not obj_points or image_size is None:
        raise ValueError("No valid chessboard detections found. Check board size and images.")

    return {
        "object_points": obj_points,
        "image_points": img_points,
        "image_size": image_size,
        "used_images": used_images,
        "rejected_images": rejected_images,
    }


def calibrate_intrinsics_zhang(
    image_paths: Sequence[str | Path],
    config: ZhangIntrinsicsConfig,
) -> Dict[str, object]:
    data = collect_chessboard_observations(image_paths=image_paths, config=config)

    obj_points = data["object_points"]
    img_points = data["image_points"]
    image_size = data["image_size"]
    used_images = data["used_images"]
    rejected_images = data["rejected_images"]

    if len(obj_points) < 3:
        raise ValueError("At least 3 valid calibration images are required.")

    rms, camera_matrix, dist_coeffs, rvecs, tvecs = cv2.calibrateCamera(
        obj_points,
        img_points,
        image_size,
        None,
        None,
    )

    dist5 = _normalize_distortion_5(dist_coeffs)
    per_view_errors = _compute_per_view_reprojection_errors(
        obj_points=obj_points,
        img_points=img_points,
        rvecs=rvecs,
        tvecs=tvecs,
        camera_matrix=camera_matrix,
        dist_coeffs=dist_coeffs,
    )

    return {
        "camera_matrix": np.asarray(camera_matrix, dtype=np.float64),
        "distortion_coefficients": dist5,
        "rms": float(rms),
        "mean_reprojection_error": float(np.mean(per_view_errors)),
        "per_view_reprojection_error": [float(v) for v in per_view_errors],
        "used_images": used_images,
        "rejected_images": rejected_images,
        "image_size": list(image_size),
    }


def format_intrinsics_payload(
    camera_matrix: np.ndarray,
    dist_coeffs: Sequence[float],
) -> Dict[str, List[List[float]]]:
    dist5 = _normalize_distortion_5(np.asarray(dist_coeffs, dtype=np.float64))
    return {
        "camera_matrix": np.asarray(camera_matrix, dtype=np.float64).tolist(),
        "distortion_coefficients": [dist5.tolist()],
    }


def save_intrinsics_json(
    camera_matrix: np.ndarray,
    dist_coeffs: Sequence[float],
    output_path: str | Path,
) -> Dict[str, List[List[float]]]:
    payload = format_intrinsics_payload(camera_matrix=camera_matrix, dist_coeffs=dist_coeffs)
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return payload


def calibrate_from_image_pattern(
    image_pattern: str,
    config: ZhangIntrinsicsConfig,
    output_path: str | Path,
) -> Dict[str, object]:
    image_paths = sorted(glob.glob(image_pattern))
    if not image_paths:
        raise ValueError(f"No images matched pattern: {image_pattern}")

    result = calibrate_intrinsics_zhang(image_paths=image_paths, config=config)
    payload = save_intrinsics_json(
        camera_matrix=result["camera_matrix"],
        dist_coeffs=result["distortion_coefficients"],
        output_path=output_path,
    )
    return {
        "params": payload,
        "metrics": {
            "rms": result["rms"],
            "mean_reprojection_error": result["mean_reprojection_error"],
            "valid_image_count": float(len(result["used_images"])),
            "rejected_image_count": float(len(result["rejected_images"])),
        },
        "used_images": result["used_images"],
        "rejected_images": result["rejected_images"],
        "image_size": result["image_size"],
    }


def _build_object_points(config: ZhangIntrinsicsConfig) -> np.ndarray:
    cols, rows = config.board_size
    objp = np.zeros((rows * cols, 3), dtype=np.float32)
    grid = np.mgrid[0:cols, 0:rows].T.reshape(-1, 2)
    objp[:, :2] = grid * float(config.square_size)
    return objp


def _find_corners(gray: np.ndarray, config: ZhangIntrinsicsConfig) -> Tuple[bool, np.ndarray]:
    flags = cv2.CALIB_CB_ADAPTIVE_THRESH + cv2.CALIB_CB_NORMALIZE_IMAGE
    board_size = config.board_size

    if config.use_findchessboard_sb and hasattr(cv2, "findChessboardCornersSB"):
        found, corners = cv2.findChessboardCornersSB(gray, board_size, flags=0)
        if found:
            return True, corners

    found, corners = cv2.findChessboardCorners(gray, board_size, flags)
    return bool(found), corners


def _normalize_distortion_5(dist_coeffs: np.ndarray) -> np.ndarray:
    arr = np.asarray(dist_coeffs, dtype=np.float64).reshape(-1)
    out = np.zeros(5, dtype=np.float64)
    out[: min(5, arr.size)] = arr[:5]
    return out


def _compute_per_view_reprojection_errors(
    obj_points: Sequence[np.ndarray],
    img_points: Sequence[np.ndarray],
    rvecs: Sequence[np.ndarray],
    tvecs: Sequence[np.ndarray],
    camera_matrix: np.ndarray,
    dist_coeffs: np.ndarray,
) -> List[float]:
    errors: List[float] = []
    for i in range(len(obj_points)):
        projected, _ = cv2.projectPoints(
            obj_points[i],
            rvecs[i],
            tvecs[i],
            camera_matrix,
            dist_coeffs,
        )
        err = cv2.norm(img_points[i], projected, cv2.NORM_L2) / max(len(projected), 1)
        errors.append(float(err))
    return errors
