#!/usr/bin/env python3
"""
BIT RAGE LABOUR GitHub Integration Setup
Initializes the GitHub integration system for the Resonance Energy portfolio
"""

import os
import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime

def run_command(command: list, cwd: str = None) -> bool:
    """Run a shell command and return success status"""
    try:
        result = subprocess.run(
            command, cwd=cwd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Command failed: {' '.join(command)}")
            print(f"Error: {result.stderr}")
            return False
        return True
    except Exception as e:
        print(f"Exception running command: {e}")
        return False

def check_gh_cli() -> bool:
    """Check if GitHub CLI is installed and authenticated"""
    print("🔍 Checking GitHub CLI installation...")

    # Check if gh command exists
    if not run_command(["gh", "--version"]):
        print("❌ GitHub CLI not found. Please install it:")
        print("   - Download: https://cli.github.com/")
        print("   - macOS: brew install gh")
        print("   - Ubuntu: curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg")
        return False

    # Check authentication
    print("🔐 Checking GitHub CLI authentication...")
    if not run_command(["gh", "auth", "status"]):
        print("⚠️  GitHub CLI not authenticated. Running login...")
        if not run_command(["gh", "auth", "login"]):
            print("❌ GitHub authentication failed")
            return False

    print("✅ GitHub CLI ready")
    return True

def setup_virtual_environment() -> bool:
    """Set up Python virtual environment"""
    print("🐍 Setting up Python virtual environment...")

    venv_path = Path("venv")

    if not venv_path.exists():
        if not run_command([sys.executable, "-m", "venv", "venv"]):
            return False

    # Activate and install requirements
    if sys.platform == "win32":
        activate_cmd = ["venv\\Scripts\\activate.bat", "&&",
            "pip", "install", "-r", "requirements.txt"]
    else:
        activate_cmd = ["source", "venv/bin/activate", "&&",
            "pip", "install", "-r", "requirements.txt"]

    if not run_command(activate_cmd):
        return False

    print("✅ Virtual environment ready")
    return True

def create_initial_config() -> bool:
    """Create initial configuration files"""
    print("⚙️  Creating configuration files...")

    config_dir = Path("config")
    config_dir.mkdir(exist_ok=True)

    # Check if config already exists
    config_file = config_dir / "github_config.json"
    if config_file.exists():
        print("ℹ️  Configuration already exists")
        return True

    # Create basic config
    config = {
        "organization": "ResonanceEnergy",
        "default_visibility": "private",
        "branch_protection": {
            "required_reviews": 1,
            "require_code_owner_reviews": True,
            "dismiss_stale_reviews": True,
            "require_branches_up_to_date": True
        },
        "security_settings": {
            "enable_dependabot": True,
            "enable_codeql": True,
            "enable_secret_scanning": True
        }
    }

    try:
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
        print("✅ Configuration created")
        return True
    except Exception as e:
        print(f"❌ Failed to create config: {e}")
        return False

def test_integration() -> bool:
    """Test the GitHub integration system"""
    print("🧪 Testing GitHub integration...")

    try:
        from github_integration_system import GitHubIntegrationSystem
        system = GitHubIntegrationSystem()

        # Test basic functionality
        if hasattr(system, 'config') and system.config:
            print("✅ Integration system initialized successfully")
            return True
        else:
            print("❌ Integration system failed to initialize")
            return False

    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def create_setup_summary() -> None:
    """Create a setup summary file"""
    summary = f"""# BIT RAGE LABOUR GitHub Integration Setup Complete
## Setup Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

### ✅ Components Installed:
- GitHub CLI integration
- Python virtual environment
- Configuration files
- Integration system core

### 🚀 Next Steps:
1. Configure your GitHub token (optional, for API access):
   ```bash
   export GITHUB_TOKEN=your_token_here
   ```

2. Sync portfolio repositories:
   ```bash
   ./run_github_integration.sh sync
   ```

3. Create a new repository:
   ```bash
   ./run_github_integration.sh create my-project
   ```

### 📁 File Structure:
```
github_integration/
├── README.md                    # Documentation
├── github_integration_system.py # Core integration system
├── run_github_integration.sh    # Linux/Mac runner
├── run_github_integration.bat   # Windows runner
├── requirements.txt             # Python dependencies
├── config/
│   └── github_config.json       # Configuration
└── templates/
    ├── python-ci.yml           # CI/CD templates
    └── security-scan.yml       # Security scanning
```

### 🔧 Available Commands:
- `sync` - Sync all portfolio repositories
- `create <name>` - Create new repository
- `setup <name>` - Setup protection/security
- `pr <repo> <title> <body>` - Create pull request

---
*BIT RAGE LABOUR GitHub Integration v1.0*
"""

    try:
        with open("SETUP_COMPLETE.md", 'w') as f:
            f.write(summary)
        print("📋 Setup summary created: SETUP_COMPLETE.md")
    except Exception as e:
        print(f"⚠️  Failed to create setup summary: {e}")

def main():
    """Main setup function"""
    print("🚀 BIT RAGE LABOUR GitHub Integration Setup")
    print("=" * 50)

    success = True

    # Step 1: Check GitHub CLI
    if not check_gh_cli():
        success = False

    # Step 2: Setup virtual environment
    if success and not setup_virtual_environment():
        success = False

    # Step 3: Create configuration
    if success and not create_initial_config():
        success = False

    # Step 4: Test integration
    if success and not test_integration():
        success = False

    # Step 5: Create summary
    if success:
        create_setup_summary()

    print("\n" + "=" * 50)
    if success:
        print("🎉 GitHub Integration Setup Complete!")
        print("Run './run_github_integration.sh help' for usage instructions")
    else:
        print("❌ Setup failed. Please check the errors above.")
        sys.exit(1)

if __name__ == "__main__":
    main()