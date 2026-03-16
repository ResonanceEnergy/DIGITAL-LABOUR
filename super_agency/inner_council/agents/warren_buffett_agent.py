#!/usr/bin/env python3
"""
Warren Buffett Council Agent
Autonomous agent for monitoring Warren Buffett's public communications
Specialized in value investing, business analysis, and economic insights content analysis
"""

import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path
import requests
from dataclasses import dataclass

from .base_agent import BaseCouncilAgent, AgentCapabilities

logger = logging.getLogger(__name__)

@dataclass
class WarrenBuffettAgentContentAnalysis:
    """Specialized analysis for Warren Buffett content"""
    video_id: str
    title: str
    value_investing: List[str] = None
    business_analysis: List[str] = None
    economic_insights: List[str] = None
    leadership_principles: List[str] = None
    key_takeaways: List[str] = None

    def __post_init__(self):

        if self.value_investing is None:
            self.value_investing = []
        if self.business_analysis is None:
            self.business_analysis = []
        if self.economic_insights is None:
            self.economic_insights = []
        if self.leadership_principles is None:
            self.leadership_principles = []
        if self.key_takeaways is None:
            self.key_takeaways = []

class WarrenBuffettAgent(BaseCouncilAgent):
    """Autonomous agent for Warren Buffett public communications monitoring"""

    def __init__(self):
        super().__init__(
            name="Warren Buffett",
            channel_id="UC8Z-EwvkADzZHqXYbfAXNw",  # Berkshire Hathaway related content
            focus_areas=['Investing', 'Business', 'Economics', 'Leadership'],
            priority="high",
            capabilities=[
                AgentCapabilities.CONTENT_ANALYSIS,
                AgentCapabilities.TREND_ANALYSIS,
                AgentCapabilities.STRATEGIC_INSIGHT
            ]
        )

        # Warren Buffett specific topic patterns
        self.topic_patterns = {
            'investing': ['investing', 'stocks', 'value', 'berkshire', 'dividend'],
            'business': ['business', 'company', 'management', 'strategy', 'competition'],
            'economics': ['economy', 'market', 'recession', 'inflation', 'growth'],
            'leadership': ['leadership', 'integrity', 'long-term', 'patience', 'discipline']
        }

        # Initialize analysis storage
        self.analysis_history = []

    def analyze_content(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze Warren Buffett content for investment insights"""

        analysis = WarrenBuffettAgentContentAnalysis(
            video_id=content.get('video_id', ''),
            title=content.get('title', '')
        )

        # Extract value investing insights
        investing_keywords = ["investing", "value", "stocks",
            "berkshire", "dividend", "margin of safety"]
        if any(
            keyword in content.get('title', '').
            lower() or keyword in content.get('description', '').lower()
            for keyword in investing_keywords):
            analysis.value_investing.append(
                "Value investing principle discussed")

        # Extract business analysis
        business_keywords = ["business", "company",
            "management", "strategy", "competition", "moat"]
        if any(
            keyword in content.get('title', '').
            lower() or keyword in content.get('description', '').lower()
            for keyword in business_keywords):
            analysis.business_analysis.append(
                "Business analysis topic identified")

        # Extract economic insights
        economic_keywords = ["economy", "market",
            "recession", "inflation", "growth", "economic"]
        if any(
            keyword in content.get('title', '').
            lower() or keyword in content.get('description', '').lower()
            for keyword in economic_keywords):
            analysis.economic_insights.append("Economic insight presented")

        # Extract leadership principles
        leadership_keywords = ["leadership", "integrity",
            "long-term", "patience", "discipline", "character"]
        if any(
            keyword in content.get('title', '').
            lower() or keyword in content.get('description', '').lower()
            for keyword in leadership_keywords):
            analysis.leadership_principles.append(
                "Leadership principle discussed")

        # Generate key takeaways
        analysis.key_takeaways = self._generate_takeaways(content, analysis)

        result = {
            'agent': 'Warren Buffett',
            'analysis': analysis,
            'timestamp': datetime.now().isoformat(),
            'content_type': 'video',
            'insights_generated': len(analysis.key_takeaways)
        }

        self.analysis_history.append(result)
        return result

    def _generate_takeaways(
            self, content: Dict[str, Any],
            analysis: WarrenBuffettAgentContentAnalysis) ->List[str]:
        """Generate investment takeaways from Warren Buffett content"""
        takeaways = []

        # Value investing takeaways
        if analysis.value_investing:
            takeaways.append(
                "Buy wonderful businesses at fair prices, not fair businesses at wonderful prices")
            takeaways.append(
                "Margin of safety is the cornerstone of value investing")

        # Business analysis takeaways
        if analysis.business_analysis:
            takeaways.append(
                "Invest in businesses with durable competitive advantages")
            takeaways.append(
                "Management quality is paramount in long-term investing")

        # Economic insights takeaways
        if analysis.economic_insights:
            takeaways.append(
                "Economic cycles are inevitable but unpredictable in timing")
            takeaways.append(
                "Focus on business fundamentals rather than macroeconomic predictions")

        # Leadership takeaways
        if analysis.leadership_principles:
            takeaways.append(
                "Character and integrity compound over time like interest")
            takeaways.append(
                "Long-term thinking beats short-term optimization")

        return takeaways

    def get_strategic_insights(self) -> Dict[str, Any]:
        """Get aggregated strategic insights from Warren Buffett monitoring"""
        return {
            'agent': 'Warren Buffett',
            'total_analyses': len(self.analysis_history),
            'value_investing_insights': sum(len(a['analysis'].value_investing) for a in self.analysis_history),
            'business_analysis': sum(len(a['analysis'].business_analysis) for a in self.analysis_history),
            'economic_insights': sum(len(a['analysis'].economic_insights) for a in self.analysis_history),
            'leadership_principles': sum(len(a['analysis'].leadership_principles) for a in self.analysis_history),
            'key_themes': self._extract_key_themes(),
            'last_updated': datetime.now().isoformat()
        }

    def _extract_key_themes(self) -> List[str]:
        """Extract key themes from analysis history"""
        themes = []
        if any(len(a['analysis'].value_investing) >0
               for a in self.analysis_history):
            themes.append("Value investing and margin of safety")
        if any(len(a['analysis'].business_analysis) >0
               for a in self.analysis_history):
            themes.append("Business quality and competitive advantages")
        if any(len(a['analysis'].economic_insights) >0
               for a in self.analysis_history):
            themes.append("Economic cycles and market behavior")
        if any(len(a['analysis'].leadership_principles) >0
               for a in self.analysis_history):
            themes.append("Long-term thinking and integrity")
        return themes
