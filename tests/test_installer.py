import subprocess
from pathlib import Path

from scripts import install_environment


def test_installer_creates_environment_installs_and_verifies(tmp_path, monkeypatch):
    requirements_file = tmp_path / "requirements.txt"
    requirements_file.write_text("streamlit\n", encoding="utf-8")
    venv_directory = tmp_path / ".venv"
    target_python = install_environment.venv_python_path(venv_directory)
    commands: list[tuple[list[str], str, Path]] = []

    def fake_run(command, step, cwd):
        commands.append((list(command), step, cwd))
        if "Create isolated" in step:
            target_python.parent.mkdir(parents=True)
            target_python.touch()

    monkeypatch.setattr(install_environment, "run_checked", fake_run)

    assert install_environment.install(tmp_path, venv_directory) == 0
    assert len(commands) == 4
    assert commands[0][0][1:3] == ["-m", "venv"]
    assert commands[1][0][1:4] == ["-m", "pip", "install"]
    assert str(requirements_file) in commands[2][0]
    assert commands[3][0][1] == "-c"
    assert all(command[2] == tmp_path for command in commands)


def test_installer_returns_dependency_command_error(tmp_path, monkeypatch):
    (tmp_path / "requirements.txt").write_text("streamlit\n", encoding="utf-8")
    venv_directory = tmp_path / ".venv"
    target_python = install_environment.venv_python_path(venv_directory)
    target_python.parent.mkdir(parents=True)
    target_python.touch()

    def fail_run(command, step, cwd):
        raise subprocess.CalledProcessError(returncode=7, cmd=command)

    monkeypatch.setattr(install_environment, "run_checked", fail_run)

    assert install_environment.install(tmp_path, venv_directory) == 7
