#!/bin/bash
# SuperAgency PowerShell Installation Script
# Installs PowerShell on macOS using Homebrew
# Run with: bash powershell_install.sh

echo "🔧 SuperAgency PowerShell Installation Script"
echo "=============================================="
echo ""

# Check if running on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo "❌ This script is designed for macOS only."
    exit 1
fi

echo "📍 Checking system requirements..."

# Check if Homebrew is installed
if ! command -v brew &> /dev/null; then
    echo "🍺 Homebrew not found. Installing Homebrew..."
    echo "This will require admin privileges (sudo access)."
    echo ""

    # Install Homebrew
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

    # Add Homebrew to PATH for this session
    echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
    eval "$(/opt/homebrew/bin/brew shellenv)"

    echo "✅ Homebrew installed successfully!"
else
    echo "✅ Homebrew is already installed."
fi

echo ""
echo "🔄 Updating Homebrew..."
brew update

echo ""
echo "⚡ Installing PowerShell..."
brew install --cask powershell

echo ""
echo "🔍 Verifying PowerShell installation..."

# Check if PowerShell was installed successfully
if command -v pwsh &> /dev/null; then
    echo "✅ PowerShell installed successfully!"
    echo ""

    # Get PowerShell version
    PWSH_VERSION=$(pwsh --version)
    echo "📊 PowerShell Version: $PWSH_VERSION"

    echo ""
    echo "🚀 Testing PowerShell..."
    pwsh -Command "Write-Host 'Hello from PowerShell in SuperAgency!' -ForegroundColor Green; \$PSVersionTable.PSVersion"

    echo ""
    echo "📚 PowerShell is ready for SuperAgency operations!"
    echo ""
    echo "💡 Useful commands:"
    echo "   pwsh                    - Start PowerShell interactive session"
    echo "   pwsh -Command 'command' - Run PowerShell command"
    echo "   brew upgrade powershell - Update PowerShell when new versions are available"
    echo ""
    echo "🎯 Next steps:"
    echo "   - Configure PowerShell profile for SuperAgency"
    echo "   - Set up PowerShell modules for automation"
    echo "   - Integrate with existing SuperAgency scripts"

else
    echo "❌ PowerShell installation failed."
    echo "Please check the error messages above and try again."
    echo ""
    echo "🔧 Troubleshooting:"
    echo "   - Ensure you have admin privileges"
    echo "   - Check internet connection"
    echo "   - Try: brew doctor"
    exit 1
fi

echo ""
echo "🎉 Installation complete! Welcome to PowerShell on SuperAgency."
