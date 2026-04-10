import unittest
from pathlib import Path

from core.file_types import is_supported_file


class SupportedFileTypeTests(unittest.TestCase):
    def test_supported_extensions_are_case_insensitive(self) -> None:
        self.assertTrue(is_supported_file(Path("image.JPG")))
        self.assertTrue(is_supported_file(Path("image.cr3")))
        self.assertTrue(is_supported_file(Path("image.DNG")))

    def test_unsupported_extensions_are_rejected(self) -> None:
        self.assertFalse(is_supported_file(Path("image.png")))
        self.assertFalse(is_supported_file(Path("image")))


if __name__ == "__main__":
    unittest.main()
