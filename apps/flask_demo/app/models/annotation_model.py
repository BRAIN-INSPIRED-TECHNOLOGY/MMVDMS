# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Copyright contributors to the Leinao project
from typing import Any, Dict, List

from .memory_store import STORE


def load_annotation(image_id: str) -> Dict[str, Any]:
    return STORE.get_annotation(image_id)


def save_annotation(image_id: str, points: List[Dict[str, Any]], meta: Dict[str, Any]) -> Dict[str, Any]:
    return STORE.save_annotation(image_id, points, meta)


def list_all_annotations():
    yield from STORE.iter_all_annotations()
