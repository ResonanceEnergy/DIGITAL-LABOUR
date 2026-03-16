@echo off
REM Deploy CI/CD workflows to NATEBJONES
echo Deploying CI/CD workflows to NATEBJONES...

REM Copy workflow files to repository
xcopy ".github" "c:\path\to\NATEBJONES\.github\" /E /I /Y

echo Workflows deployed! Push to GitHub to activate.
pause
