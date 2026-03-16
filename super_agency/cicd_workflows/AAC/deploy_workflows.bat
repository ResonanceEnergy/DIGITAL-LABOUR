@echo off
REM Deploy CI/CD workflows to AAC
echo Deploying CI/CD workflows to AAC...

REM Copy workflow files to repository
xcopy ".github" "c:\path\to\AAC\.github\" /E /I /Y

echo Workflows deployed! Push to GitHub to activate.
pause
