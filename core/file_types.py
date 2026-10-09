from pathlib import Path

# Single source of truth for which files the app can open (the Add Photos
# picker lists only these).
JPEG_EXTENSIONS = {
    ".jpg",
    ".jpeg",
}

RAW_EXTENSIONS = {
    ".cr2",
    ".cr3",
    ".dng",
}

SUPPORTED_EXTENSIONS = JPEG_EXTENSIONS | RAW_EXTENSIONS


def is_supported_file(path: Path) -> bool:
    return path.suffix.lower() in SUPPORTED_EXTENSIONS


def is_raw_file(path: Path) -> bool:
    return path.suffix.lower() in RAW_EXTENSIONS

