#!/usr/bin/env python3
"""
Executive Council Scheduler Agent
Compiles YouTube intelligence updates hourly and distributes to Second Brain and Galactia
"""

import asyncio
import json
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging
import schedule
from pathlib import Path

class ExecutiveCouncilScheduler:
    """Scheduler agent for compiling and distributing YouTube intelligence updates"""

    def __init__(self):
        self.intelligence_data = []
        self.scheduler_active = False
        self.last_compilation = None
        self.setup_logging()
        self.load_intelligence_sources()

    def setup_logging(self):
        """Setup scheduler logging"""
        os.makedirs("executive_scheduler", exist_ok=True)

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - EXECUTIVE SCHEDULER - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('executive_scheduler/scheduler_log.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger("ExecutiveCouncilScheduler")

    def load_intelligence_sources(self):
        """Load intelligence source configurations"""
        self.sources = {
            "inner_council_monitor": "youtube_intelligence_monitor.py",
            "council_channels": "inner_council_config.json",
            "second_brain": "second_brain_storage/",
            "galactia": "galactia_decision_system/"
        }

    async def compile_youtube_updates(self) -> Dict:
        """Compile YouTube intelligence updates from Inner Council monitoring"""

        self.logger.info("Compiling YouTube intelligence updates")

        updates = {
            "timestamp": datetime.now().isoformat(),
            "council_members": [],
            "new_videos": [],
            "transcripts_analyzed": [],
            "insights_generated": [],
            "decision_feed": []
        }

        try:
            # Load Inner Council configuration
            config_path = Path("inner_council_config.json")
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config = json.load(f)

                # Get active council channels (29 total: 25 thought leaders + 4 executive)
                active_channels = []
                for channel in config.get("youtube_channels", {}).get("inner_council", []):
                    if channel.get("active", False):
                        active_channels.append(channel)

                updates["council_members"] = active_channels

            # Check for recent intelligence data
            intelligence_dir = Path("intelligence_updates")
            if intelligence_dir.exists():
                recent_files = list(intelligence_dir.glob("*.json"))
                recent_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)

                for file_path in recent_files[:10]:  # Last 10 updates
                    try:
                        with open(file_path, 'r') as f:
                            data = json.load(f)
                            updates["insights_generated"].append(data)
                    except Exception as e:
                        self.logger.error(f"Error reading intelligence file {file_path}: {e}")

            # Check Second Brain for recent entries
            second_brain_dir = Path("second_brain_storage")
            if second_brain_dir.exists():
                recent_entries = list(second_brain_dir.glob("*.json"))
                recent_entries.sort(key=lambda x: x.stat().st_mtime, reverse=True)

                for entry in recent_entries[:5]:  # Last 5 entries
                    try:
                        with open(entry, 'r') as f:
                            data = json.load(f)
                            updates["decision_feed"].append(data)
                    except Exception as e:
                        self.logger.error(f"Error reading Second Brain entry {entry}: {e}")

        except Exception as e:
            self.logger.error(f"Error compiling YouTube updates: {e}")

        self.last_compilation = datetime.now()
        return updates

    async def send_to_second_brain(self, updates: Dict):
        """Send compiled updates to Second Brain knowledge storage"""

        self.logger.info("Sending updates to Second Brain")

        try:
            second_brain_dir = Path("second_brain_storage")
            second_brain_dir.mkdir(exist_ok=True)

            filename = f"executive_council_update_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            filepath = second_brain_dir / filename

            with open(filepath, 'w') as f:
                json.dump(updates, f, indent=2)

            self.logger.info(f"Successfully stored updates in Second Brain: {filename}")

        except Exception as e:
            self.logger.error(f"Error sending to Second Brain: {e}")

    async def send_to_galactia(self, updates: Dict):
        """Send compiled updates to Galactia decision system"""

        self.logger.info("Sending updates to Galactia decision system")

        try:
            galactia_dir = Path("galactia_decision_system")
            galactia_dir.mkdir(exist_ok=True)

            # Create decision input for Galactia
            decision_input = {
                "source": "Executive Council Scheduler",
                "timestamp": updates["timestamp"],
                "intelligence_summary": {
                    "total_council_members": len(updates.get("council_members", [])),
                    "insights_count": len(updates.get("insights_generated", [])),
                    "recent_decisions": len(updates.get("decision_feed", []))
                },
                "key_insights": self.extract_key_insights(updates),
                "recommendations": self.generate_recommendations(updates)
            }

            filename = f"galactia_input_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            filepath = galactia_dir / filename

            with open(filepath, 'w') as f:
                json.dump(decision_input, f, indent=2)

            self.logger.info(f"Successfully sent decision input to Galactia: {filename}")

        except Exception as e:
            self.logger.error(f"Error sending to Galactia: {e}")

    def extract_key_insights(self, updates: Dict) -> List[str]:
        """Extract key insights from compiled updates"""

        insights = []
        for insight in updates.get("insights_generated", []):
            if "key_findings" in insight:
                insights.extend(insight["key_findings"])

        return insights[:10]  # Limit to top 10

    def generate_recommendations(self, updates: Dict) -> List[str]:
        """Generate strategic recommendations based on updates"""

        recommendations = []

        member_count = len(updates.get("council_members", []))
        insight_count = len(updates.get("insights_generated", []))

        if member_count >= 25:
            recommendations.append("Inner Council intelligence network fully operational")

        if insight_count > 0:
            recommendations.append(f"Process {insight_count} new insights for strategic decision-making")

        recommendations.append("Schedule Executive Council meeting to review intelligence updates")
        recommendations.append("Update RAM Doctrine with latest council insights")

        return recommendations

    async def hourly_compilation_cycle(self):
        """Execute hourly compilation and distribution cycle"""

        self.logger.info("Starting hourly Executive Council compilation cycle")

        try:
            # Compile updates
            updates = await self.compile_youtube_updates()

            # Send to Second Brain
            await self.send_to_second_brain(updates)

            # Send to Galactia
            await self.send_to_galactia(updates)

            self.logger.info("Hourly compilation cycle completed successfully")

        except Exception as e:
            self.logger.error(f"Error in hourly compilation cycle: {e}")

    def start_hourly_scheduler(self):
        """Start the hourly scheduler"""

        self.logger.info("Starting Executive Council hourly scheduler")

        # Schedule hourly compilation
        schedule.every().hour.do(lambda: asyncio.run(self.hourly_compilation_cycle()))

        self.scheduler_active = True

        # Run initial compilation
        asyncio.run(self.hourly_compilation_cycle())

        # Keep scheduler running
        while self.scheduler_active:
            schedule.run_pending()
            time.sleep(60)  # Check every minute

    def stop_scheduler(self):
        """Stop the hourly scheduler"""

        self.logger.info("Stopping Executive Council scheduler")
        self.scheduler_active = False

async def main():
    """Main execution function"""
    scheduler = ExecutiveCouncilScheduler()
    scheduler.start_hourly_scheduler()

if __name__ == "__main__":
    asyncio.run(main())
