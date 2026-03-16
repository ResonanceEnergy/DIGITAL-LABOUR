@echo off
REM Deploy CI/CD workflows to demo
echo Deploying CI/CD workflows to demo...

REM Copy workflow files to repository
xcopy ".github" "c:\path\to\demo\.github\" /E /I /Y

echo Workflows deployed! Push to GitHub to activate.
pause
