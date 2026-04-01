"""
Helpers for parsing coordinate text entered or pasted into the GUI.
"""

from __future__ import annotations

import re

from core.coordinates import validate_coordinates


def parse_coordinate_text(text: str) -> tuple[str, str] | None:
    """
    Parse a combined coordinate string into separate latitude and longitude
    strings for the two input fields.
    """
    parts = re.findall(r"[+-]?\d+(?:\.\d+)?", text)

    if len(parts) != 2:
        return None

    try:
        float(parts[0])
        float(parts[1])
    except ValueError:
        return None

    return parts[0], parts[1]


def parse_manual_coordinates(
    latitude_text: str,
    longitude_text: str,
) -> tuple[float, float] | None:
    """
    Parse and validate manual latitude and longitude field values.
    """
    latitude_text = latitude_text.strip()
    longitude_text = longitude_text.strip()

    if not latitude_text or not longitude_text:
        return None

    try:
        latitude, longitude = validate_coordinates(latitude_text, longitude_text)
    except ValueError:
        return None

    return latitude, longitude
