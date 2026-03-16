@echo off
REM Deploy CI/CD workflows to GEET-PLASMA-PROJECT
echo Deploying CI/CD workflows to GEET-PLASMA-PROJECT...

REM Copy workflow files to repository
xcopy ".github" "c:\path\to\GEET-PLASMA-PROJECT\.github\" /E /I /Y

echo Workflows deployed! Push to GitHub to activate.
pause
