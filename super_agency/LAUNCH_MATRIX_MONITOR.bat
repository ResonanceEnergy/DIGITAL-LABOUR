@echo off
cd /d "%~dp0"
echo Starting Matrix Monitor (Flask)...
echo.
echo NOTE: On Windows, use .\venv\Scripts\python.exe (NOT .\venv\bin\python)
echo.

REM Try venv first, then .venv, then system python
if exist ".\venv\Scripts\python.exe" (
    echo Using .\venv\Scripts\python.exe
    .\venv\Scripts\python.exe flask_matrix_monitor.py
) else if exist ".\.venv\Scripts\python.exe" (
    echo Using .\.venv\Scripts\python.exe
    .\.venv\Scripts\python.exe flask_matrix_monitor.py
) else (
    echo Using system python
    python flask_matrix_monitor.py
)
pause
