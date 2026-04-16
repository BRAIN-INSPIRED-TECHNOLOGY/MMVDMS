# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Copyright contributors to the Leinao project
import sys
from pathlib import Path


def _ensure_local_src_path() -> None:
    root = Path(__file__).resolve().parents[2]
    src_dir = root / "src"
    if src_dir.exists() and str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))


_ensure_local_src_path()

from .app import create_app

__all__ = ["create_app"]
