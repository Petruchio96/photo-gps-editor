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
    path_list = list(paths)
    photo_infos_by_path: dict[Path, PhotoInfo] = {}
    paths_to_load: list[Path] = []

    for path in path_list:
        cached_info = cache.get(path) if cache is not None else None
        if cached_info is not None:
            photo_infos_by_path[path] = cached_info
            continue

        paths_to_load.append(path)

    loaded_infos = _load_uncached_photo_infos(paths_to_load, loader)
    for info in loaded_infos:
        if cache is not None:
            cache.set(info)
        photo_infos_by_path[info.path] = info

    return [photo_infos_by_path[path] for path in path_list]


def _load_uncached_photo_infos(paths: list[Path], loader) -> list[PhotoInfo]:
    if not paths:
        return []

    if hasattr(loader, "load_photo_infos"):
        return loader.load_photo_infos(paths)

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
