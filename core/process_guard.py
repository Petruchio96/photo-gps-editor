"""
Start helper processes that cannot outlive the app.

Why this file exists:
    ExifTool runs as one long-lived process (see exiftool_wrapper.py). If the
    app exits normally it tells ExifTool to quit, but if the app crashes or is
    force-closed, ExifTool would keep running in the background forever: in
    "-stay_open" mode it keeps polling its closed input every 10 ms.

    start_guarded_process() starts a process that is stopped automatically when
    this app's process ends, however it ends:

    Linux / macOS:
        The command runs under a tiny /bin/sh watchdog in its own process group.
        A background loop checks once per second whether the app is still
        alive; if not, it stops the whole group.

    Windows:
        The process is placed in a Windows "job object" with
        KILL_ON_JOB_CLOSE. Windows ends every process in the job when the
        app's handle to the job closes, which happens when the app exits. The
        process is started suspended and only resumed after joining the job,
        so programs it launches (ExifTool starts perl.exe) are covered too.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys

# On Windows, a GUI app that starts a console program flashes a console window
# unless told not to. CREATE_NO_WINDOW only exists on Windows; 0 is a no-op
# value for creationflags on other platforms.
NO_WINDOW_FLAGS = getattr(subprocess, "CREATE_NO_WINDOW", 0)

# $1 is the app's process ID; the rest is the command to run. The command runs
# in the foreground so it keeps this shell's stdin. "kill 0" signals the whole
# process group, which start_new_session=True makes separate from the app.
_POSIX_WATCHDOG = """
parent="$1"
shift
( while kill -0 "$parent" 2>/dev/null; do sleep 1; done; kill 0 ) &
watcher=$!
"$@"
status=$?
kill "$watcher" 2>/dev/null
exit $status
"""


def start_guarded_process(command: list[str], **popen_kwargs) -> subprocess.Popen:
    """
    Start a process that is stopped automatically when this app exits.

    Takes the same keyword arguments as subprocess.Popen.
    """
    if sys.platform == "win32":
        return _start_windows(command, popen_kwargs)

    return subprocess.Popen(
        ["/bin/sh", "-c", _POSIX_WATCHDOG, "watchdog", str(os.getpid()), *command],
        start_new_session=True,
        **popen_kwargs,
    )


def stop_process_tree(process: subprocess.Popen) -> None:
    """
    Kill a process started by start_guarded_process, plus any helpers it left.

    Safe to call after the process has already exited; it then only cleans up.
    """
    if sys.platform == "win32":
        # Closing the job handle makes Windows end everything still in the job.
        job = getattr(process, "_guard_job", None)
        if job is not None:
            process._guard_job = None
            _close_windows_handle(job)
        elif process.poll() is None:
            process.kill()
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass

    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        pass


def _start_windows(command: list[str], popen_kwargs: dict) -> subprocess.Popen:
    create_suspended = 0x00000004
    flags = popen_kwargs.pop("creationflags", 0) | create_suspended
    process = subprocess.Popen(command, creationflags=flags, **popen_kwargs)

    try:
        process._guard_job = _create_kill_on_close_job(process)
    except OSError:
        process._guard_job = None
    finally:
        # Always resume, even if the job setup failed; a working process
        # without crash protection is better than a stuck one.
        _resume_windows_process(process)

    return process


def _create_kill_on_close_job(process: subprocess.Popen) -> int:
    """
    Put the process in a new job that ends it when the job handle closes.

    The returned handle is kept until stop_process_tree() closes it. If the app
    dies first, Windows closes it, which ends the process.
    """
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateJobObjectW.restype = wintypes.HANDLE
    kernel32.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
    kernel32.SetInformationJobObject.restype = wintypes.BOOL
    kernel32.SetInformationJobObject.argtypes = [
        wintypes.HANDLE,
        ctypes.c_int,
        ctypes.c_void_p,
        wintypes.DWORD,
    ]
    kernel32.AssignProcessToJobObject.restype = wintypes.BOOL
    kernel32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]

    class IoCounters(ctypes.Structure):
        _fields_ = [
            (name, ctypes.c_ulonglong)
            for name in (
                "ReadOperationCount",
                "WriteOperationCount",
                "OtherOperationCount",
                "ReadTransferCount",
                "WriteTransferCount",
                "OtherTransferCount",
            )
        ]

    class BasicLimitInformation(ctypes.Structure):
        _fields_ = [
            ("PerProcessUserTimeLimit", ctypes.c_int64),
            ("PerJobUserTimeLimit", ctypes.c_int64),
            ("LimitFlags", wintypes.DWORD),
            ("MinimumWorkingSetSize", ctypes.c_size_t),
            ("MaximumWorkingSetSize", ctypes.c_size_t),
            ("ActiveProcessLimit", wintypes.DWORD),
            ("Affinity", ctypes.c_size_t),
            ("PriorityClass", wintypes.DWORD),
            ("SchedulingClass", wintypes.DWORD),
        ]

    class ExtendedLimitInformation(ctypes.Structure):
        _fields_ = [
            ("BasicLimitInformation", BasicLimitInformation),
            ("IoInfo", IoCounters),
            ("ProcessMemoryLimit", ctypes.c_size_t),
            ("JobMemoryLimit", ctypes.c_size_t),
            ("PeakProcessMemoryUsed", ctypes.c_size_t),
            ("PeakJobMemoryUsed", ctypes.c_size_t),
        ]

    job = kernel32.CreateJobObjectW(None, None)
    if not job:
        raise ctypes.WinError(ctypes.get_last_error())

    job_object_limit_kill_on_job_close = 0x00002000
    job_object_extended_limit_information_class = 9
    info = ExtendedLimitInformation()
    info.BasicLimitInformation.LimitFlags = job_object_limit_kill_on_job_close
    if not kernel32.SetInformationJobObject(
        job,
        job_object_extended_limit_information_class,
        ctypes.byref(info),
        ctypes.sizeof(info),
    ):
        error = ctypes.WinError(ctypes.get_last_error())
        _close_windows_handle(job)
        raise error

    if not kernel32.AssignProcessToJobObject(job, int(process._handle)):
        error = ctypes.WinError(ctypes.get_last_error())
        _close_windows_handle(job)
        raise error

    return job


def _resume_windows_process(process: subprocess.Popen) -> None:
    import ctypes
    from ctypes import wintypes

    # NtResumeProcess resumes every thread of a suspended process. Popen does
    # not keep the main thread's handle, so ResumeThread cannot be used.
    ntdll = ctypes.WinDLL("ntdll")
    ntdll.NtResumeProcess.argtypes = [wintypes.HANDLE]
    ntdll.NtResumeProcess.restype = ctypes.c_long
    ntdll.NtResumeProcess(int(process._handle))


def _close_windows_handle(handle: int) -> None:
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL
    kernel32.CloseHandle(handle)
