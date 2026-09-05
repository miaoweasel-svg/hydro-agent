import json
import signal
import tomllib
from pathlib import Path

from scripts import launch_app, stop_app


def test_streamlit_does_not_open_a_second_browser_window():
    config_path = launch_app.PROJECT_ROOT / ".streamlit" / "config.toml"
    with config_path.open("rb") as config_file:
        config = tomllib.load(config_file)

    assert config["server"]["headless"] is True


def test_launcher_reuses_existing_server(monkeypatch):
    opened_urls: list[str] = []
    monkeypatch.setattr(launch_app, "server_is_ready", lambda: True)
    monkeypatch.setattr(launch_app.webbrowser, "open", opened_urls.append)

    assert launch_app.launch(open_browser=True) == 0
    assert opened_urls == [launch_app.APP_URL]


def test_launcher_recognizes_requested_shutdown(tmp_path, monkeypatch):
    state_file = tmp_path / "server.json"
    state_file.write_text(
        json.dumps({"process_id": 1234, "stop_requested": True}),
        encoding="utf-8",
    )
    monkeypatch.setattr(launch_app, "STATE_FILE", state_file)

    assert launch_app.shutdown_was_requested(1234) is True
    assert launch_app.shutdown_was_requested(9999) is False


def test_stop_refuses_reused_process_id(tmp_path, monkeypatch):
    state_file = tmp_path / "server.json"
    expected_python = Path("C:/Python/python.exe").resolve()
    state_file.write_text(
        json.dumps(
            {
                "process_id": 1234,
                "started_at": 100.0,
                "python_executable": str(expected_python),
            }
        ),
        encoding="utf-8",
    )
    stopped: list[tuple[int, signal.Signals]] = []
    monkeypatch.setattr(stop_app, "STATE_FILE", state_file)
    monkeypatch.setattr(
        stop_app,
        "windows_process_identity",
        lambda _process_id: (200.0, expected_python),
    )
    monkeypatch.setattr(stop_app.os, "kill", lambda pid, sig: stopped.append((pid, sig)))

    assert stop_app.stop() == 1
    assert stopped == []
    assert state_file.exists()


def test_stop_terminates_only_matching_process(tmp_path, monkeypatch):
    state_file = tmp_path / "server.json"
    expected_python = Path("C:/Python/python.exe").resolve()
    state_file.write_text(
        json.dumps(
            {
                "process_id": 4321,
                "started_at": 100.0,
                "python_executable": str(expected_python),
            }
        ),
        encoding="utf-8",
    )
    stopped: list[tuple[int, signal.Signals]] = []
    monkeypatch.setattr(stop_app, "STATE_FILE", state_file)
    monkeypatch.setattr(
        stop_app,
        "windows_process_identity",
        lambda _process_id: (101.0, expected_python),
    )
    monkeypatch.setattr(stop_app.os, "kill", lambda pid, sig: stopped.append((pid, sig)))

    assert stop_app.stop() == 0
    assert stopped == [(4321, signal.SIGTERM)]
    assert not state_file.exists()
