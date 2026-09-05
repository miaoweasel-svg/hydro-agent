"""Safely stop the Hydro Agent process recorded by the local launcher."""

from __future__ import annotations

import ctypes
import json
import os
import signal
import sys
from ctypes import wintypes
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
STATE_FILE = PROJECT_ROOT / ".run" / "hydro-agent-server.json"


class FileTime(ctypes.Structure):
    _fields_ = [("low", wintypes.DWORD), ("high", wintypes.DWORD)]


def windows_process_identity(process_id: int) -> tuple[float, Path] | None:
    """Return process creation time and executable path using read-only WinAPI calls."""

    if sys.platform != "win32":
        return None
    query_access = 0x1000
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.GetProcessTimes.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(FileTime),
        ctypes.POINTER(FileTime),
        ctypes.POINTER(FileTime),
        ctypes.POINTER(FileTime),
    ]
    kernel32.GetProcessTimes.restype = wintypes.BOOL
    kernel32.QueryFullProcessImageNameW.argtypes = [
        wintypes.HANDLE,
        wintypes.DWORD,
        wintypes.LPWSTR,
        ctypes.POINTER(wintypes.DWORD),
    ]
    kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL
    handle = kernel32.OpenProcess(query_access, False, process_id)
    if not handle:
        return None
    try:
        creation = FileTime()
        exit_time = FileTime()
        kernel_time = FileTime()
        user_time = FileTime()
        if not kernel32.GetProcessTimes(
            handle,
            ctypes.byref(creation),
            ctypes.byref(exit_time),
            ctypes.byref(kernel_time),
            ctypes.byref(user_time),
        ):
            return None
        ticks = (creation.high << 32) + creation.low
        created_at = ticks / 10_000_000 - 11_644_473_600

        size = wintypes.DWORD(32_768)
        buffer = ctypes.create_unicode_buffer(size.value)
        if not kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)):
            return None
        return created_at, Path(buffer.value).resolve()
    finally:
        kernel32.CloseHandle(handle)


def stop() -> int:
    """Stop only the exact process recorded by launch_app.py."""

    if not STATE_FILE.exists():
        print("No Hydro Agent process started by the launcher was found.")
        return 0
    try:
        state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        process_id = int(state["process_id"])
        expected_start = float(state["started_at"])
        expected_python = Path(state["python_executable"]).resolve()
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        print("The launcher state file is invalid; no process was stopped.")
        return 1

    identity = windows_process_identity(process_id)
    if identity is None:
        STATE_FILE.unlink(missing_ok=True)
        print("Hydro Agent is already stopped. Stale launcher state was removed.")
        return 0
    actual_start, actual_python = identity
    if abs(actual_start - expected_start) >= 5 or actual_python != expected_python:
        print("The saved PID belongs to another process; it was not stopped.")
        return 1

    state["stop_requested"] = True
    try:
        STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")
        os.kill(process_id, signal.SIGTERM)
    except OSError as exc:
        state.pop("stop_requested", None)
        try:
            STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")
        except OSError:
            pass
        print(f"Hydro Agent could not be stopped: {exc}")
        return 1
    STATE_FILE.unlink(missing_ok=True)
    print("Hydro Agent has stopped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(stop())
