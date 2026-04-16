# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Copyright contributors to the Leinao project

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from itertools import combinations
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from mvtriangulation import (
    build_camera_arrays,
    extract_dji_metadata_from_jpeg_bytes,
    triangulate_dataframe,
)

LEINAO_CODE_MARK = "[leinao]"


def _print_leinao_mark() -> None:
    print(f"{LEINAO_CODE_MARK} minimal usage starting")


DEFAULT_POINTS_CSV = ROOT / "examples" / "demo_csv" / "keypoints_observation2.csv"
DEFAULT_IMAGE_DIR = ROOT / "examples" / "demo_images"
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".tif", ".tiff"}

CAMERA_PRESETS: Dict[str, Dict[str, List[List[float]]]] = {
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
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Triangulate distances from a point-coordinate CSV and original images with embedded XMP metadata."
    )
    parser.add_argument(
        "--points-csv",
        "--csv",
        dest="points_csv",
        type=Path,
        default=DEFAULT_POINTS_CSV,
        help=f"Point CSV path (default: {DEFAULT_POINTS_CSV})",
    )
    parser.add_argument(
        "--image-dir",
        type=Path,
        default=DEFAULT_IMAGE_DIR,
        help=f"Directory containing original images for metadata extraction (default: {DEFAULT_IMAGE_DIR})",
    )
    parser.add_argument(
        "--camera-model",
        type=str.lower,
        choices=["m3e", "m3t", "others"],
        default="m3e",
        help="Camera preset for intrinsics (default: m3e)",
    )
    parser.add_argument(
        "--intrinsics-json",
        type=Path,
        default=None,
        help="Path to intrinsics JSON. Required for --camera-model others unless --fx/--fy/--cx/--cy are set.",
    )
    parser.add_argument("--fx", type=float, default=None, help="Custom fx for camera matrix")
    parser.add_argument("--fy", type=float, default=None, help="Custom fy for camera matrix")
    parser.add_argument("--cx", type=float, default=None, help="Custom cx for camera matrix")
    parser.add_argument("--cy", type=float, default=None, help="Custom cy for camera matrix")
    parser.add_argument(
        "--dist",
        type=float,
        nargs=5,
        default=None,
        metavar=("k1", "k2", "p1", "p2", "k3"),
        help="Custom distortion coefficients",
    )
    parser.add_argument(
        "--extrinsics-json",
        type=Path,
        default=None,
        help="Optional extrinsics JSON (yaw/pitch/roll + dX/dY/dZ). Default all zeros.",
    )
    parser.add_argument(
        "--pair",
        action="append",
        default=[],
        help="Distance pair, e.g. --pair 1-2 (can repeat). If omitted, all point pairs are computed.",
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=None,
        help="Optional output path for triangulation result CSV.",
    )
    return parser.parse_args()


def _build_intrinsics(args: argparse.Namespace) -> Dict[str, List[List[float]]]:
    if args.intrinsics_json:
        payload = json.loads(args.intrinsics_json.read_text(encoding="utf-8"))
        return {
            "camera_matrix": payload.get("camera_matrix"),
            "distortion_coefficients": payload.get("distortion_coefficients", [[0.0, 0.0, 0.0, 0.0, 0.0]]),
        }

    has_manual = all(v is not None for v in [args.fx, args.fy, args.cx, args.cy])
    if has_manual:
        dc = args.dist if args.dist is not None else [0.0, 0.0, 0.0, 0.0, 0.0]
        return {
            "camera_matrix": [
                [float(args.fx), 0.0, float(args.cx)],
                [0.0, float(args.fy), float(args.cy)],
                [0.0, 0.0, 1.0],
            ],
            "distortion_coefficients": [list(map(float, dc))],
        }

    if args.camera_model in CAMERA_PRESETS:
        return CAMERA_PRESETS[args.camera_model]

    raise ValueError(
        "camera-model=others requires --intrinsics-json or --fx/--fy/--cx/--cy (and optional --dist)."
    )


def _build_extrinsics(args: argparse.Namespace) -> Dict[str, float]:
    if args.extrinsics_json:
        payload = json.loads(args.extrinsics_json.read_text(encoding="utf-8"))
        return {
            "yaw_offset": float(payload.get("yaw_offset", 0.0)),
            "pitch_offset": float(payload.get("pitch_offset", 0.0)),
            "roll_offset": float(payload.get("roll_offset", 0.0)),
            "dX": float(payload.get("dX", payload.get("dx", 0.0))),
            "dY": float(payload.get("dY", payload.get("dy", 0.0))),
            "dZ": float(payload.get("dZ", payload.get("dz", 0.0))),
        }

    return {
        "yaw_offset": 0.0,
        "pitch_offset": 0.0,
        "roll_offset": 0.0,
        "dX": 0.0,
        "dY": 0.0,
        "dZ": 0.0,
    }


def _extract_keypoint_ids(columns: Iterable[str]) -> List[int]:
    ids: List[int] = []
    names = set(columns)
    for name in names:
        if name.startswith("kp") and name.endswith("_x"):
            num = name[2:-2]
            if num.isdigit() and f"kp{num}_y" in names:
                ids.append(int(num))
    return sorted(set(ids))


def _looks_like_legacy_observation_csv(df_raw: pd.DataFrame) -> bool:
    base = {"image", "lat", "lon", "alt", "gimbal_pitch", "gimbal_yaw", "gimbal_roll"}
    return base.issubset(df_raw.columns) and bool(_extract_keypoint_ids(df_raw.columns))


def _convert_legacy_observation_csv_to_observations(df_raw: pd.DataFrame) -> pd.DataFrame:
    kp_ids = _extract_keypoint_ids(df_raw.columns)
    if not kp_ids:
        raise ValueError("No keypoint columns found. Expect columns like kp1_x/kp1_y, kp2_x/kp2_y, ...")

    records: List[Dict[str, Any]] = []
    for _, row in df_raw.iterrows():
        for kp_id in kp_ids:
            x = pd.to_numeric(row.get(f"kp{kp_id}_x"), errors="coerce")
            y = pd.to_numeric(row.get(f"kp{kp_id}_y"), errors="coerce")
            if pd.isna(x) or pd.isna(y):
                continue
            record: Dict[str, Any] = {
                "image": str(row["image"]),
                "keypoint_id": int(kp_id),
                "x": float(x),
                "y": float(y),
                "lat": float(pd.to_numeric(row["lat"], errors="coerce")),
                "lon": float(pd.to_numeric(row["lon"], errors="coerce")),
                "alt": float(pd.to_numeric(row["alt"], errors="coerce")),
                "gimbal_pitch": float(pd.to_numeric(row["gimbal_pitch"], errors="coerce")),
                "gimbal_yaw": float(pd.to_numeric(row["gimbal_yaw"], errors="coerce")),
                "gimbal_roll": float(pd.to_numeric(row["gimbal_roll"], errors="coerce")),
            }
            if "true_length" in df_raw.columns:
                true_length = pd.to_numeric(row.get("true_length"), errors="coerce")
                if pd.notna(true_length):
                    record["true_length"] = float(true_length)
            records.append(record)

    df_xy = pd.DataFrame(records)
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
    ]
    for col in numeric_cols:
        df_xy[col] = pd.to_numeric(df_xy[col], errors="coerce")

    return df_xy.dropna(subset=numeric_cols).reset_index(drop=True)


def _normalize_point_csv(df_raw: pd.DataFrame) -> pd.DataFrame:
    normalized = {str(col).strip().lower(): str(col) for col in df_raw.columns}
    aliases = {
        "image": ["image", "image_name", "filename", "file_name", "img", "img_name", "image_path", "path"],
        "keypoint_id": ["keypoint_id", "point_id", "kp_id", "id"],
        "x": ["x", "u", "pixel_x", "px"],
        "y": ["y", "v", "pixel_y", "py"],
        "true_length": ["true_length", "distance_gt", "gt_distance", "true_distance"],
    }

    selected: Dict[str, str] = {}
    for target, names in aliases.items():
        for name in names:
            if name in normalized:
                selected[target] = normalized[name]
                break

    missing = [name for name in ["image", "keypoint_id", "x", "y"] if name not in selected]
    if missing:
        raise ValueError(
            "Point CSV must contain image/keypoint_id/x/y columns or equivalent aliases. "
            f"Missing: {missing}"
        )

    data = {
        "image": df_raw[selected["image"]].astype(str).str.strip(),
        "keypoint_id": pd.to_numeric(df_raw[selected["keypoint_id"]], errors="coerce"),
        "x": pd.to_numeric(df_raw[selected["x"]], errors="coerce"),
        "y": pd.to_numeric(df_raw[selected["y"]], errors="coerce"),
    }
    if "true_length" in selected:
        data["true_length"] = pd.to_numeric(df_raw[selected["true_length"]], errors="coerce")

    df_points = pd.DataFrame(data)
    df_points = df_points.dropna(subset=["image", "keypoint_id", "x", "y"]).reset_index(drop=True)
    df_points["keypoint_id"] = df_points["keypoint_id"].astype(int)
    return df_points


def _build_image_index(image_dir: Path) -> Dict[str, Dict[str, Any]]:
    if not image_dir.exists():
        raise FileNotFoundError(f"Image directory not found: {image_dir}")

    by_name: Dict[str, Path] = {}
    by_stem: Dict[str, List[Path]] = defaultdict(list)
    for path in sorted(image_dir.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in IMAGE_SUFFIXES:
            continue
        by_name.setdefault(path.name.lower(), path)
        by_stem[path.stem.lower()].append(path)

    if not by_name:
        raise FileNotFoundError(f"No image files found under: {image_dir}")

    return {"name": by_name, "stem": dict(by_stem)}

def _resolve_image_path(image_token: str, image_dir: Path, image_index: Dict[str, Dict[str, Any]]) -> Path:
    token = str(image_token).strip()
    if not token:
        raise ValueError("Empty image value found in point CSV")

    raw_path = Path(token)
    if raw_path.is_absolute() and raw_path.exists():
        return raw_path.resolve()
    if raw_path.exists():
        return raw_path.resolve()

    candidate = image_dir / token
    if candidate.exists():
        return candidate.resolve()

    name_hit = image_index["name"].get(raw_path.name.lower())
    if name_hit is not None:
        return name_hit.resolve()

    stem_hits = image_index["stem"].get(raw_path.stem.lower(), [])
    if len(stem_hits) == 1:
        return stem_hits[0].resolve()
    if len(stem_hits) > 1:
        raise ValueError(f"Multiple images matched by stem for: {token}")

    raise FileNotFoundError(f"Unable to resolve image '{token}' under {image_dir}")


def _load_metadata_table(df_points: pd.DataFrame, image_dir: Path) -> pd.DataFrame:
    image_index = _build_image_index(image_dir)
    rows: List[Dict[str, Any]] = []
    non_rtk: List[str] = []

    for image_token in sorted(df_points["image"].astype(str).unique()):
        image_path = _resolve_image_path(image_token, image_dir, image_index)
        metadata = extract_dji_metadata_from_jpeg_bytes(image_path.read_bytes())

        lat = float(metadata.get("lat", 0.0) or 0.0)
        lon = float(metadata.get("lon", 0.0) or 0.0)
        alt = float(metadata.get("alt", 0.0) or 0.0)
        gps_status = str(metadata.get("gps_status", "")).strip().upper()
        rtk_flag = float(metadata.get("rtk_flag", 0.0) or 0.0)
        if abs(lat) < 1e-12 and abs(lon) < 1e-12 and abs(alt) < 1e-12 and not gps_status:
            raise ValueError(f"Missing DJI XMP metadata in image: {image_path}")
        if gps_status != "RTK":
            non_rtk.append(image_path.name)

        rows.append(
            {
                "image": image_token,
                "image_name": image_path.name,
                "image_path": str(image_path),
                "lat": lat,
                "lon": lon,
                "alt": alt,
                "gimbal_pitch": float(metadata.get("gimbal_pitch", 0.0) or 0.0),
                "gimbal_yaw": float(metadata.get("gimbal_yaw", 0.0) or 0.0),
                "gimbal_roll": float(metadata.get("gimbal_roll", 0.0) or 0.0),
                "gps_status": gps_status,
                "altitude_type": str(metadata.get("altitude_type", "") or ""),
                "rtk_flag": rtk_flag,
                "rtk_std_lon": float(metadata.get("rtk_std_lon", 0.0) or 0.0),
                "rtk_std_lat": float(metadata.get("rtk_std_lat", 0.0) or 0.0),
                "rtk_std_hgt": float(metadata.get("rtk_std_hgt", 0.0) or 0.0),
                "calibrated_focal_length": float(metadata.get("calibrated_focal_length", 0.0) or 0.0),
                "calibrated_optical_center_x": float(metadata.get("calibrated_optical_center_x", 0.0) or 0.0),
                "calibrated_optical_center_y": float(metadata.get("calibrated_optical_center_y", 0.0) or 0.0),
                "dewarp_data": str(metadata.get("dewarp_data", "") or ""),
            }
        )

    print(f"[INFO] Image directory: {image_dir}")
    print(f"[INFO] Unique images referenced by point CSV: {len(rows)}")
    print(f"[INFO] Images tagged as RTK in XMP: {len(rows) - len(non_rtk)}/{len(rows)}")
    if non_rtk:
        print(f"[WARN] Images not tagged as RTK in XMP: {', '.join(non_rtk)}")

    return pd.DataFrame(rows)


def _merge_points_with_image_metadata(df_points: pd.DataFrame, image_dir: Path) -> pd.DataFrame:
    metadata_df = _load_metadata_table(df_points, image_dir)
    df_xy = df_points.merge(metadata_df, on="image", how="left", validate="many_to_one")

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
    ]
    for col in numeric_cols:
        df_xy[col] = pd.to_numeric(df_xy[col], errors="coerce")

    before = len(df_xy)
    df_xy = df_xy.dropna(subset=numeric_cols).reset_index(drop=True)
    dropped = before - len(df_xy)
    if dropped > 0:
        print(f"[WARN] Dropped {dropped} invalid observations after metadata merge.")

    return df_xy


def _parse_pairs(raw_pairs: Sequence[str]) -> List[Tuple[int, int]]:
    out: List[Tuple[int, int]] = []
    for raw in raw_pairs:
        token = raw.strip().replace(",", "-")
        parts = [p.strip() for p in token.split("-") if p.strip()]
        if len(parts) != 2:
            raise ValueError(f"Invalid --pair value: {raw}. Use format like 1-2")
        a, b = int(parts[0]), int(parts[1])
        if a == b:
            raise ValueError(f"Invalid --pair value: {raw}. pair endpoints must be different")
        out.append((min(a, b), max(a, b)))
    return sorted(set(out))


def _unique_point_positions(df_out: pd.DataFrame) -> Dict[int, np.ndarray]:
    positions: Dict[int, np.ndarray] = {}
    for _, row in df_out.iterrows():
        kp_raw = pd.to_numeric(row.get("keypoint_id"), errors="coerce")
        pos = row.get("_3d_position")
        if pd.isna(kp_raw) or not isinstance(pos, (list, tuple)) or len(pos) != 3:
            continue
        kp = int(kp_raw)
        if kp not in positions:
            positions[kp] = np.asarray(pos, dtype=np.float64)
    return positions

def _print_3d_points(positions: Dict[int, np.ndarray]) -> None:
    print("\n=== Reconstructed 3D Points (ECEF) ===")
    if not positions:
        print("No valid 3D points reconstructed.")
        return
    print(f"{'keypoint_id':>11}  {'X':>16}  {'Y':>16}  {'Z':>16}")
    for kp in sorted(positions):
        x, y, z = positions[kp]
        print(f"{kp:>11d}  {x:>16.6f}  {y:>16.6f}  {z:>16.6f}")


def _distance(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.linalg.norm(a - b))


def _extract_true_length_hint(df_any: pd.DataFrame) -> float | None:
    if "true_length" not in df_any.columns:
        return None
    vals = pd.to_numeric(df_any["true_length"], errors="coerce").dropna()
    if vals.empty:
        return None
    return float(vals.mean())


def _print_distances(
    positions: Dict[int, np.ndarray],
    pairs: Sequence[Tuple[int, int]],
    true_length_hint: float | None,
) -> None:
    print("\n=== Point-to-Point Distances ===")
    if not pairs:
        print("No distance pairs available.")
        return

    print(f"{'pair':>12}  {'distance_m':>14}  {'delta_vs_true_m':>16}")
    for a, b in pairs:
        if a not in positions or b not in positions:
            print(f"{f'{a}-{b}':>12}  {'N/A':>14}  {'N/A':>16}")
            continue
        dist = _distance(positions[a], positions[b])
        delta = "N/A" if true_length_hint is None else f"{(dist - true_length_hint):.6f}"
        print(f"{f'{a}-{b}':>12}  {dist:>14.6f}  {delta:>16}")


def main() -> None:
    _print_leinao_mark()
    args = parse_args()

    if not args.points_csv.exists():
        raise FileNotFoundError(f"Point CSV not found: {args.points_csv}")

    df_raw = pd.read_csv(args.points_csv)
    if df_raw.empty:
        raise ValueError(f"Input CSV is empty: {args.points_csv}")

    intrinsics = _build_intrinsics(args)
    extrinsics = _build_extrinsics(args)
    camera_matrix, dist_coeffs, extr_cfg = build_camera_arrays(intrinsics, extrinsics)

    if _looks_like_legacy_observation_csv(df_raw):
        print("[INFO] Detected legacy observation CSV with embedded pose fields.")
        df_xy = _convert_legacy_observation_csv_to_observations(df_raw)
    else:
        df_points = _normalize_point_csv(df_raw)
        df_xy = _merge_points_with_image_metadata(df_points, args.image_dir)

    if df_xy.empty:
        raise ValueError("No valid observations available for triangulation.")

    min_views = int(df_xy.groupby("keypoint_id").size().min())
    print(f"[INFO] Point CSV: {args.points_csv}")
    print(f"[INFO] Camera model option: {args.camera_model}")
    print(f"[INFO] Observations: {len(df_xy)}; keypoints: {df_xy['keypoint_id'].nunique()}; min views/keypoint: {min_views}")

    df_out = triangulate_dataframe(df_xy, camera_matrix, dist_coeffs, extr_cfg)

    if args.output_csv is not None:
        args.output_csv.parent.mkdir(parents=True, exist_ok=True)
        df_out.to_csv(args.output_csv, index=False, encoding="utf-8")
        print(f"[INFO] Saved triangulation output: {args.output_csv}")

    positions = _unique_point_positions(df_out)
    _print_3d_points(positions)

    pairs = _parse_pairs(args.pair) if args.pair else list(combinations(sorted(positions.keys()), 2))
    true_length_hint = _extract_true_length_hint(df_xy)
    if true_length_hint is not None:
        print(f"\n[INFO] mean(true_length) from CSV: {true_length_hint:.6f} m")

    _print_distances(positions, pairs, true_length_hint=true_length_hint)


if __name__ == "__main__":
    main()
