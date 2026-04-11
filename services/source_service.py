"""
Workflow helpers for resolving GPS source coordinates.
"""

from __future__ import annotations

from core.models import GpsCoordinates, PhotoInfo
from services.coordinate_service import parse_manual_coordinates
from services.models import SourceResolution


def resolve_photo_source(photo_info: PhotoInfo | None) -> SourceResolution:
    """
    Resolve coordinates from a chosen source photo.
    """
    if photo_info is None:
        return SourceResolution(
            coordinates=None,
            error_message="Choose a source photo with GPS coordinates before applying.",
        )

    if photo_info.gps_error:
        return SourceResolution(
            coordinates=None,
            error_message="Choose a source photo with GPS coordinates before applying.",
        )

    if photo_info.current_latitude is None or photo_info.current_longitude is None:
        return SourceResolution(
            coordinates=None,
            error_message="Choose a source photo with GPS coordinates before applying.",
        )

    return SourceResolution(
        coordinates=GpsCoordinates(
            latitude=photo_info.current_latitude,
            longitude=photo_info.current_longitude,
        )
    )


def resolve_manual_source(
    latitude_text: str,
    longitude_text: str,
) -> SourceResolution:
    """
    Resolve coordinates from manual text entry.
    """
    coordinates = parse_manual_coordinates(latitude_text, longitude_text)
    if coordinates is None:
        return SourceResolution(
            coordinates=None,
            error_message="Enter valid latitude and longitude values before applying.",
        )

    return SourceResolution(
        coordinates=GpsCoordinates(
            latitude=coordinates[0],
            longitude=coordinates[1],
        )
    )


def resolve_active_source(
    *,
    using_photo_source: bool,
    source_photo_info: PhotoInfo | None,
    latitude_text: str,
    longitude_text: str,
) -> SourceResolution:
    """
    Resolve the active source mode into coordinates usable by apply workflows.
    """
    if using_photo_source:
        return resolve_photo_source(source_photo_info)

    return resolve_manual_source(latitude_text, longitude_text)
