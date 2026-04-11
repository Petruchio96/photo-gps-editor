from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from core.models import GpsCoordinates, PhotoInfo


@dataclass(frozen=True)
class SourceResolution:
    coordinates: GpsCoordinates | None
    error_message: str | None = None


@dataclass(frozen=True)
class OverwriteEntry:
    path: Path
    coordinates: GpsCoordinates

    def display_text(self) -> str:
        return (
            f"{self.path.name} — "
            f"{self.coordinates.latitude:.6f}, {self.coordinates.longitude:.6f}"
        )


@dataclass(frozen=True)
class ApplyPreparation:
    target_paths: list[Path]
    overwrite_entries: list[OverwriteEntry] = field(default_factory=list)
    coordinates: GpsCoordinates | None = None
    error_message: str | None = None


@dataclass(frozen=True)
class ApplyExecutionResult:
    success_count: int
    failed_paths: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class WorkflowMessage:
    text: str
    tone: str = "info"


@dataclass(frozen=True)
class ThumbnailItemData:
    path: Path
    filename: str
    has_gps: bool
    latitude: float | None
    longitude: float | None
    tooltip: str


@dataclass
class WorkflowSession:
    selected_paths: list[Path] = field(default_factory=list)
    loaded_photos: list[PhotoInfo] = field(default_factory=list)
    thumbnail_items: list[ThumbnailItemData] = field(default_factory=list)
    loaded_photo_infos: dict[Path, PhotoInfo] = field(default_factory=dict)
    source_photo_info: PhotoInfo | None = None
    source_photo_path: Path | None = None


@dataclass(frozen=True)
class SourceLoadResult:
    session: WorkflowSession
    message: WorkflowMessage


@dataclass(frozen=True)
class ApplyWorkflowResult:
    session: WorkflowSession
    execution_result: ApplyExecutionResult
