#!/usr/bin/env python3
"""
Super Agency GitHub Integration Orchestrator
Automatically manages GitHub operations for the Resonance Energy portfolio
"""

import os
import sys
import json
import logging
from datetime import datetime
from pathlib import Path

# Add the github_integration directory to the path
sys.path.insert(0, str(Path(__file__).parent / "github_integration"))

def setup_logging():
    """Setup logging for autonomous operations"""
    log_dir = Path(__file__).parent / "logs"
    log_dir.mkdir(exist_ok=True)

    log_file = log_dir / f"github_orchestrator_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )

    return logging.getLogger(__name__)

def run_autonomous_sync():
    """Run the autonomous GitHub integration sync"""
    logger = setup_logging()

    logger.info("Super Agency GitHub Orchestrator Starting")
    logger.info("=" * 50)

    try:
        # Import the GitHub integration system
        from github_integration_system import GitHubIntegrationSystem

        # Initialize the system
        system = GitHubIntegrationSystem()
        logger.info("GitHub Integration System initialized")

        # Run autonomous sync
        logger.info("Starting autonomous portfolio sync...")
        results = system.autonomous_sync()

        # Log results
        logger.info("Sync Results:")
        logger.info(json.dumps(results, indent=2))

        if results.get('status') == 'success':
            logger.info("Autonomous sync completed successfully!")
            summary = results.get('summary', {})
            logger.info(f"Summary: {summary.get('successful', 0)} created, {summary.get('skipped', 0)} skipped, {summary.get('failed', 0)} failed")
            return True
        else:
            logger.error(f"Autonomous sync failed: {results.get('error', 'Unknown error')}")
            return False

    except ImportError as e:
        logger.error(f"Failed to import GitHub integration system: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error during autonomous sync: {e}")
        return False

def main():
    """Main orchestrator entry point"""
    success = run_autonomous_sync()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()