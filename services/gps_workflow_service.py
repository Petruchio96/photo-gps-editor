"""
Use-case services for applying GPS coordinates to target files.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from core.models import PhotoInfo
from services.target_paths_service import get_overwrite_entries, get_target_paths
from services.models import ApplyExecutionResult, ApplyPreparation, SourceResolution


def prepare_apply_gps(
    *,
    selected_paths: list[Path],
    using_photo_source: bool,
    source_photo_path: Path | None,
    source_resolution: SourceResolution,
    photo_info_by_path: Mapping[Path, PhotoInfo],
) -> ApplyPreparation:
    """
    Validate the current workflow state before attempting to write metadata.
    """
    target_paths = get_target_paths(
        selected_paths,
        using_photo_source,
        source_photo_path,
    )

    if not target_paths:
        return ApplyPreparation(
            target_paths=[],
            error_message="Select one or more photos before applying GPS.",
        )

    if source_resolution.coordinates is None:
        return ApplyPreparation(
            target_paths=target_paths,
            error_message=source_resolution.error_message,
        )

    return ApplyPreparation(
        target_paths=target_paths,
        overwrite_entries=get_overwrite_entries(photo_info_by_path, target_paths),
        coordinates=source_resolution.coordinates,
    )


def apply_gps_to_paths(
    target_paths: list[Path],
    *,
    latitude: float,
    longitude: float,
    writer,
) -> ApplyExecutionResult:
    """
    Write GPS metadata to each target path and collect failures.
    """
    success_count = 0
    successful_paths: list[Path] = []
    failed_paths: list[str] = []

    for path in target_paths:
        try:
            writer.write_gps(path, latitude, longitude)
            success_count += 1
            successful_paths.append(path)
        except Exception as exc:
            failed_paths.append(f"{path.name}: {exc}")

    return ApplyExecutionResult(
        success_count=success_count,
        successful_paths=successful_paths,
        failed_paths=failed_paths,
    )
