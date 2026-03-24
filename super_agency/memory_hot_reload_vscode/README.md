# Bit Rage Systems Memory Hot Reload

A VS Code extension that provides hot code reloading for Bit Rage Systems memory systems, enabling real-time blank prevention and system updates.

## 🚀 Features

- **🔥 Hot Code Reloading**: Automatically reload memory systems when code changes
- **🛡️ Real-time Blank Prevention**: Continuous memory health monitoring
- **📊 Live Status**: Status bar integration showing memory system health
- **⚡ Force Reload**: Manual reload trigger with Ctrl+Shift+M (Cmd+Shift+M on Mac)
- **🔄 Auto-Recovery**: Automatic restart of failed memory systems

## 📦 Installation

### Option 1: From VS Code Marketplace
1. Open VS Code
2. Go to Extensions (Ctrl+Shift+X)
3. Search for "Bit Rage Systems Memory Hot Reload"
4. Click Install

### Option 2: Manual Installation
1. Download the `.vsix` file from releases
2. In VS Code: Extensions → Install from VSIX
3. Select the downloaded file

### Option 3: Development Installation
```bash
cd memory_hot_reload_vscode
npm install
npm run compile
code --install-extension out/super-agency-memory-hot-reload-1.0.0.vsix
```

## 🛠️ Usage

### Automatic Start
The extension automatically starts when you open a workspace containing `unified_memory_doctrine_system.py`.

### Manual Control
- **Start Hot Reload**: `Ctrl+Shift+P` → "Bit Rage Systems: Start Memory Hot Reload"
- **Stop Hot Reload**: `Ctrl+Shift+P` → "Bit Rage Systems: Stop Memory Hot Reload"
- **Show Status**: `Ctrl+Shift+P` → "Bit Rage Systems: Show Memory Status"
- **Force Reload**: `Ctrl+Shift+M` (or `Cmd+Shift+M` on Mac)

### Status Bar
- Green checkmark: Memory system healthy
- Spinning sync: Reloading in progress
- Red X: System down or error
- Flame icon: Hot reload active

## ⚙️ Configuration

Access settings via `Ctrl+,` → "Bit Rage Systems Memory Hot Reload":

- `autoStart`: Automatically start hot reload on workspace open (default: true)
- `reloadInterval`: Check interval for changes in milliseconds (default: 2000)
- `showNotifications`: Show reload notifications (default: true)

## 🔍 What It Monitors

The extension monitors these memory system files:
- `unified_memory_doctrine_system.py`
- `continuous_memory_backup.py`
- `memory_integration_hub.py`
- `memory_doctrine_system.py`

When any of these files change, the corresponding memory system is automatically reloaded.

## 🐛 Troubleshooting

### Extension Not Activating
- Ensure you're in a Bit Rage Systems workspace
- Check that `unified_memory_doctrine_system.py` exists
- Reload VS Code window: `Ctrl+Shift+P` → "Developer: Reload Window"

### Hot Reload Not Working
- Check VS Code terminal for error messages
- Ensure Python is in your PATH
- Verify memory system files are not corrupted

### Memory System Errors
- Use "Force Reload" command to restart all systems
- Check the integrated terminal for detailed error messages
- Ensure all Python dependencies are installed

## 📊 Commands

| Command | Keybinding | Description |
|---------|------------|-------------|
| Start Memory Hot Reload | - | Begin hot reloading |
| Stop Memory Hot Reload | - | Stop hot reloading |
| Show Memory Status | - | Display current memory system status |
| Force Memory Reload | `Ctrl+Shift+M` | Manually reload all memory systems |

## 🔧 Development

### Building
```bash
npm run compile
```

### Testing
```bash
npm run test
```

### Packaging
```bash
vsce package
```

## 📝 Requirements

- VS Code 1.74.0+
- Python 3.8+
- Bit Rage Systems memory system files in workspace

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details.

---

**Built for the Bit Rage Systems - Memory blanks prevented, hot reloading enabled!** 🚀