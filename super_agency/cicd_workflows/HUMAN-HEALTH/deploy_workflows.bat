@echo off
REM Deploy CI/CD workflows to HUMAN-HEALTH
echo Deploying CI/CD workflows to HUMAN-HEALTH...

REM Copy workflow files to repository
xcopy ".github" "c:\path\to\HUMAN-HEALTH\.github\" /E /I /Y

echo Workflows deployed! Push to GitHub to activate.
pause
