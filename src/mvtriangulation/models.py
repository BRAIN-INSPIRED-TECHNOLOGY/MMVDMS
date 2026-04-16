# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Copyright contributors to the Leinao project
from dataclasses import dataclass
from typing import Any, Iterable, List, Mapping


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


@dataclass(frozen=True)
class CameraIntrinsics:
    camera_matrix: List[List[float]]
    distortion_coefficients: List[List[float]]


@dataclass(frozen=True)
class CameraExtrinsics:
    yaw_offset: float = 0.0
    pitch_offset: float = 0.0
    roll_offset: float = 0.0
    dX: float = 0.0
    dY: float = 0.0
    dZ: float = 0.0
    translation_frame: str = "ecef"

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "CameraExtrinsics":
        meta = payload.get("_meta", {}) if isinstance(payload.get("_meta"), Mapping) else {}

        frame = str(
            payload.get("translation_frame", meta.get("translation_frame", "ecef"))
        ).lower()

        yaw_offset = _to_float(payload.get("yaw_offset", 0.0))
        pitch_offset = _to_float(payload.get("pitch_offset", 0.0))
        roll_offset = _to_float(payload.get("roll_offset", 0.0))

        rotation_offset = payload.get("rotation_offset")
        if isinstance(rotation_offset, Mapping):
            yaw_offset = _to_float(rotation_offset.get("yaw", yaw_offset), yaw_offset)
            pitch_offset = _to_float(rotation_offset.get("pitch", pitch_offset), pitch_offset)
            roll_offset = _to_float(rotation_offset.get("roll", roll_offset), roll_offset)

        d_x = _to_float(payload.get("dX", payload.get("dx", 0.0)))
        d_y = _to_float(payload.get("dY", payload.get("dy", 0.0)))
        d_z = _to_float(payload.get("dZ", payload.get("dz", 0.0)))

        translation = payload.get("translation")
        if isinstance(translation, Mapping):
            d_x = _to_float(translation.get("x", d_x), d_x)
            d_y = _to_float(translation.get("y", d_y), d_y)
            d_z = _to_float(translation.get("z", d_z), d_z)

        return cls(
            yaw_offset=yaw_offset,
            pitch_offset=pitch_offset,
            roll_offset=roll_offset,
            dX=d_x,
            dY=d_y,
            dZ=d_z,
            translation_frame=frame,
        )

    def as_list(self) -> List[float]:
        return [
            self.yaw_offset,
            self.pitch_offset,
            self.roll_offset,
            self.dX,
            self.dY,
            self.dZ,
        ]

    def as_dict(self) -> Mapping[str, Any]:
        return {
            "yaw_offset": self.yaw_offset,
            "pitch_offset": self.pitch_offset,
            "roll_offset": self.roll_offset,
            "dX": self.dX,
            "dY": self.dY,
            "dZ": self.dZ,
            "translation_frame": self.translation_frame,
        }


@dataclass(frozen=True)
class Observation:
    u: float
    v: float
    lat: float
    lon: float
    alt: float
    gimbal_pitch: float
    gimbal_yaw: float
    gimbal_roll: float


def as_float_list(values: Iterable[float]) -> List[float]:
    return [float(v) for v in values]
