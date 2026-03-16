@echo off
REM Deploy CI/CD workflows to Adventure-Hero-Chronicles-Of-Glory
echo Deploying CI/CD workflows to Adventure-Hero-Chronicles-Of-Glory...

REM Copy workflow files to repository
xcopy ".github" "c:\path\to\Adventure-Hero-Chronicles-Of-Glory\.github\" /E /I /Y

echo Workflows deployed! Push to GitHub to activate.
pause
