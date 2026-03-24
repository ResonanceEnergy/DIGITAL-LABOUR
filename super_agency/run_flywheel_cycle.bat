@echo off
cd /d "C:\Dev\SuperAgency-Shared"
python -m repo_depot.flywheel.flywheel_controller --once --cooldown 6 >> "%~dp0flywheel_cron.log" 2>&1
python MATRIX_MONITOR\flywheel_feed.py >> "%~dp0flywheel_cron.log" 2>&1
