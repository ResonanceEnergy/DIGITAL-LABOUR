@echo off
REM Deploy CI/CD workflows to YOUTUBEDROP
echo Deploying CI/CD workflows to YOUTUBEDROP...

REM Copy workflow files to repository
xcopy ".github" "c:\path\to\YOUTUBEDROP\.github\" /E /I /Y

echo Workflows deployed! Push to GitHub to activate.
pause
