@echo off
REM Bit Rage Systems CPU Regulator & Task Manager Launcher
REM Launches the CPU regulator and task manager in the background

echo 🚀 Starting Bit Rage Systems CPU Regulator & Task Manager...
echo.

REM Change to the script directory
cd /d "%~dp0"

REM Start the CPU and Task Manager in background
start "CPU-Task-Manager" /B python cpu_task_manager.py start --cpu-target 80 --memory-threshold 85 --max-tasks 4

echo ✅ CPU Regulator & Task Manager started in background
echo 💡 Use 'python cpu_task_manager.py dashboard' to monitor
echo 💡 Use 'python cpu_task_manager.py stop' to stop
echo.
pause