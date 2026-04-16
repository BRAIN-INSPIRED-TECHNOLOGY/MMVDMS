# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Copyright contributors to the Leinao project
from typing import Any, Mapping, Sequence, Tuple

import numpy as np
import pandas as pd

from .models import CameraExtrinsics
from .triangulator import CameraTriangulator


def _is_valid_camera_matrix(matrix: Sequence[Sequence[Any]]) -> bool:
    try:
        if len(matrix) != 3 or any(len(row) != 3 for row in matrix):
            return False
        total = sum(abs(float(v)) for row in matrix for v in row)
        return total > 0.0
    except Exception:
        return False


def _normalize_distortion_coefficients(dc: Any) -> np.ndarray:
    if isinstance(dc, list) and len(dc) == 5:
        return np.asarray(dc, dtype=np.float64).ravel()
    if isinstance(dc, list) and dc and isinstance(dc[0], list):
        return np.asarray(dc[0], dtype=np.float64).ravel()
    return np.asarray([0.0, 0.0, 0.0, 0.0, 0.0], dtype=np.float64)


def build_extrinsics_config(extrinsics: Any) -> Mapping[str, Any]:
    if isinstance(extrinsics, CameraExtrinsics):
        return extrinsics.as_dict()

    if isinstance(extrinsics, Mapping):
        return CameraExtrinsics.from_mapping(extrinsics).as_dict()

    if isinstance(extrinsics, Sequence) and not isinstance(extrinsics, (str, bytes)):
        if len(extrinsics) < 6:
            raise ValueError("extrinsics sequence must contain at least 6 values")
        ext = CameraExtrinsics(*[float(v) for v in extrinsics[:6]], translation_frame="ecef")
        return ext.as_dict()

    raise TypeError("Unsupported extrinsics type")


def build_camera_arrays(
    intrinsics: Mapping[str, Any],
    extrinsics: Any,
) -> Tuple[np.ndarray, np.ndarray, Mapping[str, Any]]:
    camera_matrix = intrinsics.get("camera_matrix")
    if not _is_valid_camera_matrix(camera_matrix):
        camera_matrix = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]

    distortion_coefficients = _normalize_distortion_coefficients(
        intrinsics.get("distortion_coefficients", [[0.0, 0.0, 0.0, 0.0, 0.0]])
    )

    extr_cfg = build_extrinsics_config(extrinsics)

    return np.asarray(camera_matrix, dtype=np.float64), distortion_coefficients, extr_cfg


def triangulate_dataframe(
    df_xy: pd.DataFrame,
    camera_matrix: np.ndarray,
    dist_coeffs: np.ndarray,
    extrinsics: Any,
) -> pd.DataFrame:
    triangulator = CameraTriangulator(camera_matrix, dist_coeffs, extrinsics)
    return triangulator.get_3d_results(df_xy)


def detect(
    df_xy: pd.DataFrame,
    camera_matrix: np.ndarray,
    dist_coeffs: np.ndarray,
    extrinsics: Any,
) -> pd.DataFrame:
    """Backward-compatible alias."""
    return triangulate_dataframe(df_xy, camera_matrix, dist_coeffs, extrinsics)
