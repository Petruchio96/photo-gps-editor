"""
Background loading, placeholders, and the progress row, using a real
background thread and deliberately slow fake loaders.
"""

import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QColor, QIcon, QImage, QPixmap
from PySide6.QtWidgets import QApplication, QLabel

from core.models import PhotoInfo
from gui.background import BackgroundRunner
from gui.main_window import MainWindow
from gui.widgets import loading_indicator as loading_indicator_module
from gui.widgets.loading_indicator import LoadingIndicator
from gui.widgets.thumbnail_delegate import SHIMMER_ROLE
from gui.window_mixins.photo_list import THUMBNAIL_PATH_ROLE
from services.workflow_facade import PhotoWorkflowFacade


def wait_until(predicate, timeout: float = 5.0) -> bool:
    """Run the Qt event loop until predicate() is true or time runs out."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        QApplication.processEvents()
        if predicate():
            return True
        time.sleep(0.01)
    QApplication.processEvents()
    return predicate()


def run_events_for(seconds: float, check=None) -> None:
    """Run the event loop for a while, calling check() each step."""
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        QApplication.processEvents()
        if check is not None:
            check()
        time.sleep(0.01)


class SlowThumbnailLoader:
    """Builds solid-color thumbnails, sleeping `delay` seconds per batch."""

    def __init__(self, delay: float) -> None:
        self.delay = delay
        self.batches: list[list[Path]] = []
        self.threads: set[str] = set()
        self._icons: dict[tuple[str, bool], QIcon] = {}
        self.fallback = QIcon(QPixmap(8, 8))

    def cached_icon(self, path: Path, has_gps: bool = False):
        return self._icons.get((str(path), has_gps))

    def load_images(self, paths: list[Path]) -> dict:
        self.threads.add(threading.current_thread().name)
        self.batches.append(list(paths))
        time.sleep(self.delay)
        images = {}
        for path in paths:
            image = QImage(12, 8, QImage.Format_RGB32)
            image.fill(QColor("green"))
            images[path] = image
        return images

    def icon_from_image(self, path: Path, has_gps: bool, image) -> QIcon:
        icon = QIcon(QPixmap.fromImage(image))
        self._icons[(str(path), has_gps)] = icon
        return icon

    def fallback_icon_for(self, has_gps: bool) -> QIcon:
        return self.fallback

    def load_icon(self, path: Path, has_gps: bool = False) -> QIcon:
        return self.cached_icon(path, has_gps) or self.fallback


class FakePhotoLoader:
    """Returns photos without GPS, optionally slowly."""

    def __init__(self, delay: float = 0.0) -> None:
        self.delay = delay

    def load_photo_info(self, path: Path) -> PhotoInfo:
        time.sleep(self.delay)
        return PhotoInfo(path=path, file_type="JPG")


class FakeWriter:
    keep_backups = False


class BackgroundLoadingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        settings_dir = tempfile.TemporaryDirectory()
        self.addCleanup(settings_dir.cleanup)
        settings = QSettings(str(Path(settings_dir.name) / "s.ini"), QSettings.IniFormat)

        self.window = MainWindow(settings=settings)
        self.addCleanup(self.window.close)
        self.loader = FakePhotoLoader()
        self.window.workflow = PhotoWorkflowFacade(loader=self.loader, writer=FakeWriter())
        self.window.thumbnail_batch_size = 2
        self.window.show()

        self.paths = [Path(f"/tmp/photo-{index}.jpg") for index in range(8)]

    def _use_thumbnails(self, delay: float) -> SlowThumbnailLoader:
        loader = SlowThumbnailLoader(delay)
        self.window.thumbnail_loader = loader
        return loader

    def _photo_items(self) -> list:
        grid = self.window.list_widget
        return [
            grid.item(row)
            for row in range(grid.count())
            if grid.item(row).data(THUMBNAIL_PATH_ROLE) is not None
        ]

    def _grid_paths(self) -> list[str]:
        return [item.data(THUMBNAIL_PATH_ROLE) for item in self._photo_items()]

    def _loading_done(self) -> bool:
        return not self.window._pending_thumbnail_items

    def test_fast_load_shows_no_progress_or_placeholders(self) -> None:
        self._use_thumbnails(delay=0.0)
        seen = {"progress": False, "shimmer": False}

        def check() -> None:
            seen["progress"] |= self.window.loading_indicator.is_showing
            seen["shimmer"] |= any(item.data(SHIMMER_ROLE) for item in self._photo_items())

        self.window.session.selected_paths = list(self.paths)
        self.window.populate_list()
        self.assertTrue(wait_until(self._loading_done))
        # Stay past both delays to make sure nothing appears late.
        run_events_for(0.8, check)

        self.assertFalse(seen["progress"])
        self.assertFalse(seen["shimmer"])

    def test_slow_load_shows_placeholders_then_progress_then_hides(self) -> None:
        loader = self._use_thumbnails(delay=0.25)

        self.window.session.selected_paths = list(self.paths)
        self.window.populate_list()

        # Thumbnails are built on the background thread, not the GUI thread.
        self.assertTrue(
            wait_until(lambda: any(item.data(SHIMMER_ROLE) for item in self._photo_items()))
        )
        self.assertTrue(self.window._shimmer_timer.isActive())
        self.assertTrue(wait_until(lambda: self.window.loading_indicator.is_showing))

        self.assertTrue(wait_until(self._loading_done))
        self.assertFalse(self.window._shimmer_timer.isActive())
        self.assertFalse(any(item.data(SHIMMER_ROLE) for item in self._photo_items()))
        self.assertTrue(wait_until(lambda: not self.window.loading_indicator.is_showing))
        self.assertEqual(len(loader.batches), 4)
        self.assertNotIn(threading.main_thread().name, loader.threads)

    def test_choose_photos_reads_gps_in_background_and_keeps_update_list(self) -> None:
        self._use_thumbnails(delay=0.0)
        old_paths = self.paths[:2]
        self.window.session.selected_paths = list(old_paths)
        self.window.populate_list()
        self.assertTrue(wait_until(self._loading_done))
        self.window.session.target_paths = [old_paths[0]]

        self.loader.delay = 0.05
        self.window.load_photos(self.paths[2:6])

        # The old grid stays in place until the new GPS data is ready.
        self.assertEqual(self._grid_paths(), [str(path) for path in old_paths])

        self.assertTrue(
            wait_until(lambda: self.window.session.selected_paths == self.paths[2:6])
        )
        self.assertEqual(self.window.session.target_paths, [old_paths[0]])
        self.assertTrue(wait_until(self._loading_done))
        self.assertEqual(self._grid_paths(), [str(path) for path in self.paths[2:6]])

    def test_new_load_replaces_a_slow_earlier_load(self) -> None:
        self._use_thumbnails(delay=0.2)
        self.window.session.selected_paths = list(self.paths)
        self.window.populate_list()

        newer = [Path("/tmp/newer-1.jpg"), Path("/tmp/newer-2.jpg")]
        self.window.load_photos(newer)

        self.assertTrue(wait_until(lambda: self.window.session.selected_paths == newer))
        self.assertTrue(wait_until(self._loading_done))
        run_events_for(0.5)
        self.assertEqual(self._grid_paths(), [str(path) for path in newer])
        self.assertTrue(all(not item.icon().isNull() for item in self._photo_items()))

    def test_cancel_gives_plain_icons_and_hides_progress(self) -> None:
        loader = self._use_thumbnails(delay=0.3)
        self.window.session.selected_paths = list(self.paths)
        self.window.populate_list()
        self.assertTrue(wait_until(lambda: self.window.loading_indicator.is_showing))

        self.window.loading_indicator.cancel_button.click()

        self.assertTrue(self._loading_done())
        self.assertFalse(any(item.data(SHIMMER_ROLE) for item in self._photo_items()))
        fallback_key = loader.fallback.cacheKey()
        self.assertTrue(
            any(item.icon().cacheKey() == fallback_key for item in self._photo_items())
        )
        self.assertTrue(wait_until(lambda: not self.window.loading_indicator.is_showing))
        # The job stops early instead of building every remaining batch.
        run_events_for(0.5)
        self.assertLess(len(loader.batches), 4)

    def test_closing_during_load_is_safe(self) -> None:
        errors = []
        original_hook = sys.excepthook
        sys.excepthook = lambda *exc_info: errors.append(exc_info)
        self.addCleanup(setattr, sys, "excepthook", original_hook)

        self._use_thumbnails(delay=0.2)
        self.window.session.selected_paths = list(self.paths)
        self.window.populate_list()
        self.window.close()
        run_events_for(0.8)

        self.assertEqual(errors, [])
        self.assertTrue(self._loading_done())


# A stand-in app that closes while the background thread is busy with Qt image
# work, then exits. Before BackgroundRunner.shutdown() existed, this crashed
# (segmentation fault) about half the time as Qt shut down under the thread.
EXIT_DURING_LOAD_SCRIPT = """
import os, sys, tempfile, time
from pathlib import Path
sys.path.insert(0, os.getcwd())
os.environ["QT_QPA_PLATFORM"] = "offscreen"
from PySide6.QtCore import QBuffer, QSettings, QSize
from PySide6.QtGui import QColor, QImage, QImageReader
from PySide6.QtWidgets import QApplication
app = QApplication([])
from core.models import PhotoInfo
from gui.main_window import MainWindow
from services.workflow_facade import PhotoWorkflowFacade

class BusyQtLoader:
    def cached_icon(self, path, has_gps=False):
        return None
    def load_images(self, paths):
        # Decode JPEGs in a loop, like the real loader, for long enough that
        # it is still running when the app exits. JPEG decoding goes through
        # Qt's image plugin, which Qt unloads while shutting down.
        source = QImage(1600, 1200, QImage.Format_RGB32)
        source.fill(QColor("red"))
        encoded = QBuffer()
        encoded.open(QBuffer.WriteOnly)
        source.save(encoded, "JPEG")
        data = encoded.data()
        image = source
        deadline = time.monotonic() + 1.5
        while time.monotonic() < deadline:
            buffer = QBuffer()
            buffer.setData(data)
            buffer.open(QBuffer.ReadOnly)
            reader = QImageReader(buffer)
            reader.setScaledSize(QSize(128, 96))
            image = reader.read()
        return {path: image for path in paths}
    def icon_from_image(self, path, has_gps, image):
        from PySide6.QtGui import QIcon, QPixmap
        return QIcon(QPixmap.fromImage(image))
    def fallback_icon_for(self, has_gps):
        from PySide6.QtGui import QIcon
        return QIcon()

class Loader:
    def load_photo_info(self, path):
        return PhotoInfo(path=path, file_type="JPG")

class Writer:
    keep_backups = False

settings_file = Path(tempfile.mkdtemp()) / "s.ini"
window = MainWindow(settings=QSettings(str(settings_file), QSettings.IniFormat))
window.workflow = PhotoWorkflowFacade(loader=Loader(), writer=Writer())
window.thumbnail_loader = BusyQtLoader()
window.thumbnail_batch_size = 2
window.show()
window.session.selected_paths = [Path(f"/tmp/p{i}.jpg") for i in range(20)]
window.populate_list()
start = time.monotonic()
while time.monotonic() - start < 0.3:
    app.processEvents()
    time.sleep(0.01)
window.close()
"""


class ExitDuringLoadTests(unittest.TestCase):
    def test_closing_mid_load_then_exiting_does_not_crash(self) -> None:
        project_root = Path(__file__).resolve().parent.parent
        # Without the fix this crashed in about 3 of 8 runs, so 6 attempts catch
        # a regression about 94% of the time.
        for attempt in range(6):
            result = subprocess.run(
                [sys.executable, "-c", EXIT_DURING_LOAD_SCRIPT],
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=60,
            )
            with self.subTest(attempt=attempt):
                self.assertEqual(result.returncode, 0, result.stderr[-2000:])


class BackgroundRunnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_results_and_errors_arrive_on_the_gui_thread(self) -> None:
        runner = BackgroundRunner()
        received = []

        def fail():
            raise RuntimeError("boom")

        runner.submit(lambda: threading.current_thread().name, lambda name: received.append(("done", name, threading.current_thread() is threading.main_thread())))
        runner.submit(fail, lambda _: None, lambda exc: received.append(("error", str(exc), threading.current_thread() is threading.main_thread())))

        self.assertTrue(wait_until(lambda: len(received) == 2))
        done, error = received
        self.assertEqual(done[0], "done")
        self.assertNotEqual(done[1], threading.main_thread().name)
        self.assertTrue(done[2])
        self.assertEqual(error, ("error", "boom", True))

    def test_shutdown_waits_for_running_job_and_drops_queued_ones(self) -> None:
        runner = BackgroundRunner()
        ran = []

        def slow_job():
            time.sleep(0.3)
            ran.append("slow")

        runner.submit(slow_job, lambda _: None)
        runner.submit(lambda: ran.append("queued"), lambda _: None)
        time.sleep(0.05)

        self.assertTrue(runner.shutdown(timeout=5))
        self.assertEqual(ran, ["slow"])
        time.sleep(0.1)
        self.assertEqual(ran, ["slow"])

        # Nothing runs after shutdown.
        runner.submit(lambda: ran.append("late"), lambda _: None)
        time.sleep(0.1)
        self.assertEqual(ran, ["slow"])

    def test_inline_mode_runs_immediately(self) -> None:
        runner = BackgroundRunner()
        runner.run_inline = True
        received = []

        runner.submit(lambda: 42, received.append)

        self.assertEqual(received, [42])


class LoadingIndicatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.indicator = LoadingIndicator(QLabel("hint"))
        self.indicator.show()

    def test_quick_work_never_shows(self) -> None:
        self.indicator.begin("Working…")
        run_events_for(0.1)
        self.indicator.finish()
        run_events_for(loading_indicator_module.SHOW_DELAY_MS / 1000 + 0.3)

        self.assertFalse(self.indicator.is_showing)
        self.assertIs(self.indicator.currentWidget(), self.indicator.hint_label)

    def test_slow_work_shows_then_stays_for_minimum_then_hides(self) -> None:
        self.indicator.begin("Working…", total=10)
        self.assertTrue(wait_until(lambda: self.indicator.is_showing, timeout=2))
        self.assertIs(self.indicator.currentWidget(), self.indicator.progress_row)

        self.indicator.finish()
        # Still visible right after finishing: it stays for the minimum time.
        run_events_for(0.1)
        self.assertTrue(self.indicator.is_showing)

        self.assertTrue(wait_until(lambda: not self.indicator.is_showing, timeout=3))
        self.assertIs(self.indicator.currentWidget(), self.indicator.hint_label)

    def test_progress_updates_bar_and_text(self) -> None:
        self.indicator.begin("Loading thumbnails… 0 of 4", total=4)
        self.indicator.set_progress(3, 4, "Loading thumbnails… 3 of 4")

        self.assertEqual(self.indicator.progress_bar.value(), 3)
        self.assertEqual(self.indicator.progress_bar.maximum(), 4)
        self.assertEqual(self.indicator.status_label.text(), "Loading thumbnails… 3 of 4")

    def test_unknown_total_uses_busy_bar(self) -> None:
        self.indicator.begin("Reading GPS data…")

        self.assertEqual(
            (self.indicator.progress_bar.minimum(), self.indicator.progress_bar.maximum()),
            (0, 0),
        )


class ShimmerPaintTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_placeholder_tile_is_painted_for_waiting_items(self) -> None:
        settings_dir = tempfile.TemporaryDirectory()
        self.addCleanup(settings_dir.cleanup)
        window = MainWindow(
            settings=QSettings(str(Path(settings_dir.name) / "s.ini"), QSettings.IniFormat)
        )
        self.addCleanup(window.close)
        window.workflow = PhotoWorkflowFacade(loader=FakePhotoLoader(), writer=FakeWriter())
        window.thumbnail_loader = SlowThumbnailLoader(delay=0.0)
        window.background.run_inline = True
        window.session.selected_paths = [Path("/tmp/a.jpg")]
        window.show()
        window.populate_list()
        grid = window.list_widget
        item = next(
            grid.item(row) for row in range(grid.count())
            if grid.item(row).data(THUMBNAIL_PATH_ROLE) is not None
        )
        item.setIcon(window._blank_thumbnail_icon())
        rect = grid.visualItemRect(item)

        item.setData(SHIMMER_ROLE, False)
        without = grid.viewport().grab().toImage().copy(rect)
        item.setData(SHIMMER_ROLE, True)
        window.thumbnail_delegate.advance(600)
        with_tile = grid.viewport().grab().toImage().copy(rect)

        self.assertNotEqual(without, with_tile)


if __name__ == "__main__":
    unittest.main()
