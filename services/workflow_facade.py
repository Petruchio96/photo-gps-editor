"""
Single backend workflow entry point for frontend code.
"""

from __future__ import annotations

from pathlib import Path

from core.exiftool_wrapper import ExifToolWrapper
from core.photo_loader import PhotoLoader
from services.models import (
    ApplyPreparation,
    ApplyWorkflowResult,
    SourceLoadResult,
    WorkflowMessage,
    WorkflowSession,
)
from services.photo_metadata_cache import PhotoMetadataCache
from services.workflow_controller import (
    clear_source_workflow,
    execute_apply_workflow,
    load_source_workflow,
    prepare_apply_workflow,
    refresh_photo_workflow,
    restore_gps_states_workflow,
)


class PhotoWorkflowFacade:
    """
    Backend workflow API used by the desktop frontend.
    """

    def __init__(self, loader=None, writer=None, metadata_cache=None) -> None:
        self.writer = writer or ExifToolWrapper()
        self.loader = loader or PhotoLoader(self.writer)
        self.metadata_cache = metadata_cache or PhotoMetadataCache()

    def refresh_photo_workflow(self, session: WorkflowSession) -> WorkflowSession:
        return refresh_photo_workflow(session, self.loader, self.metadata_cache)

    def load_source_workflow(
        self,
        session: WorkflowSession,
        source_path: Path,
    ) -> SourceLoadResult:
        return load_source_workflow(session, source_path, self.loader)

    def clear_source_workflow(self, session: WorkflowSession) -> WorkflowMessage:
        return clear_source_workflow(session)

    def prepare_apply_workflow(
        self,
        *,
        session: WorkflowSession,
        selected_paths: list[Path],
        using_photo_source: bool,
        latitude_text: str,
        longitude_text: str,
    ) -> ApplyPreparation:
        return prepare_apply_workflow(
            session=session,
            selected_paths=selected_paths,
            using_photo_source=using_photo_source,
            latitude_text=latitude_text,
            longitude_text=longitude_text,
        )

    def execute_apply_workflow(
        self,
        *,
        session: WorkflowSession,
        preparation: ApplyPreparation,
    ) -> ApplyWorkflowResult:
        return execute_apply_workflow(
            session=session,
            preparation=preparation,
            writer=self.writer,
            loader=self.loader,
            cache=self.metadata_cache,
        )

    def restore_gps_states_workflow(
        self,
        *,
        session: WorkflowSession,
        states: dict[Path, tuple[float | None, float | None]],
    ) -> WorkflowSession:
        return restore_gps_states_workflow(
            session=session,
            states=states,
            writer=self.writer,
            loader=self.loader,
            cache=self.metadata_cache,
        )
