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

from core.runtime_paths import default_exiftool_executable

# On Windows, a GUI app that starts a console program flashes a console window
# unless told not to. CREATE_NO_WINDOW only exists on Windows; 0 is a no-op
# value for creationflags on other platforms.
_NO_WINDOW_FLAGS = getattr(subprocess, "CREATE_NO_WINDOW", 0)


class ExifToolWrapper:
    """
    Small helper class for interacting with the external 'exiftool' program.

    This class keeps command construction and subprocess handling in one place,
    which makes the rest of the application simpler and easier to test.
    """

    def __init__(self, executable: str | None = None) -> None:
        """
        Store the executable name or path.

        Args:
            executable:
                The command name or full path to ExifTool.
                Usually just "exiftool" if it is installed in PATH.
        """
        self.executable = executable or default_exiftool_executable()

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
        output = self._run(
            ["-json", "-n", "-GPSLatitude", "-GPSLongitude"],
            [path],
            "Failed to read metadata.",
        )
        data = json.loads(output)

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

    def read_gps_many(self, paths: list[Path]) -> dict[Path, dict]:
        """
        Read GPS metadata for many files with one ExifTool invocation.
        """
        if not paths:
            return {}

        output = self._run(
            ["-json", "-n", "-GPSLatitude", "-GPSLongitude"],
            paths,
            "Failed to read metadata.",
        )
        records = json.loads(output)
        gps_by_path: dict[Path, dict] = {}

        for record in records:
            source_file = record.get("SourceFile")
            if source_file is None:
                continue

            gps_by_path[Path(source_file)] = {
                "latitude": record.get("GPSLatitude"),
                "longitude": record.get("GPSLongitude"),
            }

        return gps_by_path

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

        self._run(
            [
                "-overwrite_original",
                f"-GPSLatitude={abs(latitude)}",
                f"-GPSLatitudeRef={latitude_ref}",
                f"-GPSLongitude={abs(longitude)}",
                f"-GPSLongitudeRef={longitude_ref}",
            ],
            [path],
            "Failed to write metadata.",
        )

    def clear_gps(self, path: Path) -> None:
        """
        Remove GPS metadata from a file using ExifTool.
        """
        self._run(
            [
                "-overwrite_original",
                "-GPSLatitude=",
                "-GPSLatitudeRef=",
                "-GPSLongitude=",
                "-GPSLongitudeRef=",
            ],
            [path],
            "Failed to clear metadata.",
        )

    def _run(self, options: list[str], paths: list[Path], failure_message: str) -> str:
        """
        Run ExifTool with the given options on the given files.

        Why file paths go through stdin instead of the command line:
            On Windows, command-line arguments are limited to the system code
            page, so some file names (for example Japanese or emoji characters)
            cannot be passed correctly. ExifTool's recommended fix is to list
            the files in a UTF-8 argument file ("-@ -" reads it from stdin) and
            set "-charset filename=utf8". This works the same on every platform.

        Args:
            options:
                ExifTool options to use, such as ["-json", "-n"].
            paths:
                Files to process. These should be absolute paths, because
                ExifTool argument files ignore lines starting with "#" and
                strip leading spaces.
            failure_message:
                Error text used when ExifTool fails without printing a reason.

        Returns:
            ExifTool's standard output as text.

        Raises:
            RuntimeError:
                If ExifTool returns a non-zero exit code.
        """
        command = [
            self.executable,
            "-charset",
            "filename=utf8",
            *options,
            "-@",
            "-",
        ]

        result = subprocess.run(
            command,
            input="".join(f"{path}\n" for path in paths),
            capture_output=True,
            text=True,
            # ExifTool writes UTF-8; do not rely on the OS default encoding,
            # which is Windows-1252 on many Windows systems.
            encoding="utf-8",
            errors="replace",
            check=False,
            creationflags=_NO_WINDOW_FLAGS,
        )

        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or failure_message)

        return result.stdout
