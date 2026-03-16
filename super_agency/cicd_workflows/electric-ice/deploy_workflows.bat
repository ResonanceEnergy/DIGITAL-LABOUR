@echo off
REM Deploy CI/CD workflows to electric-ice
echo Deploying CI/CD workflows to electric-ice...

REM Copy workflow files to repository
xcopy ".github" "c:\path\to\electric-ice\.github\" /E /I /Y

echo Workflows deployed! Push to GitHub to activate.
pause
