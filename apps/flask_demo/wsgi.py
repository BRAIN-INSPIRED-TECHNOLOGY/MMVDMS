# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Copyright contributors to the Leinao project
import sys
from pathlib import Path

LEINAO_CODE_MARK = "[leinao]"


def _ensure_local_src_path() -> None:
    """Allow gunicorn/app imports from source checkout without editable install."""
    root = Path(__file__).resolve().parents[2]
    src_dir = root / "src"
    if src_dir.exists() and str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))


_ensure_local_src_path()

from .app import create_app

app = create_app()
