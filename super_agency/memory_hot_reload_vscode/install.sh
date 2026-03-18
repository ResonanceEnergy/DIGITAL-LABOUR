#!/bin/bash
# Bit Rage Labour Memory Hot Reload VS Code Extension Installer

set -e

echo "🧠 Bit Rage Labour Memory Hot Reload VS Code Extension"
echo "=================================================="

# Check if vsce is installed
if ! command -v vsce &> /dev/null; then
    echo "❌ vsce (VS Code Extension Manager) not found"
    echo "Install with: npm install -g @vscode/vsce"
    exit 1
fi

# Check if we're in the right directory
if [ ! -f "package.json" ] || [ ! -f "src/extension.ts" ]; then
    echo "❌ Not in extension directory. Run from memory_hot_reload_vscode/"
    exit 1
fi

echo "📦 Building extension..."
npm run compile

echo "🔨 Packaging extension..."
vsce package

echo "📥 Installing extension..."
code --install-extension Digital-Labour-memory-hot-reload-1.0.0.vsix

echo ""
echo "✅ Installation Complete!"
echo ""
echo "🎯 Next Steps:"
echo "1. Reload VS Code: Ctrl+Shift+P → 'Developer: Reload Window'"
echo "2. Open Bit Rage Labour workspace"
echo "3. Hot reload will start automatically"
echo ""
echo "🔥 Hot Code Reloading Active!"
echo "   • Memory blanks prevented"
echo "   • Real-time system updates"
echo "   • VS Code integration complete"