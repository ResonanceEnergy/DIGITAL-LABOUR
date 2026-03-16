@echo off
REM Deploy CI/CD workflows to CIVIL-FORGE-TECHNOLOGIES-
echo Deploying CI/CD workflows to CIVIL-FORGE-TECHNOLOGIES-...

REM Copy workflow files to repository
xcopy ".github" "c:\path\to\CIVIL-FORGE-TECHNOLOGIES-\.github\" /E /I /Y

echo Workflows deployed! Push to GitHub to activate.
pause
