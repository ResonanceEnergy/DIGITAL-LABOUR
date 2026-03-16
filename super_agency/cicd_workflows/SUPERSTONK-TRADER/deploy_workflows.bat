@echo off
REM Deploy CI/CD workflows to SUPERSTONK-TRADER
echo Deploying CI/CD workflows to SUPERSTONK-TRADER...

REM Copy workflow files to repository
xcopy ".github" "c:\path\to\SUPERSTONK-TRADER\.github\" /E /I /Y

echo Workflows deployed! Push to GitHub to activate.
pause
