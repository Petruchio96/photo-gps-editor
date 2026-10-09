"""
Run Python's garbage collector only on the GUI thread, at a safe moment.

Why this file exists:
    Python's automatic garbage collection can start in any thread, at almost
    any line of code. When it frees leftover Qt objects at the wrong moment
    (from the background thread, or in the middle of Qt delivering an event)
    Qt aborts the whole app. The Windows build crashed this way while the
    photo picker was open.

    Turning automatic collection off and collecting from a timer on the GUI
    thread, between events, is a common safeguard for PySide apps. Memory is
    still freed: ordinary objects are freed immediately as always, and only
    leftover reference loops wait for the timer.
"""

from __future__ import annotations

import gc

from PySide6.QtCore import QObject, QTimer

# How often to check whether a collection is due (milliseconds).
CHECK_INTERVAL_MS = 500


class GuiThreadGarbageCollector(QObject):
    """
    Create once, on the GUI thread, after the QApplication. Keep a reference
    to it for the app's lifetime.
    """

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._thresholds = gc.get_threshold()
        gc.disable()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.check)
        self._timer.start(CHECK_INTERVAL_MS)

    def check(self) -> None:
        """
        Collect the generations that have grown past their usual thresholds,
        the same rule Python follows when collection is automatic.
        """
        counts = gc.get_count()
        if counts[0] <= self._thresholds[0]:
            return
        generation = 0
        if counts[1] > self._thresholds[1]:
            generation = 1
            if counts[2] > self._thresholds[2]:
                generation = 2
        gc.collect(generation)
