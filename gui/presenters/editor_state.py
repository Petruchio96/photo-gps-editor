"""
Presenter helpers for editor/detail panel UI state.
"""

from __future__ import annotations

from dataclasses import dataclass

from services.target_paths_service import get_target_paths
from services.models import WorkflowSession
from services.source_service import resolve_active_source


@dataclass(frozen=True)
class EditorPanelState:
    source_summary: str
    selected_photo_names: list[str]
    selected_photo_count: int
    selected_gps_count: int
    can_add_selected_photos: bool
    can_remove_selected_photos: bool
    can_clear_list_gps: bool
    can_clear_source: bool
    can_apply: bool
    apply_tone: str


def build_editor_panel_state(
    *,
    session: WorkflowSession,
    browser_selected_paths,
    target_selected_paths,
    using_photo_source: bool,
    latitude_text: str,
    longitude_text: str,
) -> EditorPanelState:
    """
    Build the derived UI state for the editor panel from workflow/session inputs.
    """
    target_paths = get_target_paths(
        list(session.target_paths),
        using_photo_source,
        session.source_photo_path,
    )
    staged_path_set = set(session.target_paths)
    can_add_selected_photos = any(
        path not in staged_path_set for path in browser_selected_paths
    )
    has_selected_targets = bool(target_paths)
    selected_gps_count = sum(
        1
        for path in target_paths
        if (
            info := session.loaded_photo_infos.get(path)
        ) is not None
        and info.current_latitude is not None
        and info.current_longitude is not None
    )
    any_target_has_gps = any(
        (
            info := session.loaded_photo_infos.get(path)
        ) is not None
        and info.current_latitude is not None
        and info.current_longitude is not None
        for path in target_paths
    )
    source_resolution = resolve_active_source(
        using_photo_source=using_photo_source,
        source_photo_info=session.source_photo_info,
        latitude_text=latitude_text,
        longitude_text=longitude_text,
    )

    if using_photo_source:
        if session.source_photo_path is None:
            source_summary = "Source GPS Coordinates: Not set"
        elif source_resolution.coordinates is None:
            source_summary = "Source GPS Coordinates: Source photo has no GPS"
        else:
            source_summary = (
                "Source GPS Coordinates: "
                f"{source_resolution.coordinates.latitude:.6f}, "
                f"{source_resolution.coordinates.longitude:.6f}"
            )
    elif source_resolution.coordinates is None:
        source_summary = "Source GPS Coordinates: Not set"
    else:
        source_summary = (
            "Source GPS Coordinates: "
            f"{source_resolution.coordinates.latitude:.6f}, "
            f"{source_resolution.coordinates.longitude:.6f}"
        )

    return EditorPanelState(
        source_summary=source_summary,
        selected_photo_names=[path.name for path in target_paths],
        selected_photo_count=len(target_paths),
        selected_gps_count=selected_gps_count,
        can_add_selected_photos=can_add_selected_photos,
        can_remove_selected_photos=bool(target_selected_paths),
        can_clear_list_gps=selected_gps_count > 0,
        can_clear_source=session.source_photo_path is not None,
        can_apply=has_selected_targets and source_resolution.coordinates is not None,
        apply_tone="warning" if any_target_has_gps else "safe",
    )
