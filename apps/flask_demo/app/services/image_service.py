# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Copyright contributors to the Leinao project
from ..models.image_model import get_image_bytes, list_saved_images, save_images


def save_uploaded_images(files):
    return save_images(files)


def list_images():
    return list_saved_images()


def fetch_image_bytes(image_id: str):
    return get_image_bytes(image_id)
