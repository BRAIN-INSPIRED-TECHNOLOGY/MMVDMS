# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Copyright contributors to the Leinao project
import io

from flask import Blueprint, Response, abort, jsonify, render_template, request, send_file

from ..models.memory_store import STORE
from ..services.annotation_service import (
    build_all_csv_bytes,
    build_xanything_zip_bytes,
    build_image_json_bytes,
    get_annotations,
    save_annotations,
)
from ..services.compute3d_service import compute_3d_dataframe
from ..services.image_service import fetch_image_bytes, list_images, save_uploaded_images

image_bp = Blueprint("image", __name__)


@image_bp.route("/")
def index():
    return render_template("index.html")


@image_bp.route("/api/images/upload", methods=["POST"])
def upload_images():
    files = request.files.getlist("images")
    if not files:
        return jsonify({"images": [], "error": "no files (field name must be 'images')"}), 400
    items = save_uploaded_images(files)
    return jsonify({"images": items})


@image_bp.route("/api/images/list", methods=["GET"])
def api_list_images():
    return jsonify({"images": list_images()})


@image_bp.route("/api/images/<image_id>/content", methods=["GET"])
def api_image_content(image_id):
    got = fetch_image_bytes(image_id)
    if not got:
        abort(404)
    data, mime = got
    return Response(data, mimetype=mime)


@image_bp.route("/api/annotations/<image_id>", methods=["GET"])
def api_get_annotations(image_id):
    return jsonify(get_annotations(image_id))


@image_bp.route("/api/annotations/<image_id>", methods=["POST"])
def api_save_annotations(image_id):
    payload = request.get_json(force=True) or {}
    points = payload.get("points", [])
    meta = payload.get("meta", {})
    save_annotations(image_id, points, meta)
    return jsonify({"ok": True})


@image_bp.route("/api/annotations/<image_id>/export_json", methods=["GET"])
def api_export_json(image_id):
    content = build_image_json_bytes(image_id)
    return send_file(
        io.BytesIO(content),
        mimetype="application/json; charset=utf-8",
        as_attachment=True,
        download_name=f"{image_id}.json",
    )


@image_bp.route("/api/export/csv", methods=["GET"])
def api_export_csv():
    content = build_all_csv_bytes()
    return send_file(
        io.BytesIO(content),
        mimetype="text/csv; charset=utf-8",
        as_attachment=True,
        download_name="keypoints.csv",
    )


@image_bp.route("/api/export/json", methods=["GET"])
def api_export_json_batch():
    content = build_xanything_zip_bytes()
    return send_file(
        io.BytesIO(content),
        mimetype="application/zip",
        as_attachment=True,
        download_name="xanything_labels.zip",
    )


@image_bp.route("/api/camera/params", methods=["GET"])
def api_get_camera_params():
    return jsonify(STORE.get_camera_params())


@image_bp.route("/api/camera/intrinsics", methods=["POST"])
def api_set_intrinsics():
    payload = request.get_json(force=True) or {}
    STORE.set_intrinsics(payload)
    return jsonify({"ok": True, "intrinsics": STORE.get_camera_params()["intrinsics"]})


@image_bp.route("/api/camera/extrinsics", methods=["POST"])
def api_set_extrinsics():
    payload = request.get_json(force=True) or {}
    STORE.set_extrinsics(payload)
    return jsonify({"ok": True, "extrinsics": STORE.get_camera_params()["extrinsics"]})


@image_bp.route("/api/camera/reset", methods=["POST"])
def api_reset_camera():
    STORE.reset_camera_params()
    return jsonify({"ok": True, **STORE.get_camera_params()})


@image_bp.route("/api/compute/3d", methods=["POST"])
def api_compute_3d():
    df = compute_3d_dataframe()
    return jsonify({"columns": df.columns.tolist(), "rows": df.to_dict(orient="records")})


@image_bp.route("/api/images/clear", methods=["POST"])
def api_clear_images():
    STORE.clear_all(reset_camera=False)
    return jsonify({"ok": True})
