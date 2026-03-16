"""
Executive Intelligence Briefings System
Phase 3: Crisis Management Protocols + Executive Briefings
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, asdict
from enum import Enum
import json
import logging
from pathlib import Path
import re

from crisis_management_framework import CrisisManagementFramework
from ceo_command_authority import CEOCommandAuthority
from executive_decision_matrix import DecisionMatrix

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BriefingPriority(Enum):
    """Briefing priority levels"""
    ROUTINE = "routine"
    IMPORTANT = "important"
    URGENT = "urgent"
    CRITICAL = "critical"
    EXISTENTIAL = "existential"


class IntelligenceSource(Enum):
    """Intelligence source types"""
    INTERNAL_MONITORING = "internal_monitoring"
    EXTERNAL_INTELLIGENCE = "external_intelligence"
    COUNCIL_52 = "council_52"
    MARKET_ANALYSIS = "market_analysis"
    TECHNICAL_SURVEILLANCE = "technical_surveillance"
    HUMAN_INTELLIGENCE = "human_intelligence"
    CYBER_INTELLIGENCE = "cyber_intelligence"


@dataclass
class IntelligenceReport:
    """Raw intelligence report"""
    report_id: str
    source: IntelligenceSource
    title: str
    content: str
    confidence: float
    collected_at: str
    expires_at: str
    tags: List[str]
    classification: str = "confidential"


@dataclass
class BriefingItem:
    """Individual briefing item"""
    item_id: str
    category: str
    title: str
    summary: str
    details: str
    priority: BriefingPriority
    intelligence_sources: List[IntelligenceSource]
    confidence_score: float
    action_required: bool
    action_deadline: Optional[str]
    related_decisions: List[str]


@dataclass
class ExecutiveBriefingPackage:
    """Complete executive briefing package"""
    briefing_id: str
    title: str
    executive_summary: str
    briefing_items: List[BriefingItem]
    key_recommendations: List[str]
    risk_assessment: Dict[str, Any]
    generated_at: str
    expires_at: str
    classification: str
    priority: BriefingPriority
    delivery_method: str = "secure_dashboard"


class ExecutiveBriefingsSystem:
    """
    Executive Intelligence Briefings System
    Generates and manages executive intelligence briefings
    """

    def __init__(self):
        """Initialize."""
        self.crisis_framework = CrisisManagementFramework()
        self.ceo_authority = CEOCommandAuthority()
        self.decision_matrix = DecisionMatrix()

        # Intelligence data
        self.intelligence_reports: Dict[str, IntelligenceReport] = {}
        self.briefing_packages: Dict[str, ExecutiveBriefingPackage] = {}
        self.active_briefings: List[str] = []

        # Briefing templates and protocols
        self.briefing_templates = self._load_briefing_templates()
        self.intelligence_filters = self._load_intelligence_filters()

        logger.info("Executive Briefings System initialized")

    def _load_briefing_templates(self) -> Dict[str, Dict[str, Any]]:
        """Load briefing templates for different scenarios"""
        return {
            "daily_executive": {
                "title_template": "Daily Executive Intelligence Briefing - {date}",
                "sections": ["strategic_overview", "operational_status", "risk_assessment", "key_decisions"],
                "priority": "routine",
                "frequency": "daily"
            },
            "crisis_response": {
                "title_template": "Crisis Response Briefing: {crisis_title}",
                "sections": ["crisis_summary", "immediate_actions", "executive_decisions", "communication_plan"],
                "priority": "critical",
                "frequency": "as_needed"
            },
            "strategic_decision": {
                "title_template": "Strategic Decision Briefing: {decision_title}",
                "sections": ["decision_context", "intelligence_assessment", "risk_analysis", "recommendations"],
                "priority": "important",
                "frequency": "as_needed"
            },
            "market_intelligence": {
                "title_template": "Market Intelligence Update - {date}",
                "sections": ["market_trends", "competitive_analysis", "regulatory_changes", "opportunities"],
                "priority": "important",
                "frequency": "weekly"
            }
        }

    def _load_intelligence_filters(self) -> Dict[str, Any]:
        """Load intelligence filtering and prioritization rules"""
        return {
            "priority_keywords": {
                "existential": ["existential", "catastrophic", "total_failure", "system_collapse"],
                "critical": ["critical", "emergency", "breach", "attack", "crisis"],
                "urgent": ["urgent", "immediate", "escalation", "violation", "non_compliant"],
                "important": ["important", "significant", "major", "substantial", "material"],
                "routine": ["routine", "normal", "standard", "regular", "ongoing"]
            },
            "source_reliability": {
                "council_52": 0.95,
                "internal_monitoring": 0.90,
                "external_intelligence": 0.85,
                "market_analysis": 0.80,
                "technical_surveillance": 0.85,
                "human_intelligence": 0.75,
                "cyber_intelligence": 0.80
            },
            "confidence_thresholds": {
                "existential": 0.90,
                "critical": 0.85,
                "urgent": 0.80,
                "important": 0.70,
                "routine": 0.50
            }
        }

    def collect_intelligence(self, source: IntelligenceSource, title: str,
                           content: str, confidence: float, tags: List[str],
                           classification: str = "confidential") -> str:
        """
        Collect and process new intelligence report

        Args:
            source: Intelligence source
            title: Report title
            content: Report content
            confidence: Confidence score (0-1)
            tags: Content tags
            classification: Security classification

        Returns:
            Report ID
        """
        report_id = f"intel_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        report = IntelligenceReport(
            report_id=report_id,
            source=source,
            title=title,
            content=content,
            confidence=confidence,
            collected_at=datetime.now().isoformat(),
            expires_at=(datetime.now() + timedelta(days=30)).isoformat(),
            tags=tags,
            classification=classification
        )

        self.intelligence_reports[report_id] = report

        # Analyze and potentially generate briefing
        self._analyze_intelligence(report)

        logger.info(
            f"Intelligence collected: {report_id} - {title} (Source: {source.value})")

        return report_id

    def _analyze_intelligence(self, report: IntelligenceReport):
        """Analyze intelligence report and determine if briefing is needed"""
        priority = self._determine_priority(report)

        if priority.value != "routine":
            # Generate briefing item
            briefing_item = self._create_briefing_item(report, priority)

            # Check if immediate briefing is needed
            if priority in [
                BriefingPriority.CRITICAL, BriefingPriority.EXISTENTIAL]:
                self._generate_immediate_briefing([briefing_item], priority)
            else:
                # Add to next regular briefing
                self._queue_for_next_briefing(briefing_item)

    def _determine_priority(
            self, report: IntelligenceReport) ->BriefingPriority:
        """Determine briefing priority based on content analysis"""
        content_lower = report.content.lower()
        title_lower = report.title.lower()

        # Check for priority keywords
        for priority_name, keywords in self.intelligence_filters["priority_keywords"].items():
            if any(
                keyword in content_lower or keyword in title_lower
                for keyword in keywords):
                return BriefingPriority(priority_name)

        # Check confidence against thresholds
        for priority_name, threshold in self.intelligence_filters[
            "confidence_thresholds"].items():
            if report.confidence >= threshold:
                return BriefingPriority(priority_name)

        return BriefingPriority.ROUTINE

    def _create_briefing_item(self, report: IntelligenceReport,
                              priority: BriefingPriority) ->BriefingItem:
        """Create a briefing item from intelligence report"""
        item_id = f"brief_item_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Extract key information
        summary = self._extract_summary(report.content)
        action_required = self._determine_action_required(report, priority)

        briefing_item = BriefingItem(
            item_id=item_id,
            category=self._categorize_content(report),
            title=report.title,
            summary=summary,
            details=report.content,
            priority=priority,
            intelligence_sources=[report.source],
            confidence_score=report.confidence,
            action_required=action_required,
            action_deadline=self._calculate_action_deadline(priority),
            related_decisions=[]
        )

        return briefing_item

    def _extract_summary(self, content: str) -> str:
        """Extract summary from content"""
        # Simple extraction - first 200 characters or first paragraph
        if len(content) <= 200:
            return content

        # Try to find first paragraph
        paragraphs = content.split('\n\n')
        if paragraphs and len(paragraphs[0]) <= 300:
            return paragraphs[0]

        # Fallback to first 200 characters
        return content[:200] + "..."

    def _categorize_content(self, report: IntelligenceReport) -> str:
        """Categorize intelligence content"""
        content_lower = report.content.lower()

        categories = {
            "security": ["security", "breach", "attack", "threat", "vulnerability"],
            "financial": ["financial", "market", "investment", "revenue", "cost"],
            "operational": ["operational", "system", "process", "efficiency", "performance"],
            "strategic": ["strategic", "competition", "market", "growth", "partnership"],
            "regulatory": ["regulatory", "compliance", "legal", "regulation", "law"],
            "technical": ["technical", "technology", "innovation", "development", "research"]
        }

        for category, keywords in categories.items():
            if any(keyword in content_lower for keyword in keywords):
                return category

        return "general"

    def _determine_action_required(self, report: IntelligenceReport,
                                   priority: BriefingPriority) ->bool:
        """Determine if action is required based on report and priority"""
        if priority in [
            BriefingPriority.CRITICAL, BriefingPriority.EXISTENTIAL]:
            return True

        # Check for action keywords
        action_keywords = ["action", "required",
            "immediate", "urgent", "respond", "address"]
        content_lower = report.content.lower()

        return any(keyword in content_lower for keyword in action_keywords)

    def _calculate_action_deadline(
            self, priority: BriefingPriority) ->Optional[str]:
        """Calculate action deadline based on priority"""
        now = datetime.now()

        if priority == BriefingPriority.EXISTENTIAL:
            return (now + timedelta(hours=1)).isoformat()
        elif priority == BriefingPriority.CRITICAL:
            return (now + timedelta(hours=4)).isoformat()
        elif priority == BriefingPriority.URGENT:
            return (now + timedelta(hours=24)).isoformat()
        elif priority == BriefingPriority.IMPORTANT:
            return (now + timedelta(days=3)).isoformat()

        return None

    def _generate_immediate_briefing(
            self, briefing_items: List[BriefingItem],
            priority: BriefingPriority):
        """Generate immediate executive briefing"""
        briefing_id = f"immediate_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Determine title based on items
        if len(briefing_items) == 1:
            title = f"Immediate Briefing: {briefing_items[0].title}"
        else:
            title = f"Immediate Executive Briefing - {
                len(briefing_items)}  Critical Items"

        # Create executive summary
        executive_summary = self._create_executive_summary(briefing_items)

        # Generate key recommendations
        key_recommendations = self._generate_recommendations(briefing_items)

        # Risk assessment
        risk_assessment = self._assess_risks(briefing_items)

        briefing_package = ExecutiveBriefingPackage(
            briefing_id=briefing_id, title=title,
            executive_summary=executive_summary, briefing_items=briefing_items,
            key_recommendations=key_recommendations,
            risk_assessment=risk_assessment,
            generated_at=datetime.now().isoformat(),
            expires_at=(datetime.now() +timedelta(hours=24)).isoformat(),
            classification="top_secret"
            if priority ==BriefingPriority.EXISTENTIAL else "confidential",
            priority=priority, delivery_method="immediate_notification")

        self.briefing_packages[briefing_id] = briefing_package
        self.active_briefings.append(briefing_id)

        # Deliver briefing
        self._deliver_briefing(briefing_package)

        logger.warning(
            f"Immediate briefing generated: {briefing_id} - {title}")

    def _queue_for_next_briefing(self, briefing_item: BriefingItem):
        """Queue briefing item for next regular briefing"""
        # In a real implementation, this would add to a queue for the next
        # scheduled briefing (daily, weekly, etc.)
        logger.info(f"Briefing item queued: {briefing_item.item_id}")

    def generate_daily_executive_briefing(self) -> str:
        """Generate daily executive intelligence briefing"""
        briefing_id = f"daily_{datetime.now().strftime('%Y%m%d')}"

        # Collect intelligence from last 24 hours
        recent_intelligence = self._get_recent_intelligence(hours=24)

        if not recent_intelligence:
            logger.info("No significant intelligence for daily briefing")
            return ""

        # Create briefing items
        briefing_items = []
        for report in recent_intelligence:
            priority = self._determine_priority(report)
            if priority.value != "routine":
                item = self._create_briefing_item(report, priority)
                briefing_items.append(item)

        if not briefing_items:
            logger.info("No briefing items meet threshold for daily briefing")
            return ""

        # Generate briefing package
        template = self.briefing_templates["daily_executive"]
        title = template["title_template"].format(
            date=datetime.now().strftime("%Y-%m-%d"))

        executive_summary = self._create_executive_summary(briefing_items)
        key_recommendations = self._generate_recommendations(briefing_items)
        risk_assessment = self._assess_risks(briefing_items)

        briefing_package = ExecutiveBriefingPackage(
            briefing_id=briefing_id,
            title=title,
            executive_summary=executive_summary,
            briefing_items=briefing_items,
            key_recommendations=key_recommendations,
            risk_assessment=risk_assessment,
            generated_at=datetime.now().isoformat(),
            expires_at=(datetime.now() + timedelta(hours=24)).isoformat(),
            classification="confidential",
            priority=BriefingPriority.ROUTINE,
            delivery_method="secure_dashboard"
        )

        self.briefing_packages[briefing_id] = briefing_package
        self.active_briefings.append(briefing_id)

        # Deliver briefing
        self._deliver_briefing(briefing_package)

        logger.info(f"Daily executive briefing generated: {briefing_id}")

        return briefing_id

    def _get_recent_intelligence(self, hours: int) -> List[IntelligenceReport]:
        """Get intelligence reports from the last N hours"""
        cutoff_time = datetime.now() - timedelta(hours=hours)

        recent_reports = []
        for report in self.intelligence_reports.values():
            report_time = datetime.fromisoformat(report.collected_at)
            if report_time >= cutoff_time:
                recent_reports.append(report)

        return recent_reports

    def _create_executive_summary(
            self, briefing_items: List[BriefingItem]) ->str:
        """Create executive summary from briefing items"""
        if not briefing_items:
            return "No significant intelligence to report."

        # Count by priority
        priority_counts = {}
        for item in briefing_items:
            priority_counts[item.priority.value] = priority_counts.get(
                item.priority.value, 0) + 1

        summary_parts = []
        if priority_counts.get("existential", 0) > 0:
            summary_parts.append(
                f"{priority_counts['existential']} existential threats")
        if priority_counts.get("critical", 0) > 0:
            summary_parts.append(
                f"{priority_counts['critical']} critical issues")
        if priority_counts.get("urgent", 0) > 0:
            summary_parts.append(f"{priority_counts['urgent']} urgent matters")
        if priority_counts.get("important", 0) > 0:
            summary_parts.append(
                f"{priority_counts['important']} important developments")

        if summary_parts:
            return f"Executive Intelligence Summary: {
                ', '.join(summary_parts)}  requiring attention."
        else:
            return "Routine intelligence update with no immediate action items."

    def _generate_recommendations(
            self, briefing_items: List[BriefingItem]) ->List[str]:
        """Generate key recommendations from briefing items"""
        recommendations = []

        # Group by category and priority
        high_priority_items = [item for item in briefing_items if item.priority in [
            BriefingPriority.CRITICAL, BriefingPriority.EXISTENTIAL]]

        if high_priority_items:
            recommendations.append(
                "Immediate executive attention required for critical items")

        action_items = [
            item for item in briefing_items if item.action_required]
        if action_items:
            recommendations.append(
                f"Action required on {len(action_items)} intelligence items")

        # Category-specific recommendations
        categories = set(item.category for item in briefing_items)
        for category in categories:
            category_items = [
                item for item in briefing_items if item.category == category]
            if len(category_items) > 1:
                recommendations.append(
                    f"Review {category} intelligence cluster ({len(category_items)} items)")

        return recommendations

    def _assess_risks(self, briefing_items: List[BriefingItem]) -> Dict[str, Any]:
        """Assess overall risk from briefing items"""
        risk_levels = {
            "existential": 0,
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0
        }

        for item in briefing_items:
            if item.priority == BriefingPriority.EXISTENTIAL:
                risk_levels["existential"] += 1
            elif item.priority == BriefingPriority.CRITICAL:
                risk_levels["critical"] += 1
            elif item.priority == BriefingPriority.URGENT:
                risk_levels["high"] += 1
            elif item.priority == BriefingPriority.IMPORTANT:
                risk_levels["medium"] += 1
            else:
                risk_levels["low"] += 1

        # Calculate overall risk score
        risk_score = (
            risk_levels["existential"] * 1.0 +
            risk_levels["critical"] * 0.8 +
            risk_levels["high"] * 0.6 +
            risk_levels["medium"] * 0.4 +
            risk_levels["low"] * 0.2
        ) / max(len(briefing_items), 1)

        return {
            "overall_risk_score": risk_score,
            "risk_breakdown": risk_levels,
            "highest_risk_level": max(risk_levels.keys(), key=lambda k: risk_levels[k]) if any(risk_levels.values()) else "none",
            "action_required_count": len([item for item in briefing_items if item.action_required])
        }

    def _deliver_briefing(self, briefing: ExecutiveBriefingPackage):
        """Deliver briefing to executives"""
        logger.info(
            f"Delivering briefing {briefing.briefing_id} via {briefing.delivery_method}")

        # In a real implementation, this would:
        # - Send to executive dashboards
        # - Trigger notifications
        # - Update CEO command interface
        # - Send secure communications

        # For now, log the delivery
        delivery_info = {
            "briefing_id": briefing.briefing_id,
            "title": briefing.title,
            "priority": briefing.priority.value,
            "delivered_at": datetime.now().isoformat(),
            "method": briefing.delivery_method
        }

        logger.info(
            f"Briefing delivered: {json.dumps(delivery_info, indent=2)}")

    def get_briefing_status(self) -> Dict[str, Any]:
        """Get current briefing system status"""
        return {
            "active_briefings": len(self.active_briefings),
            "total_intelligence_reports": len(self.intelligence_reports),
            "recent_briefings": [
                {
                    "id": bid,
                    "title": self.briefing_packages[bid].title,
                    "priority": self.briefing_packages[bid].priority.value,
                    "generated_at": self.briefing_packages[bid].generated_at
                }
                for bid in self.active_briefings[-5:]  # Last 5 briefings
            ],
            "intelligence_sources": list(set(report.source.value for report in self.intelligence_reports.values())),
            "system_status": "active"
        }

    def get_executive_briefing(self, briefing_id: str) -> Optional[Dict[str, Any]]:
        """Get specific executive briefing"""
        if briefing_id not in self.briefing_packages:
            return None

        briefing = self.briefing_packages[briefing_id]
        return {
            "briefing": asdict(briefing),
            "items": [asdict(item) for item in briefing.briefing_items]
        }


# Convenience functions
def collect_intelligence(source: str, title: str, content: str,
                        confidence: float, tags: List[str]) -> str:
    """Convenience function for intelligence collection"""
    system = ExecutiveBriefingsSystem()
    source_enum = IntelligenceSource(source)
    return system.collect_intelligence(
        source_enum, title, content, confidence, tags)


def generate_daily_briefing() -> str:
    """Generate daily executive briefing"""
    system = ExecutiveBriefingsSystem()
    return system.generate_daily_executive_briefing()


def get_briefing_status() -> Dict[str, Any]:
    """Get briefing system status"""
    system = ExecutiveBriefingsSystem()
    return system.get_briefing_status()


def get_executive_briefing(briefing_id: str) -> Optional[Dict[str, Any]]:
    """Get specific briefing"""
    system = ExecutiveBriefingsSystem()
    return system.get_executive_briefing(briefing_id)