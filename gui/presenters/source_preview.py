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
            has_gps=False,
            can_clear_source=False,
        )

    source_info = session.source_photo_info
    has_gps = (
        source_info is not None
        and source_info.current_latitude is not None
        and source_info.current_longitude is not None
    )

    return SourcePreviewState(
        is_empty=False,
        filename_text=session.source_photo_path.name,
        has_gps=has_gps,
        can_clear_source=True,
    )
