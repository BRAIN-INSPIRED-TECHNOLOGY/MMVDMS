# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Copyright contributors to the Leinao project
from typing import Any, Dict, List

import pandas as pd

from mvtriangulation import (
    build_camera_arrays,
    extract_dji_metadata_from_jpeg_bytes,
    triangulate_dataframe,
)

from ..models.memory_store import STORE


def compute_df_xy_with_metadata() -> pd.DataFrame:
    images = STORE.list_images()

    rows: List[Dict[str, Any]] = []
    for image in images:
        image_id = image["id"]
        image_name = image.get("name") or image_id

        annotation = STORE.get_annotation(image_id)
        points = annotation.get("points", []) or []
        if not points:
            continue

        got = STORE.get_image_bytes(image_id)
        metadata = {
            "lat": 0.0,
            "lon": 0.0,
            "alt": 0.0,
            "gimbal_pitch": 0.0,
            "gimbal_yaw": 0.0,
            "gimbal_roll": 0.0,
        }
        if got:
            content, _mime = got
            metadata = extract_dji_metadata_from_jpeg_bytes(content)

        for point in points:
            rows.append(
                {
                    "image": image_name,
                    "keypoint_id": int(point.get("keypoint_id")),
                    "x": float(point.get("x")),
                    "y": float(point.get("y")),
                    **metadata,
                }
            )

    cols = [
        "image",
        "keypoint_id",
        "x",
        "y",
        "lat",
        "lon",
        "alt",
        "gimbal_pitch",
        "gimbal_yaw",
        "gimbal_roll",
    ]
    return pd.DataFrame(rows, columns=cols)


def compute_3d_dataframe() -> pd.DataFrame:
    df_xy = compute_df_xy_with_metadata()
    if df_xy.empty:
        return df_xy.assign(_3d_position=None)

    params = STORE.get_camera_params()
    intrinsics = params.get("intrinsics", {})
    extrinsics = params.get("extrinsics", {})

    camera_matrix, dist_coeffs, extr = build_camera_arrays(intrinsics, extrinsics)
    return triangulate_dataframe(df_xy, camera_matrix, dist_coeffs, extr)
