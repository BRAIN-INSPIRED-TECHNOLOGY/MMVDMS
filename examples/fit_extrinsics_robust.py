# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Copyright contributors to the Leinao project
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from mvtriangulation.calibration import ExtrinsicFitConfig, calibrate_and_save

LEINAO_CODE_MARK = "[leinao]"


def _print_leinao_mark() -> None:
    print(f"{LEINAO_CODE_MARK} extrinsics calibration starting")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fit camera extrinsics and save 6-field JSON output.")
    parser.add_argument("--intrinsics", required=True, help="Path to camera intrinsics JSON")
    parser.add_argument("--fit-csv", required=True, help="Path to fit CSV")
    parser.add_argument("--out", required=True, help="Path to output extrinsics JSON")
    parser.add_argument("--test-csv", default=None, help="Optional path to test CSV for validation")

    parser.add_argument("--with-xyz-offset", action="store_true", help="Fit dX/dY/dZ together")
    parser.add_argument("--yaw-bound", type=float, default=30.0, help="Yaw offset bound in degrees")
    parser.add_argument("--pitch-bound", type=float, default=30.0, help="Pitch offset bound in degrees")
    parser.add_argument("--roll-bound", type=float, default=30.0, help="Roll offset bound in degrees")
    parser.add_argument("--xyz-bound", type=float, default=20.0, help="dX/dY/dZ bound in meters")
    parser.add_argument(
        "--loss",
        default="soft_l1",
        choices=["linear", "soft_l1", "huber", "cauchy", "arctan"],
        help="Robust loss for least squares",
    )
    parser.add_argument("--f-scale", type=float, default=2.0, help="Scale parameter for robust loss")
    parser.add_argument("--max-nfev", type=int, default=500, help="Maximum solver evaluations")
    return parser.parse_args()


def main() -> None:
    _print_leinao_mark()
    args = parse_args()

    config = ExtrinsicFitConfig(
        use_xyz_offset=args.with_xyz_offset,
        yaw_bound_deg=args.yaw_bound,
        pitch_bound_deg=args.pitch_bound,
        roll_bound_deg=args.roll_bound,
        xyz_bound_m=args.xyz_bound,
        loss=args.loss,
        f_scale=args.f_scale,
        max_nfev=args.max_nfev,
    )

    result = calibrate_and_save(
        intrinsics_path=args.intrinsics,
        fit_csv=args.fit_csv,
        output_path=args.out,
        config=config,
        test_csv=args.test_csv,
    )

    print("[INFO] Saved extrinsics JSON:")
    print(json.dumps(result["params"], ensure_ascii=False, indent=2))

    metrics = result.get("metrics")
    if metrics:
        print("\n[INFO] Validation metrics:")
        print(json.dumps(metrics, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
