"""
Session-only undo/redo memory for GPS edits.
"""

from __future__ import annotations

from pathlib import Path

# GPS state of one file: (latitude, longitude), or (None, None) for no GPS.
type GpsState = tuple[float | None, float | None]


class GpsEditHistory:
    """
    Remember the most recent GPS apply or clear so it can be undone and redone.

    This is single-step: recording a new edit replaces the previous one. The
    history lives in memory only and is never written to disk.
    """

    def __init__(self) -> None:
        self._before: dict[Path, GpsState] = {}
        self._after: dict[Path, GpsState] = {}
        self._undone = False

    def record(
        self,
        *,
        before: dict[Path, GpsState],
        after: dict[Path, GpsState],
    ) -> None:
        """
        Remember an edit. Only files present in both mappings are kept, so
        files that failed to update are never "restored" by undo.
        """
        paths = [path for path in after if path in before]
        self._before = {path: before[path] for path in paths}
        self._after = {path: after[path] for path in paths}
        self._undone = False

    def clear(self) -> None:
        self._before = {}
        self._after = {}
        self._undone = False

    @property
    def can_undo(self) -> bool:
        return bool(self._before) and not self._undone

    @property
    def can_redo(self) -> bool:
        return bool(self._after) and self._undone

    def undo_states(self) -> dict[Path, GpsState]:
        """
        GPS states to write to undo the edit. Empty if there is nothing to undo.
        """
        return dict(self._before) if self.can_undo else {}

    def redo_states(self) -> dict[Path, GpsState]:
        """
        GPS states to write to redo the edit. Empty if there is nothing to redo.
        """
        return dict(self._after) if self.can_redo else {}

    def mark_undone(self) -> None:
        self._undone = True

    def mark_redone(self) -> None:
        self._undone = False
