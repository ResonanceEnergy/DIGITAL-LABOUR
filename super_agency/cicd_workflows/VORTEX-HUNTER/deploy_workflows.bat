@echo off
REM Deploy CI/CD workflows to VORTEX-HUNTER
echo Deploying CI/CD workflows to VORTEX-HUNTER...

REM Copy workflow files to repository
xcopy ".github" "c:\path\to\VORTEX-HUNTER\.github\" /E /I /Y

echo Workflows deployed! Push to GitHub to activate.
pause
