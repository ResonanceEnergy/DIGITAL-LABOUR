#!/usr/bin/env python3
"""
SYSTEM VALIDATION AND REPAIR SCRIPT
Comprehensive fix for DIGITAL LABOUR system components
"""

import sys
import os
import subprocess
import json
from pathlib import Path
from datetime import datetime
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - SYSTEM_FIX - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SystemValidator:
    """Comprehensive system validation and repair"""

    def __init__(self):
        self.workspace_root = Path(__file__).parent
        self.issues_found = []
        self.fixes_applied = []

    def log_issue(self, issue: str):
        """Log an issue found"""
        logger.warning(f"❌ ISSUE: {issue}")
        self.issues_found.append(issue)

    def log_fix(self, fix: str):
        """Log a fix applied"""
        logger.info(f"✅ FIX: {fix}")
        self.fixes_applied.append(fix)

    def validate_python_environment(self):
        """Validate Python environment"""
        logger.info("🔍 Validating Python environment...")

        # Check Python version
        version = sys.version_info
        if version.major < 3 or (version.major == 3 and version.minor < 8):
            self.log_issue(f"Python version {version.major}.{version.minor} is too old. Need 3.8+")
        else:
            logger.info(f"✅ Python {version.major}.{version.minor}.{version.micro} OK")

        # Check required packages
        required_packages = ['flask', 'psutil', 'requests']
        missing_packages = []

        for package in required_packages:
            try:
                __import__(package)
                logger.info(f"✅ {package} available")
            except ImportError:
                missing_packages.append(package)
                self.log_issue(f"Missing required package: {package}")

        if missing_packages:
            logger.info(f"📦 Installing missing packages: {missing_packages}")
            try:
                subprocess.check_call([sys.executable, '-m', 'pip', 'install'] + missing_packages)
                self.log_fix(f"Installed missing packages: {missing_packages}")
            except subprocess.CalledProcessError as e:
                self.log_issue(f"Failed to install packages: {e}")

    def validate_file_structure(self):
        """Validate file structure"""
        logger.info("🔍 Validating file structure...")

        required_files = [
            'matrix_maximizer.py',
            'qforge_launcher.py',
            'qusar_init.py',
            'celebrity_council_orchestrator.py',
            'operations_centers.py'
        ]

        for file in required_files:
            if (self.workspace_root / file).exists():
                logger.info(f"✅ {file} exists")
            else:
                self.log_issue(f"Missing required file: {file}")

        # Check directories
        required_dirs = [
            'qforge',
            'repos/QUSAR',
            'Digital-Labour',
            'musk_innovations',
            'dimon_finance',
            'buffett_investments',
            'cohen_retail',
            'executive_council_results'
        ]

        for dir_path in required_dirs:
            if (self.workspace_root / dir_path).exists():
                logger.info(f"✅ {dir_path}/ exists")
            else:
                logger.info(f"📁 Creating missing directory: {dir_path}")
                (self.workspace_root / dir_path).mkdir(parents=True, exist_ok=True)
                self.log_fix(f"Created directory: {dir_path}")

    def validate_imports(self):
        """Validate critical imports"""
        logger.info("🔍 Validating critical imports...")

        test_imports = [
            ('matrix_maximizer', 'EnhancedMatrixMaximizer'),
            ('qforge.qforge_executor', 'QFORGEExecutor'),
            ('repos.QUSAR.qusar_orchestrator', 'QUSAROrchestrator'),
            ('celebrity_council_orchestrator', 'CelebrityCouncilOrchestrator'),
            ('operations_centers', None)
        ]

        for module, class_name in test_imports:
            try:
                module_obj = __import__(module, fromlist=[class_name] if class_name else [])
                if class_name and not hasattr(module_obj, class_name):
                    self.log_issue(f"Class {class_name} not found in {module}")
                else:
                    logger.info(f"✅ {module} import OK")
            except ImportError as e:
                self.log_issue(f"Failed to import {module}: {e}")
            except Exception as e:
                self.log_issue(f"Error importing {module}: {e}")

    def fix_qforge_launcher(self):
        """Fix QFORGE launcher path issues"""
        logger.info("🔧 Fixing QFORGE launcher...")

        launcher_path = self.workspace_root / 'qforge_launcher.py'
        if launcher_path.exists():
            with open(launcher_path, 'r') as f:
                content = f.read()

            # Fix path issue - should use absolute path
            if 'qforge_dir = Path(__file__).parent / "qforge"' in content:
                fixed_content = content.replace(
                    'qforge_dir = Path(__file__).parent / "qforge"',
                    'qforge_dir = Path(__file__).parent / "qforge"\n    qforge_dir = qforge_dir.resolve()'
                )

                with open(launcher_path, 'w') as f:
                    f.write(fixed_content)

                self.log_fix("Fixed QFORGE launcher path resolution")

    def fix_qusar_init(self):
        """Fix QUSAR initialization"""
        logger.info("🔧 Fixing QUSAR initialization...")

        init_path = self.workspace_root / 'repos' / 'QUSAR' / 'qusar_init.py'
        if init_path.exists():
            with open(init_path, 'r') as f:
                content = f.read()

            # Fix localhost connection for development
            if 'qforge_host="192.168.1.200"' in content:
                fixed_content = content.replace(
                    'qforge_host="192.168.1.200"',
                    'qforge_host="127.0.0.1"'
                )

                with open(init_path, 'w') as f:
                    f.write(fixed_content)

                self.log_fix("Fixed QUSAR host to localhost for development")

    def create_missing_executors(self):
        """Create missing executor files if needed"""
        logger.info("🔧 Creating missing executor files...")

        # Check if qforge_executor exists
        executor_path = self.workspace_root / 'qforge' / 'qforge_executor.py'
        if not executor_path.exists():
            logger.info("📝 Creating qforge_executor.py...")

            executor_content = '''#!/usr/bin/env python3
"""
QFORGE Executor - Task Execution Layer
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

from sasp_protocol import SASPServer, SASPSecurityManager, SASPMessage

logger = logging.getLogger(__name__)

class QFORGEExecutor:
    """QFORGE task execution engine"""

    def __init__(self):
        self.sasp_server = None
        self.tasks = {}
        self.security_manager = SASPSecurityManager("qforge-secret-key-change-in-production")
        logger.info("🎯 QFORGE Executor initialized")

    def start(self):
        """Start QFORGE services"""
        logger.info("🚀 Starting QFORGE services...")

        # Initialize SASP server
        self.sasp_server = SASPServer(
            host="127.0.0.1",
            port=8888,
            security_manager=self.security_manager
        )

        logger.info("✅ QFORGE services started on localhost:8888")

    def stop(self):
        """Stop QFORGE services"""
        if self.sasp_server:
            self.sasp_server.stop()
        logger.info("🛑 QFORGE services stopped")
'''

            with open(executor_path, 'w') as f:
                f.write(executor_content)

            self.log_fix("Created qforge_executor.py")

    def validate_and_fix_all(self):
        """Run all validations and fixes"""
        logger.info("🔧 Starting comprehensive system validation and repair...")

        self.validate_python_environment()
        self.validate_file_structure()
        self.validate_imports()
        self.fix_qforge_launcher()
        self.fix_qusar_init()
        self.create_missing_executors()

        # Summary
        logger.info("="*60)
        logger.info("SYSTEM VALIDATION COMPLETE")
        logger.info("="*60)
        logger.info(f"Issues Found: {len(self.issues_found)}")
        logger.info(f"Fixes Applied: {len(self.fixes_applied)}")

        if self.issues_found:
            logger.warning("ISSUES FOUND:")
            for issue in self.issues_found:
                logger.warning(f"  - {issue}")

        if self.fixes_applied:
            logger.info("FIXES APPLIED:")
            for fix in self.fixes_applied:
                logger.info(f"  - {fix}")

        logger.info("="*60)

        return len(self.issues_found) == 0

def main():
    """Main validation function"""
    validator = SystemValidator()
    success = validator.validate_and_fix_all()

    if success:
        logger.info("🎉 System validation PASSED - all components ready")
        return 0
    else:
        logger.error("❌ System validation FAILED - issues remain")
        return 1

if __name__ == "__main__":
    sys.exit(main())
