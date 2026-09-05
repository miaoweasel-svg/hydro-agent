"""Create the project virtual environment and install all dependencies."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[1]
VENV_DIRECTORY = PROJECT_ROOT / ".venv"
MINIMUM_PYTHON = (3, 10)


def venv_python_path(venv_directory: Path) -> Path:
    """Return the Python executable path for a virtual environment."""

    if sys.platform == "win32":
        return venv_directory / "Scripts" / "python.exe"
    return venv_directory / "bin" / "python"


def run_checked(command: Sequence[str], step: str, cwd: Path) -> None:
    """Run one visible installation step and fail with its original exit code."""

    print(f"\n[{step}]", flush=True)
    subprocess.run(list(command), cwd=cwd, check=True)


def install(
    project_root: Path = PROJECT_ROOT,
    venv_directory: Path = VENV_DIRECTORY,
) -> int:
    """Create or update the isolated environment and verify key imports."""

    if sys.version_info < MINIMUM_PYTHON:
        print("Hydro Agent requires Python 3.10 or newer.")
        print(f"Current interpreter: {sys.version.split()[0]}")
        return 1

    requirements_file = project_root / "requirements.txt"
    if not requirements_file.is_file():
        print(f"requirements.txt was not found in: {project_root}")
        return 1

    target_python = venv_python_path(venv_directory)
    try:
        if not target_python.is_file():
            run_checked(
                [sys.executable, "-m", "venv", str(venv_directory)],
                "1/4 Create isolated .venv",
                project_root,
            )
        else:
            print("\n[1/4 Reuse existing .venv]", flush=True)
        if not target_python.is_file():
            print("The virtual environment was not created correctly.")
            return 1

        run_checked(
            [
                str(target_python),
                "-m",
                "pip",
                "install",
                "--upgrade",
                "pip",
                "setuptools",
                "wheel",
            ],
            "2/4 Update packaging tools",
            project_root,
        )
        run_checked(
            [
                str(target_python),
                "-m",
                "pip",
                "install",
                "--prefer-binary",
                "-r",
                str(requirements_file),
            ],
            "3/4 Install Hydro Agent dependencies",
            project_root,
        )
        verification_code = (
            "import hydro_agent, numpy, openai, openpyxl, pandas, plotly, "
            "pypdf, sklearn, streamlit; print('Dependency imports: OK')"
        )
        run_checked(
            [str(target_python), "-c", verification_code],
            "4/4 Verify installation",
            project_root,
        )
    except subprocess.CalledProcessError as exc:
        print(f"\nInstallation stopped because a command failed (exit code {exc.returncode}).")
        print("Check the network connection, then run this installer again.")
        return exc.returncode or 1
    except KeyboardInterrupt:
        print("\nInstallation was cancelled. Run the installer again to continue.")
        return 130
    except OSError as exc:
        print(f"\nInstallation could not continue: {exc}")
        return 1

    print("\nHydro Agent environment is ready.")
    print("Next: double-click the start script in the project folder.")
    return 0


if __name__ == "__main__":
    raise SystemExit(install())
