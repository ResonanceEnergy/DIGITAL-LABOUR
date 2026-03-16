# 🚀 DIGITAL LABOUR - Cross-Platform Development Setup

## 📁 Shared Repository Location
**Path:** `C:\Dev\DIGITAL-LABOUR\`

This repository is optimized for **cross-platform development** between:
- **macOS (Quantum Quasar)** - Primary development system
- **Windows (QUANTUM FORGE)** - Secondary development system

## 🔄 Git Sync Setup

### On macOS (Quantum Quasar):
- Files are in: `$HOME/repos/DIGITAL-LABOUR/`
- Git automatically syncs changes to the remote

### On Windows (QUANTUM FORGE):
- Files will appear in: `C:\Dev\DIGITAL-LABOUR\`
- Git automatically syncs changes from the remote

## 🛠️ Initial Setup

### 1. Clone/Open Repository
```bash
# On macOS:
cd "$HOME/repos/DIGITAL-LABOUR"

# On Windows:
cd "C:\Dev\DIGITAL-LABOUR"
```

### 2. Install Recommended VS Code Extensions
- Open VS Code
- Go to Extensions (Ctrl+Shift+X / Cmd+Shift+X)
- Install all recommended extensions from `.vscode/extensions.json`

### 3. Set Up Python Environment (Local to Each System)
```bash
# macOS
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Windows
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 4. Test Setup
```bash
# Run basic tests
python -m pytest tests/ -v

# Test MATRIX MAXIMIZER
python matrix_maximizer.py
```

## 📋 Development Guidelines

### 🔄 Sync Best Practices
- **Always pull before starting work:** `git pull origin main`
- **Commit frequently:** `git add . && git commit -m "description"`
- **Push regularly:** `git push origin main`
- **Monitor git sync status** via `git status`

### 🚫 What NOT to Sync
- Virtual environments (`.venv/`, `venv/`)
- IDE settings (`.vscode/settings.json` - use workspace settings)
- OS-specific files (`.DS_Store`, `Thumbs.db`)
- Logs and temporary files

### ✅ What TO Sync
- Source code (`.py`, `.html`, `.css`, `.js`)
- Configuration files (shared settings)
- Documentation (`.md` files)
- Test files
- Git repository (`.git/`)

## 🧠 Key Components

### MATRIX MAXIMIZER System
- **`matrix_maximizer.py`** - Flask backend with real-time monitoring
- **`templates/matrix_maximizer.html`** - Advanced UI interface
- **`static/css/matrix_maximizer.css`** - Comprehensive styling
- **`static/js/matrix_maximizer.js`** - Interactive functionality

### Mobile Command Center
- **`mobile_command_center_simple.py`** - Unified command interface
- **Access at:** `http://localhost:8080/matrix`

### Memory Doctrine System
- **`unified_memory_doctrine_system.py`** - Cross-session memory management
- **`unified_memory_doctrine.json`** - Persistent memory storage

## 🔧 VS Code Live Share

For real-time collaborative coding:

1. Install "Live Share" extension on both systems
2. One developer starts a session: `Ctrl+Shift+P` → "Live Share: Start Collaboration Session"
3. Share the link with the other developer
4. Both can edit the same files simultaneously

## 🚀 Deployment

### Local Development
```bash
# Start Mobile Command Center
python mobile_command_center_simple.py

# Access interfaces:
# - Main: http://localhost:8080
# - MATRIX MAXIMIZER: http://localhost:8080/matrix
```

### Cross-Platform Testing
- Test on both macOS and Windows
- Verify git sync works correctly
- Check that all dependencies install on both systems

## 📞 Support

- **GitHub Repository:** https://github.com/ResonanceEnergy/Digital-Labour
- **Git Sync Issues:** Check `git status` and `git remote -v`
- **VS Code Issues:** Verify extensions are installed and settings are applied

## 📊 System Status

- **macOS (Quantum Quasar):** ✅ Primary development system
- **Windows (QUANTUM FORGE):** ✅ Secondary development system
- **Git Sync:** ✅ Active and tested
- **Git Integration:** ✅ Working across platforms
- **MATRIX MAXIMIZER:** ✅ Fully implemented and operational

---

**Last Updated:** February 21, 2026
**Platform:** Cross-platform (macOS ↔ Windows)
**Status:** 🟢 Active Development