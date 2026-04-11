"""
Presenter helpers for source preview UI state.
"""

from __future__ import annotations

from dataclasses import dataclass

from services.models import WorkflowSession


@dataclass(frozen=True)
class SourcePreviewState:
    is_empty: bool
    filename_text: str
    gps_text: str
    has_gps: bool
    can_clear_source: bool


def build_source_preview_state(session: WorkflowSession) -> SourcePreviewState:
    """
    Build the derived state for the source preview card.
    """
    if session.source_photo_path is None:
        return SourcePreviewState(
            is_empty=True,
            filename_text="No source photo selected",
            gps_text="Source GPS: Not loaded",
            has_gps=False,
            can_clear_source=False,
        )

    source_info = session.source_photo_info
    has_gps = (
        source_info is not None
        and source_info.current_latitude is not None
        and source_info.current_longitude is not None
    )

    if has_gps:
        gps_text = (
            "Source GPS: "
            f"{source_info.current_latitude:.6f}, "
            f"{source_info.current_longitude:.6f}"
        )
    else:
        gps_text = "Source GPS: Not found in this photo"

    return SourcePreviewState(
        is_empty=False,
        filename_text=session.source_photo_path.name,
        gps_text=gps_text,
        has_gps=has_gps,
        can_clear_source=True,
    )
