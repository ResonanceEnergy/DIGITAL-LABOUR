@echo off
REM Deploy CI/CD workflows to ELECTRIC-UNIVERSE
echo Deploying CI/CD workflows to ELECTRIC-UNIVERSE...

REM Copy workflow files to repository
xcopy ".github" "c:\path\to\ELECTRIC-UNIVERSE\.github\" /E /I /Y

echo Workflows deployed! Push to GitHub to activate.
pause
