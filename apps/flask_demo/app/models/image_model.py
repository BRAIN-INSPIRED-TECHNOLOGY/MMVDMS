# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Copyright contributors to the Leinao project
from typing import Any, Dict, List, Optional, Tuple

from .memory_store import STORE


def save_images(files) -> List[Dict[str, Any]]:
    saved = []
    for file_obj in files:
        if not file_obj or not file_obj.filename:
            continue
        data = file_obj.read()
        mime = getattr(file_obj, "mimetype", None) or "application/octet-stream"
        saved.append(STORE.add_image(filename=file_obj.filename, mime=mime, data=data))
    return saved


def list_saved_images() -> List[Dict[str, Any]]:
    return STORE.list_images()


def get_image_bytes(image_id: str) -> Optional[Tuple[bytes, str]]:
    return STORE.get_image_bytes(image_id)
