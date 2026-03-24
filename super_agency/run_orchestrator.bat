@echo off
cd /d "C:\Dev\SuperAgency-Shared"
echo Starting GitHub Orchestrator...
c:\Python314\python.exe github_orchestrator.py
echo.
echo Orchestrator completed. Check logs/github_orchestrator_* for results.
pause