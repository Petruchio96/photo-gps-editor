"""
Presenter for the inspector panel (the right side of the window).

Why this file exists:
    The inspector shows what is selected in the photo grid and what can be done
    with it. Working that out (labels, counts, which buttons are enabled, and
    why not) is plain logic, kept here without any Qt code so it is easy to
    test and can be reused by a future web interface.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from core.models import GpsCoordinates, PhotoInfo
from services.coordinate_service import parse_manual_coordinates


@dataclass(frozen=True)
class InspectorState:
    # Selection summary
    title: str
    selected_count: int
    gps_summary: str
    # Set only when exactly one photo is selected and it has GPS.
    single_photo_coordinates: GpsCoordinates | None
    can_use_location: bool

    # New location fields
    new_location: GpsCoordinates | None

    # Apply
    can_apply: bool
    apply_label: str
    # Shown above the Apply button: why it is disabled, or a heads-up.
    apply_hint: str
    apply_hint_tone: str
    overwrite_count: int

    # Remove GPS
    can_remove_gps: bool
    remove_gps_label: str
    remove_gps_count: int


def _photos(count: int) -> str:
    return f"{count} Photo" if count == 1 else f"{count} Photos"


def _gps_of(info: PhotoInfo | None) -> GpsCoordinates | None:
    if info is None or info.current_latitude is None or info.current_longitude is None:
        return None
    return GpsCoordinates(info.current_latitude, info.current_longitude)


def format_coordinates(coordinates: GpsCoordinates) -> str:
    return f"{coordinates.latitude:.6f}, {coordinates.longitude:.6f}"


def build_inspector_state(
    *,
    selected_paths: list[Path],
    photo_infos: Mapping[Path, PhotoInfo],
    latitude_text: str,
    longitude_text: str,
) -> InspectorState:
    """
    Work out everything the inspector panel shows for the current selection.

    Args:
        selected_paths:
            Photos selected in the grid. These are the photos Apply and
            Remove GPS act on.
        photo_infos:
            Loaded metadata for the photos, keyed by path.
        latitude_text / longitude_text:
            Contents of the New location fields.
    """
    count = len(selected_paths)
    gps_by_path = {path: _gps_of(photo_infos.get(path)) for path in selected_paths}
    with_gps = [path for path in selected_paths if gps_by_path[path] is not None]

    # Selection summary
    single_coordinates = None
    if count == 0:
        title = "No Photos Selected"
        gps_summary = "Select photos in the grid to see or change their GPS location."
    elif count == 1:
        title = selected_paths[0].name
        single_coordinates = gps_by_path[selected_paths[0]]
        gps_summary = (
            f"Current GPS: {format_coordinates(single_coordinates)}"
            if single_coordinates is not None
            else "Current GPS: none"
        )
    else:
        title = f"{count} Photos Selected"
        if not with_gps:
            gps_summary = "Current GPS: none of them have GPS"
        elif len(with_gps) == count:
            gps_summary = "Current GPS: all of them have GPS"
        else:
            gps_summary = f"Current GPS: {len(with_gps)} of {count} have GPS"

    # New location
    parsed = parse_manual_coordinates(latitude_text, longitude_text)
    new_location = GpsCoordinates(*parsed) if parsed is not None else None
    fields_empty = not latitude_text.strip() and not longitude_text.strip()

    # Apply
    can_apply = count > 0 and new_location is not None
    apply_label = f"Apply to {_photos(count)}" if count else "Apply to Selected Photos"
    overwrite_count = len(with_gps) if can_apply else 0
    if count == 0:
        apply_hint, apply_hint_tone = "Select the photos to update in the grid.", "info"
    elif new_location is None and fields_empty:
        apply_hint = "Enter a new location above, paste one, or use a photo's location."
        apply_hint_tone = "info"
    elif new_location is None:
        apply_hint = "The new location isn't valid. Check the latitude and longitude."
        apply_hint_tone = "error"
    elif overwrite_count:
        apply_hint = (
            f"{_photos(overwrite_count).lower()} already "
            f"{'has' if overwrite_count == 1 else 'have'} GPS, which will be replaced."
        )
        apply_hint_tone = "warning"
    else:
        apply_hint, apply_hint_tone = "", "info"

    # Remove GPS
    remove_count = len(with_gps)
    remove_label = (
        f"Remove GPS from {_photos(remove_count)}" if remove_count else "Remove GPS"
    )

    return InspectorState(
        title=title,
        selected_count=count,
        gps_summary=gps_summary,
        single_photo_coordinates=single_coordinates,
        can_use_location=single_coordinates is not None,
        new_location=new_location,
        can_apply=can_apply,
        apply_label=apply_label,
        apply_hint=apply_hint,
        apply_hint_tone=apply_hint_tone,
        overwrite_count=overwrite_count,
        can_remove_gps=remove_count > 0,
        remove_gps_label=remove_label,
        remove_gps_count=remove_count,
    )
