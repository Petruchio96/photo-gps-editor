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


@dataclass(frozen=True)
class EmbeddedPreview:
    """
    A JPEG preview stored inside a RAW file, used for thumbnails.

    jpeg_bytes:
        The preview image, stored unrotated.
    orientation:
        EXIF orientation of the photo, 1-8 (1 = upright). Apply it to the
        preview for display.
    image_width / image_height:
        Size of the full photo before rotation, if known. Some cameras pad
        small previews with black bars (Canon CR3 thumbnails are 4:3 while the
        photo is 3:2); cropping the preview to this shape removes them.
    """

    jpeg_bytes: bytes
    orientation: int = 1
    image_width: int | None = None
    image_height: int | None = None

