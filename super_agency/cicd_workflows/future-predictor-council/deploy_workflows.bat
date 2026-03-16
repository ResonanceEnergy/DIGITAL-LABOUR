@echo off
REM Deploy CI/CD workflows to future-predictor-council
echo Deploying CI/CD workflows to future-predictor-council...

REM Copy workflow files to repository
xcopy ".github" "c:\path\to\future-predictor-council\.github\" /E /I /Y

echo Workflows deployed! Push to GitHub to activate.
pause
