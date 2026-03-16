@echo off
REM Deploy CI/CD workflows to TESLA-TECH
echo Deploying CI/CD workflows to TESLA-TECH...

REM Copy workflow files to repository
xcopy ".github" "c:\path\to\TESLA-TECH\.github\" /E /I /Y

echo Workflows deployed! Push to GitHub to activate.
pause
