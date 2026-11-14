"""Build standalone Windows executable (dist/GitAICommit.exe) using PyInstaller."""

from pathlib import Path
import subprocess
import sys


def main() -> int:
    root = Path(__file__).resolve().parent
    entry_script = root / "app" / "main.py"

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--name=GitAICommit",
        "--onefile",
        "--windowed",
        "--noconfirm",
        "--clean",
        f"--paths={root}",
        "--collect-all=customtkinter",
        "--collect-submodules=core",
        "--collect-submodules=app",
        str(entry_script),
    ]

    print("Running:", " ".join(cmd))
    return subprocess.call(cmd, cwd=str(root))


if __name__ == "__main__":
    raise SystemExit(main())
