"""
Wrapper around ExifTool for reading and writing GPS metadata.

Why this file exists:
    We do not want GUI code directly calling subprocess commands all over the
    project. This wrapper gives us one clean place to:
    1. check whether ExifTool exists
    2. read GPS metadata from files
    3. later, write GPS metadata back to files

Why ExifTool:
    ExifTool is the most reliable way to work with metadata across JPG and many
    RAW formats like CR2, CR3, and DNG.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path


class ExifToolWrapper:
    """
    Small helper class for interacting with the external 'exiftool' program.

    This class keeps command construction and subprocess handling in one place,
    which makes the rest of the application simpler and easier to test.
    """

    def __init__(self, executable: str = "exiftool") -> None:
        """
        Store the executable name or path.

        Args:
            executable:
                The command name or full path to ExifTool.
                Usually just "exiftool" if it is installed in PATH.
        """
        self.executable = executable

    def is_available(self) -> bool:
        """
        Check whether ExifTool can be found on the system PATH.

        Returns:
            True if ExifTool is available, otherwise False.
        """
        return shutil.which(self.executable) is not None

    def read_gps(self, path: Path) -> dict:
        """
        Read GPS metadata from a file using ExifTool and return it in a cleaner form.

        Why we use "-n":
            By default, ExifTool may return GPS values as nicely formatted text
            like:
                40 deg 29' 10.77" N
            That is fine for humans, but not ideal for a program.

            The "-n" option tells ExifTool to return raw numeric values instead,
            which are much easier for our application to use. For example:
                40.486325
                -111.813414

        Args:
            path:
                Path to the image file we want to inspect.

        Returns:
            A dictionary with these keys:
                "latitude": float | None
                "longitude": float | None

            If the image has no GPS data, the values will be None.

        Raises:
            RuntimeError:
                If ExifTool fails, such as when the file cannot be read.
        """
        command = [
            self.executable,
            "-json",
            "-n",
            "-GPSLatitude",
            "-GPSLongitude",
            str(path),
        ]

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "Failed to read metadata.")

        data = json.loads(result.stdout)

        if not data:
            return {
                "latitude": None,
                "longitude": None,
            }

        record = data[0]

        return {
            "latitude": record.get("GPSLatitude"),
            "longitude": record.get("GPSLongitude"),
        }

    def write_gps(self, path: Path, latitude: float, longitude: float) -> None:
        """
        Write GPS metadata to a file using ExifTool.

        Why we set latitude/longitude references explicitly:
            GPS metadata is commonly stored as a positive numeric value plus a
            directional reference:
                latitude  -> N or S
                longitude -> E or W

            This keeps the metadata explicit and avoids ambiguity.

        Args:
            path:
                Path to the image file to update.
            latitude:
                Decimal latitude value.
            longitude:
                Decimal longitude value.

        Raises:
            RuntimeError:
                If ExifTool fails to write the metadata.
        """
        latitude_ref = "N" if latitude >= 0 else "S"
        longitude_ref = "E" if longitude >= 0 else "W"

        command = [
            self.executable,
            "-overwrite_original",
            f"-GPSLatitude={abs(latitude)}",
            f"-GPSLatitudeRef={latitude_ref}",
            f"-GPSLongitude={abs(longitude)}",
            f"-GPSLongitudeRef={longitude_ref}",
            str(path),
        ]

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "Failed to write metadata.")