"""
Helpers for thumbnail list item presentation and selection restore.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QListWidget


def build_tooltip_text(
    filename: str,
    latitude: float | None,
    longitude: float | None,
) -> str:
    """
    Build hover tooltip text for a thumbnail item.
    """
    if latitude is not None and longitude is not None:
        return f"{filename}\nGPS: {latitude:.6f}, {longitude:.6f}"

    return f"{filename}\nNo GPS"


def reselect_paths(
    list_widget: QListWidget,
    paths_to_select: list[Path],
) -> None:
    """
    Re-select items in the thumbnail grid after the list has been rebuilt.
    """
    wanted = {str(path) for path in paths_to_select}

    for index in range(list_widget.count()):
        item = list_widget.item(index)
        item_path = item.data(Qt.UserRole)

        if item_path in wanted:
            item.setSelected(True)
