# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Copyright contributors to the Leinao project
from typing import Any, Dict, Mapping, Sequence

import cv2
import numpy as np
import pandas as pd

from .exceptions import InputSchemaError
from .models import CameraExtrinsics
from .transforms import body_to_ned_matrix, cam_ray_to_ecef, lla_to_ecef, ned_to_ecef_matrix


class CameraTriangulator:
    """Triangulate points from multi-view 2D observations into ECEF coordinates."""

    def __init__(self, camera_intrinsic: np.ndarray, dist_coeffs: np.ndarray, extrinsics: Any):
        self.K = np.asarray(camera_intrinsic, dtype=np.float64)
        self.dist = np.asarray(dist_coeffs, dtype=np.float64)

        ext = self._parse_extrinsics(extrinsics)
        self.yaw_off = float(ext.yaw_offset)
        self.pitch_off = float(ext.pitch_offset)
        self.roll_off = float(ext.roll_offset)
        self.translation_frame = str(ext.translation_frame).lower()
        self.translation_vector = np.asarray([ext.dX, ext.dY, ext.dZ], dtype=np.float64)

    @staticmethod
    def _parse_extrinsics(extrinsics: Any) -> CameraExtrinsics:
        if isinstance(extrinsics, CameraExtrinsics):
            return extrinsics

        if isinstance(extrinsics, Mapping):
            return CameraExtrinsics.from_mapping(extrinsics)

        if isinstance(extrinsics, Sequence) and not isinstance(extrinsics, (str, bytes)):
            if len(extrinsics) < 6:
                raise ValueError("extrinsics sequence must contain at least 6 values")
            return CameraExtrinsics(*[float(v) for v in extrinsics[:6]], translation_frame="ecef")

        raise TypeError("Unsupported extrinsics type for CameraTriangulator")

    def _resolve_translation_ecef(
        self,
        lat_deg: float,
        lon_deg: float,
        yaw_deg: float,
        pitch_deg: float,
        roll_deg: float,
    ) -> np.ndarray:
        frame = self.translation_frame
        t = self.translation_vector

        if frame == "ecef":
            return t

        if frame == "ned":
            return ned_to_ecef_matrix(lat_deg, lon_deg) @ t

        if frame == "camera":
            return cam_ray_to_ecef(yaw_deg, pitch_deg, roll_deg, lat_deg, lon_deg, t)

        if frame == "body":
            r_ecef_ned = ned_to_ecef_matrix(lat_deg, lon_deg)
            r_body_ned = body_to_ned_matrix(yaw_deg, pitch_deg, roll_deg)
            return r_ecef_ned @ (r_body_ned @ t)

        raise ValueError(f"Unsupported translation_frame: {frame}")

    def compute_min_max_baselines(self, predict_df: pd.DataFrame):
        baselines = []
        for i in range(len(predict_df) - 1):
            p1 = lla_to_ecef(
                predict_df.loc[i, "lat"],
                predict_df.loc[i, "lon"],
                predict_df.loc[i, "alt"],
            )
            p2 = lla_to_ecef(
                predict_df.loc[i + 1, "lat"],
                predict_df.loc[i + 1, "lon"],
                predict_df.loc[i + 1, "alt"],
            )
            baselines.append(np.linalg.norm(p1 - p2))

        if not baselines:
            return None, None
        return float(min(baselines)), float(max(baselines))

    def _backproject_ray(self, u: float, v: float) -> np.ndarray:
        pts = np.array([[[u, v]]], dtype=np.float64)
        undistorted = cv2.undistortPoints(pts, self.K, self.dist)
        x_n, y_n = undistorted[0, 0]
        ray = np.array([x_n, y_n, 1.0], dtype=np.float64)
        return ray / np.linalg.norm(ray)

    def _triangulate_point(self, observations: Sequence[Dict[str, float]]) -> np.ndarray:
        a_blocks = []
        b_blocks = []

        for obs in observations:
            d_cam = self._backproject_ray(obs["u"], obs["v"])

            yaw = obs["gimbal_yaw"] + self.yaw_off
            pitch = obs["gimbal_pitch"] + self.pitch_off
            roll = obs["gimbal_roll"] + self.roll_off

            ray_world = cam_ray_to_ecef(
                yaw,
                pitch,
                roll,
                obs["lat"],
                obs["lon"],
                d_cam,
            )
            d = ray_world / np.linalg.norm(ray_world)

            cam_ecef = lla_to_ecef(obs["lat"], obs["lon"], obs["alt"])
            t_ecef = self._resolve_translation_ecef(obs["lat"], obs["lon"], yaw, pitch, roll)
            origin = cam_ecef + t_ecef

            i3 = np.eye(3, dtype=np.float64)
            p = i3 - np.outer(d, d)
            a_blocks.append(p)
            b_blocks.append(p @ origin)

        a = np.vstack(a_blocks)
        b = np.vstack(b_blocks).reshape(-1)
        x, _, _, _ = np.linalg.lstsq(a, b, rcond=None)
        return x.astype(np.float64).flatten()

    def _3d_point(self, predict_df: pd.DataFrame):
        points = []
        grouped = predict_df.groupby(["group", "idx"])

        for (group, idx), sub_df in grouped:
            if len(sub_df) < 2:
                continue

            observations = []
            for _, row in sub_df.iterrows():
                observations.append(
                    {
                        "u": row["x"],
                        "v": row["y"],
                        "lat": row["lat"],
                        "lon": row["lon"],
                        "alt": row["alt"],
                        "gimbal_pitch": row["gimbal_pitch"],
                        "gimbal_yaw": row["gimbal_yaw"],
                        "gimbal_roll": row["gimbal_roll"],
                    }
                )

            pos = self._triangulate_point(observations)
            points.append(
                {
                    "group": int(group),
                    "idx": int(idx),
                    "position": pos.tolist(),
                }
            )

        return points

    def get_3d_results(self, df_xy: pd.DataFrame) -> pd.DataFrame:
        required = [
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
        missing = [name for name in required if name not in df_xy.columns]
        if missing:
            raise InputSchemaError(f"df_xy missing required columns: {missing}")

        df_out = df_xy.copy()
        predict_df = df_xy.copy()
        predict_df["group"] = 0
        predict_df["idx"] = predict_df["keypoint_id"]

        numeric_cols = [
            "keypoint_id",
            "x",
            "y",
            "lat",
            "lon",
            "alt",
            "gimbal_pitch",
            "gimbal_yaw",
            "gimbal_roll",
            "group",
            "idx",
        ]
        for col in numeric_cols:
            predict_df[col] = pd.to_numeric(predict_df[col], errors="coerce")

        predict_df = predict_df.dropna(
            subset=[
                "idx",
                "x",
                "y",
                "lat",
                "lon",
                "alt",
                "gimbal_pitch",
                "gimbal_yaw",
                "gimbal_roll",
            ]
        )

        rows = self._3d_point(predict_df)
        pos_map = {int(row["idx"]): [float(v) for v in row["position"]] for row in rows}

        keypoints = pd.to_numeric(df_out["keypoint_id"], errors="coerce").astype("Int64")
        df_out["_3d_position"] = keypoints.map(
            lambda keypoint: pos_map.get(int(keypoint)) if pd.notna(keypoint) else None
        )
        return df_out
