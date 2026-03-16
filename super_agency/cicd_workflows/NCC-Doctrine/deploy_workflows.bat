@echo off
REM Deploy CI/CD workflows to NCC-Doctrine
echo Deploying CI/CD workflows to NCC-Doctrine...

REM Copy workflow files to repository
xcopy ".github" "c:\path\to\NCC-Doctrine\.github\" /E /I /Y

echo Workflows deployed! Push to GitHub to activate.
pause
