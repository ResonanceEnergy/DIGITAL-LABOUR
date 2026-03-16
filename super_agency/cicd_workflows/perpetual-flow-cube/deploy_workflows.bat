@echo off
REM Deploy CI/CD workflows to perpetual-flow-cube
echo Deploying CI/CD workflows to perpetual-flow-cube...

REM Copy workflow files to repository
xcopy ".github" "c:\path\to\perpetual-flow-cube\.github\" /E /I /Y

echo Workflows deployed! Push to GitHub to activate.
pause
