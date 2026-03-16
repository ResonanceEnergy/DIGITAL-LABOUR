@echo off
REM Deploy CI/CD workflows to NCL
echo Deploying CI/CD workflows to NCL...

REM Copy workflow files to repository
xcopy ".github" "c:\path\to\NCL\.github\" /E /I /Y

echo Workflows deployed! Push to GitHub to activate.
pause
