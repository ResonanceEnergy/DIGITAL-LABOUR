@echo off
REM Deploy CI/CD workflows to Crimson-Compass
echo Deploying CI/CD workflows to Crimson-Compass...

REM Copy workflow files to repository
xcopy ".github" "c:\path\to\Crimson-Compass\.github\" /E /I /Y

echo Workflows deployed! Push to GitHub to activate.
pause
