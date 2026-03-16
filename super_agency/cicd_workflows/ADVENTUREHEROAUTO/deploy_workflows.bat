@echo off
REM Deploy CI/CD workflows to ADVENTUREHEROAUTO
echo Deploying CI/CD workflows to ADVENTUREHEROAUTO...

REM Copy workflow files to repository
xcopy ".github" "c:\path\to\ADVENTUREHEROAUTO\.github\" /E /I /Y

echo Workflows deployed! Push to GitHub to activate.
pause
