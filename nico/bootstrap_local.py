from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _venv_python() -> Path:
    if os.name == "nt":
        return _repo_root() / ".venv" / "Scripts" / "python.exe"
    return _repo_root() / ".venv" / "bin" / "python"


def _create_venv() -> None:
    subprocess.check_call([sys.executable, "-m", "venv", str(_repo_root() / ".venv")])


def _run(cmd: list[str]) -> None:
    subprocess.check_call(cmd, cwd=str(_repo_root()))


def main() -> None:
    mode = "web"
    extra_args = []
    if len(sys.argv) > 1 and sys.argv[1] in {"desktop", "web"}:
        mode = sys.argv[1]
        extra_args = sys.argv[2:]
    else:
        extra_args = sys.argv[1:]

    venv_py = _venv_python()
    if not venv_py.exists():
        print("[NICO] Creating local environment...")
        _create_venv()

    print("[NICO] Installing/refreshing local package...")
    _run([str(venv_py), "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"])
    _run([str(venv_py), "-m", "pip", "install", "-e", "."])

    target = "nico.desktop_app" if mode == "desktop" else "nico.local_launcher"
    print(f"[NICO] Starting {target}...")
    os.execv(str(venv_py), [str(venv_py), "-m", target, *extra_args])


if __name__ == "__main__":
    main()
