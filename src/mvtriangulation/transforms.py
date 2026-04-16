# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Copyright contributors to the Leinao project
import numpy as np

A = 6378137.0
F = 1 / 298.257223563
E2 = F * (2 - F)


def lla_to_ecef(lat_deg: float, lon_deg: float, h: float) -> np.ndarray:
    lat = np.radians(lat_deg)
    lon = np.radians(lon_deg)

    n = A / np.sqrt(1 - E2 * (np.sin(lat) ** 2))
    x = (n + h) * np.cos(lat) * np.cos(lon)
    y = (n + h) * np.cos(lat) * np.sin(lon)
    z = ((1 - E2) * n + h) * np.sin(lat)
    return np.array([x, y, z], dtype=np.float64)


def rz(yaw_rad: float) -> np.ndarray:
    c, s = np.cos(yaw_rad), np.sin(yaw_rad)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]], dtype=np.float64)


def ry(pitch_rad: float) -> np.ndarray:
    c, s = np.cos(pitch_rad), np.sin(pitch_rad)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]], dtype=np.float64)


def rx(roll_rad: float) -> np.ndarray:
    c, s = np.cos(roll_rad), np.sin(roll_rad)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]], dtype=np.float64)


def body_to_ned_matrix(yaw_deg: float, pitch_deg: float, roll_deg: float) -> np.ndarray:
    return rz(np.radians(yaw_deg)) @ ry(np.radians(pitch_deg)) @ rx(np.radians(roll_deg))


def ned_to_ecef_matrix(lat_deg: float, lon_deg: float) -> np.ndarray:
    lat = np.radians(lat_deg)
    lon = np.radians(lon_deg)
    return np.array(
        [
            [-np.sin(lat) * np.cos(lon), -np.sin(lon), -np.cos(lat) * np.cos(lon)],
            [-np.sin(lat) * np.sin(lon), np.cos(lon), -np.cos(lat) * np.sin(lon)],
            [np.cos(lat), 0, -np.sin(lat)],
        ],
        dtype=np.float64,
    )


def cam_to_ned_matrix() -> np.ndarray:
    return np.array([[0, 0, 1], [1, 0, 0], [0, 1, 0]], dtype=np.float64)


def cam_ray_to_ecef(
    yaw_deg: float,
    pitch_deg: float,
    roll_deg: float,
    lat_deg: float,
    lon_deg: float,
    ray_cam: np.ndarray,
) -> np.ndarray:
    r_total = ned_to_ecef_matrix(lat_deg, lon_deg) @ body_to_ned_matrix(yaw_deg, pitch_deg, roll_deg) @ cam_to_ned_matrix()
    return r_total @ ray_cam
