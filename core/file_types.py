from pathlib import Path

# Single source of truth for which files the app can open. The file picker's
# filter is built from these too, so the two lists cannot drift apart.
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


def file_dialog_patterns() -> str:
    """
    Space-separated wildcard patterns for a file picker, such as "*.jpg *.JPG".

    Both cases are listed because file pickers on Linux match case-sensitively.
    """
    patterns: list[str] = []
    for extension in sorted(SUPPORTED_EXTENSIONS):
        patterns.append(f"*{extension}")
        patterns.append(f"*{extension.upper()}")
    return " ".join(patterns)
