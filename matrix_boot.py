"""BITRAGE MATRIX — Auto-launch script.

Starts the FastAPI server + all daemons on system boot.
Install via Windows Task Scheduler or run manually.

Usage:
    python matrix_boot.py          # Start everything
    python matrix_boot.py --stop   # Kill daemons + server

Task Scheduler setup:
    Trigger: At startup
    Action:  pythonw.exe "C:\\dev\\DIGITAL LABOUR\\DIGITAL LABOUR\\matrix_boot.py"
    Start in: C:\\dev\\DIGITAL LABOUR\\DIGITAL LABOUR
"""

import subprocess
import sys
import os
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV_PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"
PYTHON = str(VENV_PYTHON) if VENV_PYTHON.exists() else sys.executable
LOG_DIR = ROOT / "data"
LOG_DIR.mkdir(exist_ok=True)


def start_server():
    """Launch FastAPI via uvicorn as a background process."""
    log = open(LOG_DIR / "matrix_server.log", "a", encoding="utf-8")
    proc = subprocess.Popen(
        [PYTHON, "-m", "uvicorn", "api.intake:app",
         "--host", "0.0.0.0", "--port", "8000"],
        cwd=str(ROOT),
        stdout=log,
        stderr=subprocess.STDOUT,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    print(f"[MATRIX] Server started — PID {proc.pid}")
    return proc


def start_daemons():
    """Launch all daemon processes via launch.py."""
    log = open(LOG_DIR / "matrix_daemons.log", "a", encoding="utf-8")
    proc = subprocess.Popen(
        [PYTHON, "launch.py", "--daemons"],
        cwd=str(ROOT),
        stdout=log,
        stderr=subprocess.STDOUT,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    print(f"[MATRIX] Daemons started — PID {proc.pid}")
    return proc


def main():
    if "--stop" in sys.argv:
        # Kill by script names
        if os.name == "nt":
            os.system('taskkill /F /FI "WINDOWTITLE eq uvicorn*" 2>nul')
        print("[MATRIX] Stop signal sent")
        return

    print("[MATRIX] ═══════════════════════════════")
    print("[MATRIX]  BITRAGE MATRIX — AUTO BOOT")
    print("[MATRIX] ═══════════════════════════════")
    print(f"[MATRIX] Python: {PYTHON}")
    print(f"[MATRIX] Root:   {ROOT}")

    server = start_server()
    time.sleep(2)
    daemons = start_daemons()

    print("[MATRIX] All systems launched.")
    print(f"[MATRIX] Dashboard: http://localhost:8000/matrix")
    print(f"[MATRIX] Logs: {LOG_DIR}")


if __name__ == "__main__":
    main()
