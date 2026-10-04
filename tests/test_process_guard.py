import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

from core.process_guard import start_guarded_process, stop_process_tree

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# A guarded command that starts a grandchild process (the way the Windows
# exiftool.exe starts perl.exe), records the grandchild's process ID, and waits.
CHILD_SCRIPT = """
import subprocess, sys, time
subprocess.Popen([
    sys.executable, "-c",
    "import os, sys, time\\n"
    "with open(sys.argv[1], 'w') as f: f.write(str(os.getpid()))\\n"
    "time.sleep(120)",
    sys.argv[1],
])
time.sleep(120)
"""

# A stand-in for the app: starts the guarded command, then exits without any
# cleanup (os._exit skips atexit handlers), the way a crash would.
CRASHING_APP_SCRIPT = """
import os, sys, time
sys.path.insert(0, sys.argv[1])
from core.process_guard import start_guarded_process
pid_file = sys.argv[2]
start_guarded_process([sys.executable, "-c", sys.argv[3], pid_file])
deadline = time.time() + 30
while time.time() < deadline:
    if os.path.exists(pid_file) and open(pid_file).read().strip():
        break
    time.sleep(0.05)
os._exit(0)
"""


def _pid_is_running(pid: int) -> bool:
    if sys.platform == "win32":
        import ctypes

        synchronize = 0x00100000
        wait_timeout = 0x00000102
        kernel32 = ctypes.WinDLL("kernel32")
        handle = kernel32.OpenProcess(synchronize, False, pid)
        if not handle:
            return False
        try:
            return kernel32.WaitForSingleObject(handle, 0) == wait_timeout
        finally:
            kernel32.CloseHandle(handle)

    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _wait_until_stopped(pid: int, timeout: float = 10.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if not _pid_is_running(pid):
            return True
        time.sleep(0.1)
    return False


def _read_pid(pid_file: Path, timeout: float = 30.0) -> int:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if pid_file.exists() and pid_file.read_text().strip():
            return int(pid_file.read_text())
        time.sleep(0.05)
    raise AssertionError("Grandchild process did not start")


class ProcessGuardTests(unittest.TestCase):
    def setUp(self) -> None:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        self.pid_file = Path(temp_dir.name) / "grandchild.pid"

    def _kill_if_running(self, pid: int) -> None:
        if _pid_is_running(pid):
            os.kill(pid, 9)

    def test_processes_stop_when_app_crashes(self) -> None:
        subprocess.run(
            [
                sys.executable,
                "-c",
                CRASHING_APP_SCRIPT,
                str(PROJECT_ROOT),
                str(self.pid_file),
                CHILD_SCRIPT,
            ],
            check=True,
            timeout=60,
        )
        grandchild_pid = _read_pid(self.pid_file)
        self.addCleanup(self._kill_if_running, grandchild_pid)

        self.assertTrue(
            _wait_until_stopped(grandchild_pid),
            "Guarded process kept running after the app exited",
        )

    def test_stop_process_tree_stops_grandchildren(self) -> None:
        process = start_guarded_process(
            [sys.executable, "-c", CHILD_SCRIPT, str(self.pid_file)]
        )
        grandchild_pid = _read_pid(self.pid_file)
        self.addCleanup(self._kill_if_running, grandchild_pid)

        stop_process_tree(process)

        self.assertIsNotNone(process.poll())
        self.assertTrue(_wait_until_stopped(grandchild_pid))

    def test_stop_process_tree_is_safe_after_exit(self) -> None:
        process = start_guarded_process([sys.executable, "-c", "pass"])
        process.wait(timeout=30)

        stop_process_tree(process)
        stop_process_tree(process)

        self.assertEqual(process.returncode, 0)


if __name__ == "__main__":
    unittest.main()
