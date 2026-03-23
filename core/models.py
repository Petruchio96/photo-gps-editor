from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class GpsCoordinates:
    latitude: float
    longitude: float


@dataclass
class PhotoInfo:
    path: Path
    file_type: str
    current_latitude: Optional[float] = None
    current_longitude: Optional[float] = None
    gps_error: Optional[str] = None


@dataclass
class WriteResult:
    path: Path
    success: bool
    message: str