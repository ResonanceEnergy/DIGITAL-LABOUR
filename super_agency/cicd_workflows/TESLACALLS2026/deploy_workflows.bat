@echo off
REM Deploy CI/CD workflows to TESLACALLS2026
echo Deploying CI/CD workflows to TESLACALLS2026...

REM Copy workflow files to repository
xcopy ".github" "c:\path\to\TESLACALLS2026\.github\" /E /I /Y

echo Workflows deployed! Push to GitHub to activate.
pause
