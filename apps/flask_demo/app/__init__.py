# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Copyright contributors to the Leinao project
import os
import sys

from flask import Flask, jsonify
from werkzeug.exceptions import RequestEntityTooLarge

from .models.memory_store import STORE, normalize_camera_model


def _camera_model_from_argv() -> str | None:
    args = sys.argv[1:]
    for idx, token in enumerate(args):
        if token.startswith("--camera-model="):
            return token.split("=", 1)[1]
        if token == "--camera-model" and idx + 1 < len(args):
            return args[idx + 1]
    return None


def create_app(camera_model: str | None = None):
    app = Flask(__name__, static_url_path="/static")
    app.config["MAX_CONTENT_LENGTH"] = 500 * 1024 * 1024

    selected_model = (
        camera_model
        or _camera_model_from_argv()
        or os.environ.get("FLASK_CAMERA_MODEL")
        or "m3e"
    )
    model = normalize_camera_model(selected_model)
    STORE.set_default_camera_model(model, apply_now=True)
    app.config["CAMERA_MODEL"] = model

    @app.errorhandler(RequestEntityTooLarge)
    def handle_413(_error):
        max_mb = app.config["MAX_CONTENT_LENGTH"] // (1024 * 1024)
        return jsonify({"error": "uploaded content too large", "max_mb": max_mb}), 413

    from .routes.image import image_bp

    app.register_blueprint(image_bp)
    return app
