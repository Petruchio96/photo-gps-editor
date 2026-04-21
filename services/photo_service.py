"""
Services for loading photo models for frontend workflows.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from core.models import PhotoInfo
from services.photo_metadata_cache import PhotoMetadataCache
from services.models import WorkflowSession


def load_selected_photo_infos(
    paths: Iterable[Path],
    loader,
    cache: PhotoMetadataCache | None = None,
) -> list[PhotoInfo]:
    """
    Load photo models for the current selected-photo workspace.
    """
    photo_infos: list[PhotoInfo] = []

    for path in paths:
        cached_info = cache.get(path) if cache is not None else None
        if cached_info is not None:
            photo_infos.append(cached_info)
            continue

        info = loader.load_photo_info(path)
        if cache is not None:
            cache.set(info)
        photo_infos.append(info)

    return photo_infos


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


def refresh_photo_session(
    selected_paths: Iterable[Path],
    loader,
    cache: PhotoMetadataCache | None = None,
) -> WorkflowSession:
    """
    Build the selected-photo session state from the current selected paths.
    """
    selected_path_list = list(selected_paths)
    loaded_photos = load_selected_photo_infos(selected_path_list, loader, cache)
    return WorkflowSession(
        selected_paths=selected_path_list,
        loaded_photos=loaded_photos,
        loaded_photo_infos=index_photo_infos(loaded_photos),
    )
