# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Copyright contributors to the Leinao project
import csv
import io
import json
import zipfile
from typing import Any, Dict, List

from ..models.annotation_model import list_all_annotations, load_annotation, save_annotation
from .image_service import fetch_image_bytes

try:
    import cv2
    import numpy as np
except Exception:  # pragma: no cover - fallback when optional runtime deps are missing
    cv2 = None
    np = None


def get_annotations(image_id: str) -> Dict[str, Any]:
    return load_annotation(image_id)


def save_annotations(image_id: str, points: List[Dict[str, Any]], meta: Dict[str, Any]) -> Dict[str, Any]:
    return save_annotation(image_id, points, meta)


def build_image_json_bytes(image_id: str) -> bytes:
    data = load_annotation(image_id)
    return json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")


def _safe_stem(name: str) -> str:
    cleaned = "".join(ch for ch in (name or "").strip() if ch not in r'\/:*?"<>|')
    if not cleaned:
        return "annotation"
    if "." in cleaned:
        return cleaned.rsplit(".", 1)[0] or "annotation"
    return cleaned


def _detect_image_wh(image_id: str) -> tuple[int | None, int | None]:
    if cv2 is None or np is None:
        return None, None
    image = fetch_image_bytes(image_id)
    if not image:
        return None, None
    data, _mime = image
    try:
        arr = np.frombuffer(data, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_UNCHANGED)
        if img is None:
            return None, None
        h, w = img.shape[:2]
        return int(w), int(h)
    except Exception:
        return None, None


def _to_xanything_label(image_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    meta = data.get("meta") or {}
    image_name = str(meta.get("name") or f"{image_id}.jpg")
    image_width, image_height = _detect_image_wh(image_id)

    shapes: List[Dict[str, Any]] = []
    for point in data.get("points", []):
        try:
            x = float(point.get("x"))
            y = float(point.get("y"))
        except Exception:
            continue
        keypoint_id = point.get("keypoint_id")
        label = str(keypoint_id) if keypoint_id is not None else "point"
        shapes.append(
            {
                "label": label,
                "points": [[x, y]],
                "group_id": None,
                "description": "",
                "shape_type": "point",
                "flags": {},
                "attributes": {"keypoint_id": keypoint_id},
            }
        )

    return {
        "version": "xanything-label-1.0",
        "flags": {},
        "shapes": shapes,
        "imagePath": image_name,
        "imageData": None,
        "imageHeight": image_height,
        "imageWidth": image_width,
    }


def build_xanything_zip_bytes() -> bytes:
    output = io.BytesIO()
    used_names: Dict[str, int] = {}

    with zipfile.ZipFile(output, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for image_id, data in list_all_annotations():
            points = data.get("points", [])
            if not points:
                continue

            payload = _to_xanything_label(image_id, data)
            if not payload.get("shapes"):
                continue
            image_name = str((data.get("meta") or {}).get("name") or image_id)
            stem = _safe_stem(image_name)

            index = used_names.get(stem, 0)
            used_names[stem] = index + 1
            file_name = f"{stem}.json" if index == 0 else f"{stem}_{index}.json"

            zf.writestr(file_name, json.dumps(payload, ensure_ascii=False, indent=2))

        if not zf.namelist():
            zf.writestr(
                "README.txt",
                "No labeled points found. Please annotate points before exporting JSON.",
            )

    return output.getvalue()


def build_all_csv_bytes() -> bytes:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["image", "keypoint_id", "x", "y"])

    for image_id, data in list_all_annotations():
        for point in data.get("points", []):
            writer.writerow([
                image_id,
                point.get("keypoint_id"),
                point.get("x"),
                point.get("y"),
            ])

    return output.getvalue().encode("utf-8")
