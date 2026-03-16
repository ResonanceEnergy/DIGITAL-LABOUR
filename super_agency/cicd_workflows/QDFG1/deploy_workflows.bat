@echo off
REM Deploy CI/CD workflows to QDFG1
echo Deploying CI/CD workflows to QDFG1...

REM Copy workflow files to repository
xcopy ".github" "c:\path\to\QDFG1\.github\" /E /I /Y

echo Workflows deployed! Push to GitHub to activate.
pause
