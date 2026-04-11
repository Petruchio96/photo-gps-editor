"""
Services for loading photo models for frontend workflows.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from core.models import PhotoInfo
from services.models import WorkflowSession


def load_destination_photo_infos(paths: Iterable[Path], loader) -> list[PhotoInfo]:
    """
    Load photo models for the current destination workspace.
    """
    return [loader.load_photo_info(path) for path in paths]


def index_photo_infos(photo_infos: Iterable[PhotoInfo]) -> dict[Path, PhotoInfo]:
    """
    Build a path-keyed lookup table for already loaded photo models.
    """
    return {info.path: info for info in photo_infos}


def load_source_photo_info(path: Path, loader) -> PhotoInfo:
    """
    Load the chosen source photo into the shared backend photo model.
    """
    return loader.load_photo_info(path)


def refresh_destination_session(
    selected_paths: Iterable[Path],
    loader,
) -> WorkflowSession:
    """
    Build the destination-related session state from the current selected paths.
    """
    selected_path_list = list(selected_paths)
    loaded_photos = load_destination_photo_infos(selected_path_list, loader)
    return WorkflowSession(
        selected_paths=selected_path_list,
        loaded_photos=loaded_photos,
        loaded_photo_infos=index_photo_infos(loaded_photos),
    )
