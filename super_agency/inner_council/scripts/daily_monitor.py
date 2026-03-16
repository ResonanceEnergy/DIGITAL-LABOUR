#!/usr/bin/env python3
"""
Daily Inner Council Monitor
Automated script to monitor council channels and generate intelligence reports
"""

import sys
import os
from pathlib import Path
from datetime import datetime
import logging

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from council import InnerCouncil
from integrations.ncl_integration import NCLIntegration
from integrations.orchestrator_integration import OrchestratorIntegration

# Configure logging
_log_dir = Path(__file__).resolve().parent.parent / "logs"
_log_dir.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(_log_dir / 'daily_monitor.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def ensure_directories():
    """Ensure all required directories exist"""
    dirs = [
        "inner_council/logs",
        "inner_council/data",
        "inner_council/data/daily_reports",
        "decisions",
        "reports/daily"
    ]

    for dir_path in dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)

def main():
    """Main daily monitoring function"""

    logger.info("🚀 Starting Inner Council Daily Monitor")

    try:
        # Ensure directories exist
        ensure_directories()

        # Initialize systems
        logger.info("🔧 Initializing Inner Council systems...")
        council = InnerCouncil()
        ncl_integration = NCLIntegration()
        orchestrator_integration = OrchestratorIntegration()

        # Generate daily report
        logger.info("📊 Generating daily intelligence report...")
        daily_report = council.generate_daily_report()

        # Log report summary
        logger.info(f"📈 Report Summary: {daily_report.get('council_members_monitored')} members monitored, "
                   f"{daily_report.get('new_content_analyzed')} content items analyzed")

        # Store in NCL
        logger.info("🧠 Storing analysis in NCL knowledge graph...")
        ncl_integration.store_daily_report(daily_report)

        # Process for orchestrator
        logger.info("🎯 Processing intelligence for DIGITAL LABOUR operations...")
        processing_result = orchestrator_integration.process_council_intelligence(
            daily_report)

        # Update daily report
        logger.info("📋 Updating daily operations report...")
        orchestrator_integration.update_daily_report(daily_report)

        # Log completion
        logger.info("✅ Daily Inner Council monitoring completed successfully")
        logger.info(f"📊 Proposal ID: {processing_result.get('proposal_id')}")
        logger.info(
            f"🎯 Requires Council Review: {processing_result.get('requires_council_review')}")

        # Print summary to console
        print("\n" + "="*60)
        print("🎉 INNER COUNCIL DAILY MONITOR - COMPLETED")
        print("="*60)
        print(f"📅 Date: {daily_report.get('date')}")
        print(
            f"👥 Council Members: {daily_report.get('council_members_monitored')}")
        print(
            f"📺 Content Analyzed: {daily_report.get('new_content_analyzed')}")
        print(f"💡 Key Insights: {len(daily_report.get('key_insights', []))}")
        print(
            f"📋 Recommendations: {len(daily_report.get('policy_recommendations', []))}")
        print(f"🎯 Actions: {len(daily_report.get('strategic_actions', []))}")
        print(f"⚠️  Risk Alerts: {len(daily_report.get('risk_alerts', []))}")
        print(f"🆔 Proposal ID: {processing_result.get('proposal_id')}")
        print("="*60)

        return True

    except Exception as e:
        logger.error(f"❌ Daily monitor failed: {e}", exc_info=True)
        print(f"\n❌ ERROR: Daily monitor failed - {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

# Alias for backward compatibility
run_daily_monitor = main