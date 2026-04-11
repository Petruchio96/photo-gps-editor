"""
Selection and destination helper functions for the GUI workflow.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QListWidgetItem


def can_set_source_from_items(
    selected_items: list[QListWidgetItem],
    source_photo_path: Path | None,
) -> bool:
    """
    Return True when the current selection can become the locked photo source.
    """
    if len(selected_items) != 1:
        return False

    selected_item = selected_items[0]
    selected_path = Path(selected_item.data(Qt.UserRole))
    latitude = selected_item.data(Qt.UserRole + 1)
    longitude = selected_item.data(Qt.UserRole + 2)

    return (
        latitude is not None
        and longitude is not None
        and selected_path != source_photo_path
    )
