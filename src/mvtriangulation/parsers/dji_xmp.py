# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Copyright contributors to the Leinao project
import xml.etree.ElementTree as et
from typing import Any, Dict

DJI_NS = "http://www.dji.com/drone-dji/1.0/"
RDF_NS = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"


def _empty_payload() -> Dict[str, Any]:
    return {
        "lat": 0.0,
        "lon": 0.0,
        "alt": 0.0,
        "gimbal_pitch": 0.0,
        "gimbal_yaw": 0.0,
        "gimbal_roll": 0.0,
        "gps_status": "",
        "altitude_type": "",
        "rtk_flag": 0.0,
        "rtk_std_lon": 0.0,
        "rtk_std_lat": 0.0,
        "rtk_std_hgt": 0.0,
        "calibrated_focal_length": 0.0,
        "calibrated_optical_center_x": 0.0,
        "calibrated_optical_center_y": 0.0,
        "dewarp_data": "",
    }


def extract_dji_metadata_from_jpeg_bytes(content: bytes) -> Dict[str, Any]:
    xmp_start = content.find(b"<x:xmpmeta")
    xmp_end = content.find(b"</x:xmpmeta>")
    if xmp_start == -1 or xmp_end == -1:
        return _empty_payload()

    xmp_str = content[xmp_start : xmp_end + len(b"</x:xmpmeta>")].decode("utf-8", errors="ignore")
    try:
        root = et.fromstring(xmp_str)
    except et.ParseError:
        return _empty_payload()

    desc = root.find(f".//{{{RDF_NS}}}Description")
    if desc is None:
        for element in root.iter():
            if isinstance(element.tag, str) and element.tag.endswith("Description"):
                desc = element
                break

    if desc is None:
        return _empty_payload()

    def get_float(attr_name: str) -> float:
        try:
            value = str(desc.attrib.get(attr_name, "0")).replace("+", "")
            return float(value)
        except Exception:
            return 0.0

    def get_text(attr_name: str) -> str:
        try:
            return str(desc.attrib.get(attr_name, "")).strip()
        except Exception:
            return ""

    return {
        "lat": get_float(f"{{{DJI_NS}}}GpsLatitude"),
        "lon": get_float(f"{{{DJI_NS}}}GpsLongitude"),
        "alt": get_float(f"{{{DJI_NS}}}AbsoluteAltitude"),
        "gimbal_pitch": get_float(f"{{{DJI_NS}}}GimbalPitchDegree"),
        "gimbal_yaw": get_float(f"{{{DJI_NS}}}GimbalYawDegree"),
        "gimbal_roll": get_float(f"{{{DJI_NS}}}GimbalRollDegree"),
        "gps_status": get_text(f"{{{DJI_NS}}}GpsStatus"),
        "altitude_type": get_text(f"{{{DJI_NS}}}AltitudeType"),
        "rtk_flag": get_float(f"{{{DJI_NS}}}RtkFlag"),
        "rtk_std_lon": get_float(f"{{{DJI_NS}}}RtkStdLon"),
        "rtk_std_lat": get_float(f"{{{DJI_NS}}}RtkStdLat"),
        "rtk_std_hgt": get_float(f"{{{DJI_NS}}}RtkStdHgt"),
        "calibrated_focal_length": get_float(f"{{{DJI_NS}}}CalibratedFocalLength"),
        "calibrated_optical_center_x": get_float(f"{{{DJI_NS}}}CalibratedOpticalCenterX"),
        "calibrated_optical_center_y": get_float(f"{{{DJI_NS}}}CalibratedOpticalCenterY"),
        "dewarp_data": get_text(f"{{{DJI_NS}}}DewarpData"),
    }
