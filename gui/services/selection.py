"""
Selection and destination helper functions for the GUI workflow.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QListWidget, QListWidgetItem


def get_destination_paths(
    selected_paths: list[Path],
    using_photo_source: bool,
    source_photo_path: Path | None,
) -> list[Path]:
    """
    Return selected files that should receive GPS updates.
    """
    if not using_photo_source or source_photo_path is None:
        return selected_paths

    return [path for path in selected_paths if path != source_photo_path]


def get_overwrite_entries(
    list_widget: QListWidget,
    target_paths: list[Path],
) -> list[str]:
    """
    Return destination files that already contain GPS and would be overwritten.
    """
    overwrite_entries: list[str] = []

    for index in range(list_widget.count()):
        item = list_widget.item(index)
        item_path = Path(item.data(Qt.UserRole))
        if item_path not in target_paths:
            continue

        latitude = item.data(Qt.UserRole + 1)
        longitude = item.data(Qt.UserRole + 2)
        if latitude is None or longitude is None:
            continue

        overwrite_entries.append(
            f"{item_path.name} — {latitude:.6f}, {longitude:.6f}"
        )

    return overwrite_entries


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
