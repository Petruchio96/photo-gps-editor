import gc
import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from gui.gc_guard import GuiThreadGarbageCollector


class GuiThreadGarbageCollectorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        was_enabled = gc.isenabled()
        self.addCleanup(lambda: gc.enable() if was_enabled else None)

    def test_turns_off_automatic_collection(self) -> None:
        collector = GuiThreadGarbageCollector()
        self.addCleanup(collector.deleteLater)

        self.assertFalse(gc.isenabled())

    def test_collects_reference_loops_when_checked(self) -> None:
        collector = GuiThreadGarbageCollector()
        self.addCleanup(collector.deleteLater)
        freed = []

        class Node:
            def __del__(self) -> None:
                freed.append(True)

        for _ in range(gc.get_threshold()[0] + 10):
            node = Node()
            node.loop = node
        del node

        collector.check()

        self.assertTrue(freed)


if __name__ == "__main__":
    unittest.main()
