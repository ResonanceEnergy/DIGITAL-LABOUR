@echo off
REM Deploy CI/CD workflows to NCC
echo Deploying CI/CD workflows to NCC...

REM Copy workflow files to repository
xcopy ".github" "c:\path\to\NCC\.github\" /E /I /Y

echo Workflows deployed! Push to GitHub to activate.
pause
