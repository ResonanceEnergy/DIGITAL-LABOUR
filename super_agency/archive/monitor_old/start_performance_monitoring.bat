@echo off
REM Digital Labour Performance Monitoring Launcher
REM Runs 24-hour performance monitoring in background

echo 🚀 Starting Digital Labour Performance Monitoring (24 hours)
echo 📊 This will run in the background and collect metrics every 15 minutes
echo 📁 Results will be saved to performance_monitoring\ directory

cd /d "C:\Dev\DIGITAL LABOUR-Shared"

REM Start monitoring in background (24 hours = 1440 minutes)
start /B python performance_monitor.py --hours 24 --interval 15

echo ✅ Performance monitoring started successfully
echo ⏰ Monitoring will run for 24 hours
echo 📋 Check performance_monitoring\ directory for results
echo 🛑 To stop monitoring early, kill the python process

pause
