import hashlib
import importlib.util
import io
import tarfile
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

# Load packaging/fetch_exiftool.py by path. "packaging" is not a Python package
# here, and the name would clash with the third-party "packaging" library.
_SCRIPT_PATH = Path(__file__).resolve().parent.parent / "packaging" / "fetch_exiftool.py"
_spec = importlib.util.spec_from_file_location("fetch_exiftool", _SCRIPT_PATH)
fetch_exiftool = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fetch_exiftool)


def _windows_archive() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("exiftool-13.59_64/exiftool(-k).exe", b"exe")
        archive.writestr("exiftool-13.59_64/exiftool_files/perl.exe", b"perl")
        archive.writestr("exiftool-13.59_64/exiftool_files/lib/Image/ExifTool.pm", b"pm")
        archive.writestr("exiftool-13.59_64/README.txt", b"readme")
    return buffer.getvalue()


def _macos_archive() -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        for name, content in (
            ("Image-ExifTool-13.59/exiftool", b"#!/usr/bin/perl\n"),
            ("Image-ExifTool-13.59/lib/Image/ExifTool.pm", b"pm"),
            ("Image-ExifTool-13.59/t/ExifTool.t", b"test"),
        ):
            info = tarfile.TarInfo(name)
            info.size = len(content)
            archive.addfile(info, io.BytesIO(content))
    return buffer.getvalue()


class FetchExifToolTests(unittest.TestCase):
    def test_install_windows_copies_exe_and_exiftool_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            destination = Path(temp_dir)
            fetch_exiftool.install_windows(_windows_archive(), destination)

            self.assertEqual((destination / "exiftool.exe").read_bytes(), b"exe")
            self.assertEqual(
                (destination / "exiftool_files" / "perl.exe").read_bytes(),
                b"perl",
            )
            self.assertTrue(
                (destination / "exiftool_files" / "lib" / "Image" / "ExifTool.pm").exists()
            )
            self.assertFalse((destination / "README.txt").exists())

    def test_install_macos_copies_script_and_lib(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            destination = Path(temp_dir)
            fetch_exiftool.install_macos(_macos_archive(), destination)

            script = destination / "exiftool"
            self.assertEqual(script.read_bytes(), b"#!/usr/bin/perl\n")
            self.assertTrue((destination / "lib" / "Image" / "ExifTool.pm").exists())
            self.assertFalse((destination / "t").exists())

    def test_unsafe_archive_paths_are_rejected(self) -> None:
        with self.assertRaises(SystemExit):
            fetch_exiftool.safe_relative_path("../outside.txt")

    def test_download_rejects_checksum_mismatch(self) -> None:
        class FakeResponse(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        with patch.object(
            fetch_exiftool.urllib.request,
            "urlopen",
            return_value=FakeResponse(b"not the real archive"),
        ):
            with self.assertRaisesRegex(SystemExit, "Checksum mismatch"):
                fetch_exiftool.download("exiftool.zip", hashlib.sha256(b"real").hexdigest())


if __name__ == "__main__":
    unittest.main()
