@echo off
cd /d "%~dp0"
echo Activating virtual environment...
call venv\Scripts\activate.bat
echo Starting Matrix Monitor...
python flask_matrix_monitor.py
pause
