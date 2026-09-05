"""Transparent Windows launcher for the local Streamlit application."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_URL = "http://localhost:8501"
HEALTH_URL = f"{APP_URL}/_stcore/health"
STATE_DIRECTORY = PROJECT_ROOT / ".run"
STATE_FILE = STATE_DIRECTORY / "hydro-agent-server.json"


def server_is_ready() -> bool:
    """Check the local health endpoint without using system proxy settings."""

    try:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(HEALTH_URL, timeout=1) as response:
            return response.status == 200 and response.read().strip() == b"ok"
    except Exception:
        return False


def write_process_state(process: subprocess.Popen[bytes], started_at: float) -> None:
    STATE_DIRECTORY.mkdir(parents=True, exist_ok=True)
    state = {
        "process_id": process.pid,
        "started_at": started_at,
        "python_executable": str(Path(sys.executable).resolve()),
        "project_root": str(PROJECT_ROOT),
    }
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def remove_own_state(process_id: int) -> None:
    try:
        state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        if int(state.get("process_id", -1)) == process_id:
            STATE_FILE.unlink(missing_ok=True)
    except (OSError, ValueError, json.JSONDecodeError):
        pass


def shutdown_was_requested(process_id: int) -> bool:
    """Return whether the separate stop script requested this process exit."""

    if not STATE_FILE.exists():
        return True
    try:
        state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        return int(state.get("process_id", -1)) == process_id and bool(
            state.get("stop_requested", False)
        )
    except (OSError, TypeError, ValueError, json.JSONDecodeError):
        return False


def launch(open_browser: bool = True) -> int:
    """Start Streamlit, open the browser, and keep the console attached."""

    if server_is_ready():
        print(f"Hydro Agent is already running at {APP_URL}")
        if open_browser:
            webbrowser.open(APP_URL)
        return 0

    try:
        __import__("streamlit")
    except ImportError:
        print("Streamlit is not installed in this Python environment.")
        print("Run: python -m pip install -r requirements.txt")
        return 1

    command = [sys.executable, "-m", "streamlit", "run", str(PROJECT_ROOT / "app.py")]
    started_at = time.time()
    process = subprocess.Popen(command, cwd=PROJECT_ROOT)
    write_process_state(process, started_at)

    try:
        for _ in range(80):
            if server_is_ready():
                print(f"Hydro Agent started at {APP_URL}")
                print("Keep this window open. Press Ctrl+C to stop the application.")
                if open_browser:
                    webbrowser.open(APP_URL)
                break
            if process.poll() is not None:
                print(f"Streamlit exited during startup with code {process.returncode}.")
                return process.returncode or 1
            time.sleep(0.25)
        else:
            print("Hydro Agent did not become ready within 20 seconds.")
            process.terminate()
            return 1

        return_code = process.wait()
        if return_code != 0 and shutdown_was_requested(process.pid):
            # The separate stop script marks/removes the state before
            # terminating the server, so this is an expected shutdown.
            return 0
        return return_code
    except KeyboardInterrupt:
        print("\nStopping Hydro Agent...")
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        return 0
    finally:
        remove_own_state(process.pid)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Start the local Hydro Agent application.")
    parser.add_argument("--no-browser", action="store_true", help="Do not open a browser window.")
    arguments = parser.parse_args()
    raise SystemExit(launch(open_browser=not arguments.no_browser))
