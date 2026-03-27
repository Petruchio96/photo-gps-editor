"""
Load photo information from disk and convert it into our application's model objects.

Why this file exists:
    The ExifTool wrapper gives us raw GPS data in a simple dictionary format.
    The rest of the application should not have to know how ExifTool works.

    This module acts as a bridge between:
    1. a file on disk
    2. the ExifTool metadata reader
    3. the PhotoInfo dataclass used by the app

This keeps responsibilities clean:
    exiftool_wrapper.py -> talks to ExifTool
    photo_loader.py     -> builds PhotoInfo objects
"""

from __future__ import annotations

from pathlib import Path

from core.exiftool_wrapper import ExifToolWrapper
from core.file_types import is_supported_file
from core.models import PhotoInfo


class PhotoLoader:
    """
    Load metadata for a single photo and return it in our app's data model.

    This class hides the details of:
    1. checking supported file types
    2. calling the ExifTool wrapper
    3. handling missing GPS data
    4. handling read errors
    """

    def __init__(self, exiftool: ExifToolWrapper) -> None:
        """
        Store a reference to the ExifTool wrapper.

        Args:
            exiftool:
                An ExifToolWrapper instance used to read GPS metadata.
        """
        self.exiftool = exiftool

    def load_photo_info(self, path: Path) -> PhotoInfo:
        """
        Load one photo and convert its metadata into a PhotoInfo object.

        Args:
            path:
                Path to the photo file.

        Returns:
            A PhotoInfo object containing file type, GPS data, and any error
            message if something goes wrong.
        """
        info = PhotoInfo(
            path=path,
            file_type=path.suffix.upper().lstrip("."),
        )

        if not is_supported_file(path):
            info.gps_error = "Unsupported file type."
            return info

        try:
            gps_data = self.exiftool.read_gps(path)
            info.current_latitude = gps_data.get("latitude")
            info.current_longitude = gps_data.get("longitude")
        except Exception as exc:
            info.gps_error = str(exc)

        return info