"""
NCC NCL Integration Adapter
Handles integration between Neural Command Center and Neural Cognitive Layer
"""

import json
import asyncio
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

from ..engine.intelligence_synthesizer import NCCIntelligenceSynthesizer
from ..engine.command_processor import NCCCommandProcessor
from ..contracts.schemas import IntelligenceRecord, create_intelligence_record, create_command_record

class NCCNCLAdapter:
    """
    Adapter for integrating NCC with NCL Second Brain system
    """

    def __init__(self, ncl_path: str = "../../ncl_second_brain"):
        self.ncl_path = Path(ncl_path)
        self.events_file = self.ncl_path / "events.ndjson"
        self.intelligence_synthesizer = NCCIntelligenceSynthesizer()
        self.command_processor = NCCCommandProcessor()

    async def capture_ncl_event(self, event_data: Dict[str, Any]) -> str:
        """
        Capture an event from NCL and process it through NCC

        Args:
            event_data: NCL event data

        Returns:
            Intelligence record ID
        """
        # Convert NCL event to NCC intelligence record
        intelligence_record = create_intelligence_record(
            id=f"ncl_{datetime.now().isoformat()} ", source="ncl_second_brain",
            type="system_log", content=event_data, confidence=0.9,
            metadata={"timestamp": event_data.get(
                          "timestamp", datetime.now().isoformat()),
                      "tags": event_data.get("tags", []),
                      "entities": event_data.get("entities", [])})

        # Process through intelligence synthesizer
        processed_intelligence = await self.intelligence_synthesizer.synthesize_intelligence([intelligence_record])

        # Generate insights and potential commands
        insights = await self.intelligence_synthesizer.generate_insights(processed_intelligence)

        # Create commands based on insights
        for insight in insights:
            if insight.get("actionable", False):
                command = create_command_record(
                    id=f"cmd_{datetime.now().isoformat()}",
                    type="intelligence_processing",
                    priority="medium",
                    payload={
                        "insight": insight,
                        "source": "ncl_integration"
                    },
                    requester="ncl_adapter",
                    description=f"Process NCL insight: {insight.get('description', '')}"
                )
                await self.command_processor.create_command(command)

        return intelligence_record.id

    async def read_ncl_events(self, since_timestamp: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Read events from NCL events file

        Args:
            since_timestamp: Only read events after this timestamp

        Returns:
            List of NCL events
        """
        events = []

        if not self.events_file.exists():
            return events

        with open(self.events_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    event = json.loads(line.strip())
                    if since_timestamp:
                        event_time = event.get("timestamp", "")
                        if event_time < since_timestamp:
                            continue
                    events.append(event)
                except json.JSONDecodeError:
                    continue

        return events

    async def sync_ncl_intelligence(self) -> Dict[str, Any]:
        """
        Synchronize intelligence between NCC and NCL

        Returns:
            Sync results
        """
        # Read recent NCL events
        recent_events = await self.read_ncl_events()

        processed_count = 0
        insights_generated = 0

        for event in recent_events:
            try:
                intelligence_id = await self.capture_ncl_event(event)
                processed_count += 1

                # Check if insights were generated
                # This is a simplified check - in practice would query the synthesizer
                insights_generated += 1

            except Exception as e:
                print(f"Error processing NCL event: {e}")
                continue

        return {
            "events_processed": processed_count,
            "insights_generated": insights_generated,
            "sync_timestamp": datetime.now().isoformat()
        }

    async def export_ncc_commands_to_ncl(self, command_ids: List[str]) -> Dict[str, Any]:
        """
        Export NCC commands to NCL for execution

        Args:
            command_ids: List of command IDs to export

        Returns:
            Export results
        """
        exported_commands = []

        for cmd_id in command_ids:
            try:
                # Get command details from NCC
                command = await self.command_processor.get_command(cmd_id)
                if command:
                    # Convert to NCL event format
                    ncl_event = {
                        "timestamp": command.created_at,
                        "type": "ncc_command",
                        "content": {
                            "command_id": command.id,
                            "command_type": command.type,
                            "payload": command.payload,
                            "priority": command.priority
                        },
                        "tags": ["ncc", "command", command.type],
                        "entities": [command.requester]
                    }

                    # Write to NCL events file
                    with open(self.events_file, 'a', encoding='utf-8') as f:
                        f.write(json.dumps(ncl_event) + '\n')

                    exported_commands.append(cmd_id)

            except Exception as e:
                print(f"Error exporting command {cmd_id}: {e}")
                continue

        return {
            "commands_exported": len(exported_commands),
            "export_timestamp": datetime.now().isoformat()
        }

    async def monitor_ncl_health(self) -> Dict[str, Any]:
        """
        Monitor NCL system health and report to NCC

        Returns:
            Health status report
        """
        health_status = {
            "ncl_path_exists": self.ncl_path.exists(),
            "events_file_exists": self.events_file.exists(),
            "last_event_timestamp": None,
            "total_events": 0,
            "health_score": 0.0
        }

        if health_status["events_file_exists"]:
            try:
                events = await self.read_ncl_events()
                health_status["total_events"] = len(events)

                if events:
                    # Get latest event timestamp
                    latest_event = max(
                        events, key=lambda x: x.get("timestamp", ""))
                    health_status["last_event_timestamp"] = latest_event.get(
                        "timestamp")

                    # Calculate health score based on recent activity
                    # This is a simplified calculation
                    health_status["health_score"] = min(
                        1.0, len(events) / 100.0)

            except Exception as e:
                health_status["error"] = str(e)
                health_status["health_score"] = 0.0

        return health_status