#!/usr/bin/env python3
"""
Inner Council NCL Integration
Store council analysis results in the NCL knowledge graph
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)

class NCLIntegration:
    """Integration between Inner Council and NCL knowledge graph"""

    def __init__(self, ncl_events_path: str = "NCL/events.ndjson"):
        self.ncl_events_path = Path(ncl_events_path)
        self.ensure_ncl_file()

    def ensure_ncl_file(self):
        """Ensure NCL events file exists"""
        if not self.ncl_events_path.exists():
            self.ncl_events_path.parent.mkdir(parents=True, exist_ok=True)
            # Create empty file
            with open(self.ncl_events_path, 'w') as f:
                pass

    def store_council_analysis(self, analysis_data: Dict[str, Any]):
        """Store Inner Council analysis in NCL"""

        # Create NCL event record
        ncl_event = {
            "type": "inner_council_analysis",
            "timestamp": datetime.now().isoformat(),
            "data": {
                "council_member": analysis_data.get("member_name"),
                "video_id": analysis_data.get("video_id"),
                "content_title": analysis_data.get("title"),
                "analysis_type": "strategic_intelligence",
                "key_insights": analysis_data.get("key_insights", []),
                "policy_implications": analysis_data.get("policy_implications", []),
                "strategic_recommendations": analysis_data.get("strategic_recommendations", []),
                "risk_assessments": analysis_data.get("risk_assessments", []),
                "confidence_score": 0.85,  # Placeholder confidence score
                "impact_potential": "high",
                "processed_at": analysis_data.get("analyzed_at").isoformat() if hasattr(analysis_data.get("analyzed_at"), 'isoformat') else datetime.now().isoformat()
            }
        }

        # Append to NCL events file
        with open(self.ncl_events_path, 'a') as f:
            f.write(json.dumps(ncl_event) + '\n')

        logger.info(
            f"Stored Inner Council analysis for {analysis_data.get('member_name')} in NCL")

    def store_daily_report(self, daily_report: Dict[str, Any]):
        """Store daily council report in NCL"""

        ncl_event = {
            "type": "inner_council_daily_report",
            "timestamp": datetime.now().isoformat(),
            "data": {
                "report_date": daily_report.get("date"),
                "council_members_monitored": daily_report.get("council_members_monitored"),
                "new_content_analyzed": daily_report.get("new_content_analyzed"),
                "key_insights_count": len(daily_report.get("key_insights", [])),
                "policy_recommendations_count": len(daily_report.get("policy_recommendations", [])),
                "strategic_actions_count": len(daily_report.get("strategic_actions", [])),
                "risk_alerts_count": len(daily_report.get("risk_alerts", [])),
                "summary": {
                    "top_insights": daily_report.get("key_insights", [])[:5],
                    "critical_recommendations": daily_report.get("policy_recommendations", [])[:3],
                    "urgent_actions": daily_report.get("strategic_actions", [])[:3]
                },
                "generated_at": datetime.now().isoformat()
            }
        }

        # Append to NCL events file
        with open(self.ncl_events_path, 'a') as f:
            f.write(json.dumps(ncl_event) + '\n')

        logger.info(f"Stored daily Inner Council report in NCL")

    def store_insight(self, insight: Dict[str, Any]) -> bool:
        """Store a generic insight in NCL"""

        try:
            # Ensure timestamp
            if "timestamp" not in insight:
                insight["timestamp"] = datetime.now().isoformat()

            # Append to NCL events file
            with open(self.ncl_events_path, 'a') as f:
                f.write(json.dumps(insight) + '\n')

            logger.info(f"Stored insight of type {insight.get('type')} in NCL")
            return True
        except Exception as e:
            logger.error(f"Failed to store insight: {e}")
            return False

    def query_council_insights(
            self, query_type: str="recent", limit: int=10) ->List[Dict]:
        """Query council insights from NCL"""

        insights = []

        if not self.ncl_events_path.exists():
            return insights

        with open(self.ncl_events_path, 'r') as f:
            for line in f:
                if line.strip():
                    try:
                        event = json.loads(line.strip())
                        if event.get("type") in["inner_council_analysis",
                            "inner_council_daily_report"]:
                            insights.append(event)
                    except json.JSONDecodeError:
                        continue

        # Sort by timestamp (most recent first)
        insights.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

        if query_type == "recent":
            return insights[:limit]
        elif query_type == "analysis_only":
            return [i for i in insights if i.get("type") == "inner_council_analysis"][:limit]
        elif query_type == "reports_only":
            return [i for i in insights if i.get("type") == "inner_council_daily_report"][:limit]

        return insights[:limit]

    def get_council_member_insights(
            self, member_name: str, limit: int=5) ->List[Dict]:
        """Get insights from a specific council member"""

        all_insights = self.query_council_insights(
            limit=1000)  # Get more to filter
        member_insights = []

        for insight in all_insights:
            if insight.get("data", {}).get("council_member") == member_name:
                member_insights.append(insight)

        return member_insights[:limit]

    def get_topic_insights(
            self, topic_keywords: List[str],
            limit: int=10) ->List[Dict]:
        """Get insights related to specific topics"""

        all_insights = self.query_council_insights(limit=1000)
        topic_insights = []

        for insight in all_insights:
            data = insight.get("data", {})
            content = ""

            # Check various fields for topic keywords
            if "key_insights" in data:
                content += " ".join(data["key_insights"])
            if "policy_implications" in data:
                content += " ".join(data["policy_implications"])
            if "strategic_recommendations" in data:
                content += " ".join(data["strategic_recommendations"])

            # Check if any topic keywords are in the content
            content_lower = content.lower()
            if any(keyword.lower() in content_lower
                   for keyword in topic_keywords):
                topic_insights.append(insight)

        return topic_insights[:limit]

    def generate_ncl_summary(self) -> Dict[str, Any]:
        """Generate summary of council insights stored in NCL"""

        all_insights = self.query_council_insights(limit=1000)

        summary = {
            "total_insights": len(all_insights),
            "analysis_records": len([i for i in all_insights if i.get("type") == "inner_council_analysis"]),
            "daily_reports": len([i for i in all_insights if i.get("type") == "inner_council_daily_report"]),
            "council_members_covered": len(set(
                i.get("data", {}).get("council_member")
                for i in all_insights
                if i.get("data", {}).get("council_member")
            )),
            "date_range": {
                "earliest": min((i.get("timestamp") for i in all_insights), default=None),
                "latest": max((i.get("timestamp") for i in all_insights), default=None)
            },
            "top_themes": self._extract_top_themes(all_insights),
            "generated_at": datetime.now().isoformat()
        }

        return summary

    def _extract_top_themes(
            self, insights: List[Dict],
            top_n: int=10) ->List[str]:
        """Extract most common themes from insights"""

        from collections import Counter

        all_text = []
        for insight in insights:
            data = insight.get("data", {})
            for field in [
                "key_insights", "policy_implications",
                "strategic_recommendations"]:
                if field in data and isinstance(data[field], list):
                    all_text.extend(data[field])

        # Simple keyword extraction (could be enhanced with NLP)
        words = []
        for text in all_text:
            words.extend(text.lower().split())

        # Filter out common stop words
        stop_words = {
            'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of',
            'with', 'by', 'an', 'a', 'as', 'is', 'are', 'was', 'were', 'be',
            'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
            'would', 'could', 'should', 'may', 'might', 'must', 'can', 'this',
            'that', 'these', 'those'}
        filtered_words = [
            word for word in words if word not in stop_words and len(word) > 3]

        # Get most common words
        word_counts = Counter(filtered_words)
        top_themes = [word for word, count in word_counts.most_common(top_n)]

        return top_themes