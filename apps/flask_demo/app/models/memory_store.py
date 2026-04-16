# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Copyright contributors to the Leinao project
import time
import uuid
from copy import deepcopy
from threading import RLock
from typing import Dict, Any, List, Tuple, Optional


CAMERA_MODEL_PRESETS: Dict[str, Dict[str, Any]] = {
    "m3e": {
        "camera_matrix": [
            [3660.0, 0.0, 2640.0],
            [0.0, 3660.0, 1978.0],
            [0.0, 0.0, 1.0],
        ],
        "distortion_coefficients": [[0.0, 0.0, 0.0, 0.0, 0.0]],
    },
    "m3t": {
        "camera_matrix": [
            [5500.0, 0.0, 4000.0],
            [0.0, 5500.0, 3000.0],
            [0.0, 0.0, 1.0],
        ],
        "distortion_coefficients": [[0.0, 0.0, 0.0, 0.0, 0.0]],
    },
    "others": {
        "camera_matrix": [
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
        ],
        "distortion_coefficients": [[0.0, 0.0, 0.0, 0.0, 0.0]],
    },
}


def normalize_camera_model(model: Optional[str]) -> str:
    raw = (model or "").strip().lower().replace("-", "").replace("_", "").replace(" ", "")
    if raw in {"m3t", "mavic3t", "御3t"}:
        return "m3t"
    if raw in {"others", "other", "otherscamera", "其它", "其他"}:
        return "others"
    return "m3e"


class MemoryStore:
    """
    纯内存存储：图片二进制、标注点、内外参
    - 不落盘
    - 进程退出自动清空
    """
    def __init__(self, default_camera_model: str = "m3e"):
        self._lock = RLock()
        self._images: Dict[str, Dict[str, Any]] = {}        # image_id -> {name,mime,data,created_at}
        self._order: List[str] = []                         # 保持列表顺序
        self._annotations: Dict[str, Dict[str, Any]] = {}   # image_id -> {image_id, points, meta}
        self._default_camera_model = normalize_camera_model(default_camera_model)
        self._camera: Dict[str, Any] = self._build_default_camera_params()

    def _build_default_camera_params(self) -> Dict[str, Any]:
        intr = deepcopy(CAMERA_MODEL_PRESETS[self._default_camera_model])
        extr = {
            "yaw_offset": 0.0,
            "pitch_offset": 0.0,
            "roll_offset": 0.0,
            "dX": 0.0,
            "dY": 0.0,
            "dZ": 0.0,
        }
        return {"intrinsics": intr, "extrinsics": extr}

    # ---------- images ----------
    def add_image(self, *, filename: str, mime: str, data: bytes) -> Dict[str, Any]:
        with self._lock:
            image_id = uuid.uuid4().hex
            self._images[image_id] = {
                "id": image_id,
                "name": filename,
                "mime": mime or "application/octet-stream",
                "data": data,
                "created_at": time.time(),
            }
            self._order.append(image_id)
            return {
                "id": image_id,
                "name": filename,
                "url": f"/api/images/{image_id}/content",
            }

    def list_images(self) -> List[Dict[str, Any]]:
        with self._lock:
            out = []
            for image_id in self._order:
                img = self._images.get(image_id)
                if not img:
                    continue
                out.append({
                    "id": img["id"],
                    "name": img["name"],
                    "url": f"/api/images/{img['id']}/content",
                })
            return out

    def get_image_bytes(self, image_id: str) -> Optional[Tuple[bytes, str]]:
        with self._lock:
            img = self._images.get(image_id)
            if not img:
                return None
            return img["data"], img["mime"]

    # ---------- annotations ----------
    def ensure_annotation(self, image_id: str) -> Dict[str, Any]:
        with self._lock:
            if image_id not in self._annotations:
                self._annotations[image_id] = {"image_id": image_id, "points": [], "meta": {}}
            return self._annotations[image_id]

    def get_annotation(self, image_id: str) -> Dict[str, Any]:
        with self._lock:
            return self.ensure_annotation(image_id)

    def save_annotation(self, image_id: str, points: List[Dict[str, Any]], meta: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            data = self.ensure_annotation(image_id)
            data["points"] = points or []
            data["meta"] = meta or {}
            return data

    def iter_all_annotations(self):
        with self._lock:
            for image_id, data in self._annotations.items():
                yield image_id, data

    # ---------- camera params ----------
    def get_camera_params(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "camera_model": self._default_camera_model,
                "intrinsics": deepcopy(self._camera["intrinsics"]),
                "extrinsics": deepcopy(self._camera["extrinsics"]),
            }

    def set_default_camera_model(self, model: str, apply_now: bool = True) -> str:
        with self._lock:
            self._default_camera_model = normalize_camera_model(model)
            if apply_now:
                self._camera = self._build_default_camera_params()
            return self._default_camera_model

    def get_default_camera_model(self) -> str:
        with self._lock:
            return self._default_camera_model

    def set_intrinsics(self, intr: Dict[str, Any]) -> None:
        """
        intr JSON 格式:
        {
          "camera_matrix": [[...],[...],[...]],
          "distortion_coefficients": [[k1,k2,p1,p2,k3]]  或 [k1,k2,p1,p2,k3]
        }
        """
        with self._lock:
            cm = intr.get("camera_matrix", self._camera["intrinsics"]["camera_matrix"])
            dc = intr.get("distortion_coefficients", self._camera["intrinsics"]["distortion_coefficients"])

            # 规范化 distortion_coefficients -> [[5]]
            if isinstance(dc, list) and len(dc) == 5 and all(isinstance(x, (int, float)) for x in dc):
                dc = [dc]
            if not (isinstance(dc, list) and len(dc) >= 1 and isinstance(dc[0], list)):
                dc = [[0.0, 0.0, 0.0, 0.0, 0.0]]

            # K 不能全 0，否则 cv2 会出错；如果用户给了明显无效的 K，就回退到单位阵
            def _is_valid_k(mat):
                try:
                    if len(mat) != 3 or any(len(r) != 3 for r in mat):
                        return False
                    s = sum(abs(float(v)) for r in mat for v in r)
                    return s > 0.0
                except:
                    return False

            if not _is_valid_k(cm):
                cm = [
                    [1.0, 0.0, 0.0],
                    [0.0, 1.0, 0.0],
                    [0.0, 0.0, 1.0],
                ]

            self._camera["intrinsics"] = {
                "camera_matrix": [[float(v) for v in r] for r in cm],
                "distortion_coefficients": [[float(v) for v in dc[0][:5]]],
            }

    def set_extrinsics(self, extr: Dict[str, Any]) -> None:
        with self._lock:
            base = {
                "yaw_offset": 0.0,
                "pitch_offset": 0.0,
                "roll_offset": 0.0,
                "dX": 0.0,
                "dY": 0.0,
                "dZ": 0.0,
            }
            for k in base:
                if k in extr:
                    try:
                        base[k] = float(extr[k])
                    except:
                        base[k] = 0.0
            self._camera["extrinsics"] = base

    def set_camera_params(self, intr: Dict[str, Any], extr: Dict[str, Any]) -> None:
        with self._lock:
            self.set_intrinsics(intr or {})
            self.set_extrinsics(extr or {})

    def reset_camera_params(self) -> None:
        with self._lock:
            self._camera = self._build_default_camera_params()
        
    def clear_all(self, reset_camera: bool = False) -> None:
        with self._lock:
            self._images.clear()
            self._order.clear()
            self._annotations.clear()
            if reset_camera:
                self.reset_camera_params()



STORE = MemoryStore()
