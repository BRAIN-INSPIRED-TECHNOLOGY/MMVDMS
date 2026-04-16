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

from mvtriangulation.calibration import ZhangIntrinsicsConfig, calibrate_from_image_pattern

LEINAO_CODE_MARK = "[leinao]"


def _print_leinao_mark() -> None:
    print(f"{LEINAO_CODE_MARK} intrinsics calibration starting")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Zhang camera intrinsics calibration from chessboard images.")
    parser.add_argument("--images", required=True, help="Image glob pattern, e.g. data/calib/*.jpg")
    parser.add_argument("--board-cols", type=int, required=True, help="Inner corners per chessboard row")
    parser.add_argument("--board-rows", type=int, required=True, help="Inner corners per chessboard column")
    parser.add_argument("--square-size", type=float, default=1.0, help="Chessboard square size in meters")
    parser.add_argument("--out", required=True, help="Output intrinsics JSON path")
    parser.add_argument("--disable-sb", action="store_true", help="Disable findChessboardCornersSB")
    return parser.parse_args()


def main() -> None:
    _print_leinao_mark()
    args = parse_args()

    cfg = ZhangIntrinsicsConfig(
        board_cols=args.board_cols,
        board_rows=args.board_rows,
        square_size=args.square_size,
        use_findchessboard_sb=not args.disable_sb,
    )

    result = calibrate_from_image_pattern(
        image_pattern=args.images,
        config=cfg,
        output_path=args.out,
    )

    print("[INFO] Saved intrinsics JSON:")
    print(json.dumps(result["params"], ensure_ascii=False, indent=2))

    print("\n[INFO] Calibration metrics:")
    print(json.dumps(result["metrics"], ensure_ascii=False, indent=2))

    print("\n[INFO] Used images:", len(result["used_images"]))
    print("[INFO] Rejected images:", len(result["rejected_images"]))


if __name__ == "__main__":
    main()
