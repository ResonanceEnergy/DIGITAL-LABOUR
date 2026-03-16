#!/usr/bin/env python3
"""
Malcolm Gladwell Council Agent
Autonomous agent for monitoring Malcolm Gladwell's public communications
Specialized in psychology, social science, and behavioral insights content analysis
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
class MalcolmGladwellAgentContentAnalysis:
    """Specialized analysis for Malcolm Gladwell content"""
    video_id: str
    title: str
    behavioral_psychology: List[str] = None
    social_science: List[str] = None
    tipping_points: List[str] = None
    outlier_analysis: List[str] = None
    key_takeaways: List[str] = None

    def __post_init__(self):

        if self.behavioral_psychology is None:
            self.behavioral_psychology = []
        if self.social_science is None:
            self.social_science = []
        if self.tipping_points is None:
            self.tipping_points = []
        if self.outlier_analysis is None:
            self.outlier_analysis = []
        if self.key_takeaways is None:
            self.key_takeaways = []

class MalcolmGladwellAgent(BaseCouncilAgent):
    """Autonomous agent for Malcolm Gladwell public communications monitoring"""

    def __init__(self):
        super().__init__(
            name="Malcolm Gladwell",
            channel_id="UC8Z-EwvkADzZHqXYbfAXNw",  # Malcolm Gladwell related content
            focus_areas=['Psychology', 'Social Science',
                'Behavior', 'Culture'],
            priority="high",
            capabilities=[
                AgentCapabilities.CONTENT_ANALYSIS,
                AgentCapabilities.TREND_ANALYSIS,
                AgentCapabilities.STRATEGIC_INSIGHT
            ]
        )

        # Malcolm Gladwell specific topic patterns
        self.topic_patterns = {
            'psychology': ['psychology', 'behavior', 'cognitive', 'mind', 'thinking'],
            'social': ['social', 'society', 'culture', 'group', 'community'],
            'tipping': ['tipping point', 'epidemic', 'spread', 'viral', 'contagious'],
            'outlier': ['outlier', 'success', 'achievement', 'talent', 'opportunity']
        }

        # Initialize analysis storage
        self.analysis_history = []

    def analyze_content(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze Malcolm Gladwell content for behavioral insights"""

        analysis = MalcolmGladwellAgentContentAnalysis(
            video_id=content.get('video_id', ''),
            title=content.get('title', '')
        )

        # Extract behavioral psychology insights
        psychology_keywords = ["psychology", "behavior",
            "cognitive", "mind", "thinking", "decision"]
        if any(
            keyword in content.get('title', '').
            lower() or keyword in content.get('description', '').lower()
            for keyword in psychology_keywords):
            analysis.behavioral_psychology.append(
                "Behavioral psychology insight presented")

        # Extract social science insights
        social_keywords = ["social", "society", "culture",
            "group", "community", "social science"]
        if any(
            keyword in content.get('title', '').
            lower() or keyword in content.get('description', '').lower()
            for keyword in social_keywords):
            analysis.social_science.append("Social science analysis discussed")

        # Extract tipping points insights
        tipping_keywords = ["tipping point", "epidemic",
            "spread", "viral", "contagious", "threshold"]
        if any(
            keyword in content.get('title', '').
            lower() or keyword in content.get('description', '').lower()
            for keyword in tipping_keywords):
            analysis.tipping_points.append("Tipping point concept explored")

        # Extract outlier analysis insights
        outlier_keywords = ["outlier", "success", "achievement",
            "talent", "opportunity", "10,000 hours"]
        if any(
            keyword in content.get('title', '').
            lower() or keyword in content.get('description', '').lower()
            for keyword in outlier_keywords):
            analysis.outlier_analysis.append("Outlier analysis presented")

        # Generate key takeaways
        analysis.key_takeaways = self._generate_takeaways(content, analysis)

        result = {
            'agent': 'Malcolm Gladwell',
            'analysis': analysis,
            'timestamp': datetime.now().isoformat(),
            'content_type': 'video',
            'insights_generated': len(analysis.key_takeaways)
        }

        self.analysis_history.append(result)
        return result

    def _generate_takeaways(
            self, content: Dict[str, Any],
            analysis: MalcolmGladwellAgentContentAnalysis) ->List[str]:
        """Generate behavioral takeaways from Malcolm Gladwell content"""
        takeaways = []

        # Behavioral psychology takeaways
        if analysis.behavioral_psychology:
            takeaways.append(
                "Small changes in context can produce big changes in behavior")
            takeaways.append(
                "First impressions are often misleading and require deeper analysis")

        # Social science takeaways
        if analysis.social_science:
            takeaways.append(
                "Social epidemics spread through three key factors: contagiousness, little causes, and environment")
            takeaways.append(
                "Cultural legacies shape behavior in ways we often don't recognize")

        # Tipping points takeaways
        if analysis.tipping_points:
            takeaways.append(
                "Tipping points occur when small changes reach a critical threshold")
            takeaways.append(
                "Connectors, mavens, and salesmen drive social epidemics")

        # Outlier analysis takeaways
        if analysis.outlier_analysis:
            takeaways.append(
                "Success requires a combination of opportunity, timing, and preparation")
            takeaways.append(
                "Practice is necessary but not sufficient for exceptional achievement")

        return takeaways

    def get_strategic_insights(self) -> Dict[str, Any]:
        """Get aggregated strategic insights from Malcolm Gladwell monitoring"""
        return {
            'agent': 'Malcolm Gladwell',
            'total_analyses': len(self.analysis_history),
            'behavioral_psychology': sum(len(a['analysis'].behavioral_psychology) for a in self.analysis_history),
            'social_science': sum(len(a['analysis'].social_science) for a in self.analysis_history),
            'tipping_points': sum(len(a['analysis'].tipping_points) for a in self.analysis_history),
            'outlier_analysis': sum(len(a['analysis'].outlier_analysis) for a in self.analysis_history),
            'key_themes': self._extract_key_themes(),
            'last_updated': datetime.now().isoformat()
        }

    def _extract_key_themes(self) -> List[str]:
        """Extract key themes from analysis history"""
        themes = []
        if any(len(a['analysis'].behavioral_psychology) >0
               for a in self.analysis_history):
            themes.append("Behavioral psychology and decision making")
        if any(len(a['analysis'].social_science) >0
               for a in self.analysis_history):
            themes.append("Social science and cultural analysis")
        if any(len(a['analysis'].tipping_points) >0
               for a in self.analysis_history):
            themes.append("Tipping points and social epidemics")
        if any(len(a['analysis'].outlier_analysis) >0
               for a in self.analysis_history):
            themes.append("Success factors and outlier analysis")
        return themes
