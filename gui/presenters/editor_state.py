"""
Presenter helpers for editor/detail panel UI state.
"""

from __future__ import annotations

from dataclasses import dataclass

from services.destination_service import get_destination_paths
from services.models import WorkflowSession
from services.source_service import resolve_active_source


@dataclass(frozen=True)
class EditorPanelState:
    source_summary: str
    destination_names: list[str]
    can_clear_source: bool
    can_apply: bool


def build_editor_panel_state(
    *,
    session: WorkflowSession,
    selected_paths,
    using_photo_source: bool,
    latitude_text: str,
    longitude_text: str,
) -> EditorPanelState:
    """
    Build the derived UI state for the editor panel from workflow/session inputs.
    """
    target_paths = get_destination_paths(
        list(selected_paths),
        using_photo_source,
        session.source_photo_path,
    )
    source_resolution = resolve_active_source(
        using_photo_source=using_photo_source,
        source_photo_info=session.source_photo_info,
        latitude_text=latitude_text,
        longitude_text=longitude_text,
    )

    if using_photo_source:
        if session.source_photo_path is None:
            source_summary = "Coordinates to Apply: Not set"
        elif source_resolution.coordinates is None:
            source_summary = "Coordinates to Apply: Source photo has no GPS"
        else:
            source_summary = (
                "Coordinates to Apply: "
                f"{source_resolution.coordinates.latitude:.6f}, "
                f"{source_resolution.coordinates.longitude:.6f}"
            )
    elif source_resolution.coordinates is None:
        source_summary = "Coordinates to Apply: Not set"
    else:
        source_summary = (
            "Coordinates to Apply: "
            f"{source_resolution.coordinates.latitude:.6f}, "
            f"{source_resolution.coordinates.longitude:.6f}"
        )

    return EditorPanelState(
        source_summary=source_summary,
        destination_names=[path.name for path in target_paths],
        can_clear_source=session.source_photo_path is not None,
        can_apply=bool(target_paths) and source_resolution.coordinates is not None,
    )
