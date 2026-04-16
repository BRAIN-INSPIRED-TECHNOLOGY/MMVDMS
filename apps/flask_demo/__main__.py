# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Copyright contributors to the Leinao project
import sys
from pathlib import Path


def _ensure_local_src_path() -> None:
    """Allow running demo from source checkout without editable install."""
    root = Path(__file__).resolve().parents[2]
    src_dir = root / "src"
    if src_dir.exists() and str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))


_ensure_local_src_path()

from .app import create_app

app = create_app()

def main() -> None:
    import os
    host = os.environ.get("FLASK_HOST", "0.0.0.0")
    port = int(os.environ.get("FLASK_PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "False").lower() == "true"

    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    main()
