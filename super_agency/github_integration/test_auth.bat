@echo off
echo 🔐 Testing GitHub Authentication for Digital Labour
echo ==================================================
cd /d "%~dp0"

if exist ".env" (
    echo ✅ Found .env file
    python quick_test.py
) else (
    echo ❌ .env file not found
)

echo ==================================================
echo 🎯 Next Steps:
echo 1. If authentication works, run: run_github_integration.bat sync
echo 2. Check GITHUB_AUTH_SETUP_GUIDE.md for detailed instructions
pause