import unittest
from pathlib import Path

from core.file_types import (
    SUPPORTED_EXTENSIONS,
    file_dialog_patterns,
    is_raw_file,
    is_supported_file,
)


class SupportedFileTypeTests(unittest.TestCase):
    def test_supported_extensions_are_case_insensitive(self) -> None:
        self.assertTrue(is_supported_file(Path("image.JPG")))
        self.assertTrue(is_supported_file(Path("image.cr3")))
        self.assertTrue(is_supported_file(Path("image.DNG")))

    def test_unsupported_extensions_are_rejected(self) -> None:
        self.assertFalse(is_supported_file(Path("image.png")))
        self.assertFalse(is_supported_file(Path("image")))

    def test_raw_files_are_recognized(self) -> None:
        self.assertTrue(is_raw_file(Path("image.CR2")))
        self.assertTrue(is_raw_file(Path("image.dng")))
        self.assertFalse(is_raw_file(Path("image.jpg")))

    def test_file_dialog_patterns_cover_every_supported_extension_in_both_cases(self) -> None:
        patterns = file_dialog_patterns().split()

        for extension in SUPPORTED_EXTENSIONS:
            self.assertIn(f"*{extension}", patterns)
            self.assertIn(f"*{extension.upper()}", patterns)


if __name__ == "__main__":
    unittest.main()
