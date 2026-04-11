"""
Compatibility re-exports for GUI callers during the service split.
"""

from services.coordinate_service import (
    parse_coordinate_text,
    parse_latitude_text,
    parse_longitude_text,
    parse_manual_coordinates,
)
