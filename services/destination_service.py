"""
Workflow helpers for determining destination files and overwrite warnings.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from core.models import GpsCoordinates, PhotoInfo
from services.models import OverwriteEntry


def get_destination_paths(
    selected_paths: list[Path],
    using_photo_source: bool,
    source_photo_path: Path | None,
) -> list[Path]:
    """
    Return selected files that should receive GPS updates.
    """
    if not using_photo_source or source_photo_path is None:
        return selected_paths

    return [path for path in selected_paths if path != source_photo_path]


def get_overwrite_entries(
    photo_info_by_path: Mapping[Path, PhotoInfo],
    target_paths: list[Path],
) -> list[OverwriteEntry]:
    """
    Return destination files that already contain GPS and would be overwritten.
    """
    overwrite_entries: list[OverwriteEntry] = []

    for path in target_paths:
        info = photo_info_by_path.get(path)
        if info is None:
            continue

        if info.current_latitude is None or info.current_longitude is None:
            continue

        overwrite_entries.append(
            OverwriteEntry(
                path=path,
                coordinates=GpsCoordinates(
                    latitude=info.current_latitude,
                    longitude=info.current_longitude,
                ),
            )
        )

    return overwrite_entries
