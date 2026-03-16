#!/usr/bin/env python3
"""
Yuval Noah Harari Council Agent
Autonomous agent for monitoring Yuval Noah Harari's public communications
Specialized in history, philosophy, technology, and human society content analysis
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
class YuvalNoahHarariAgentContentAnalysis:
    """Specialized analysis for Yuval Noah Harari content"""
    video_id: str
    title: str
    human_history: List[str] = None
    technology_society: List[str] = None
    philosophical_insights: List[str] = None
    future_humanity: List[str] = None
    key_takeaways: List[str] = None

    def __post_init__(self):

        if self.human_history is None:
            self.human_history = []
        if self.technology_society is None:
            self.technology_society = []
        if self.philosophical_insights is None:
            self.philosophical_insights = []
        if self.future_humanity is None:
            self.future_humanity = []
        if self.key_takeaways is None:
            self.key_takeaways = []

class YuvalNoahHarariAgent(BaseCouncilAgent):
    """Autonomous agent for Yuval Noah Harari public communications monitoring"""

    def __init__(self):
        super().__init__(
            name="Yuval Noah Harari",
            channel_id="UC8Z-EwvkADzZHqXYbfAXNw",  # Yuval Noah Harari related content
            focus_areas=['History', 'Philosophy',
                'Technology', 'Human Society'],
            priority="high",
            capabilities=[
                AgentCapabilities.CONTENT_ANALYSIS,
                AgentCapabilities.TREND_ANALYSIS,
                AgentCapabilities.STRATEGIC_INSIGHT
            ]
        )

        # Yuval Noah Harari specific topic patterns
        self.topic_patterns = {
            'history': ['history', 'historical', 'civilization', 'human development'],
            'philosophy': ['philosophy', 'consciousness', 'meaning', 'purpose', 'ethics'],
            'technology': ['technology', 'ai', 'biotechnology', 'data', 'algorithms'],
            'society': ['society', 'social', 'politics', 'economics', 'future']
        }

        # Initialize analysis storage
        self.analysis_history = []

    def analyze_content(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze Yuval Noah Harari content for philosophical insights"""

        analysis = YuvalNoahHarariAgentContentAnalysis(
            video_id=content.get('video_id', ''),
            title=content.get('title', '')
        )

        # Extract human history insights
        history_keywords = ["history", "civilization",
            "human", "development", "evolution"]
        if any(
            keyword in content.get('title', '').
            lower() or keyword in content.get('description', '').lower()
            for keyword in history_keywords):
            analysis.human_history.append("Human history analysis presented")

        # Extract technology society insights
        tech_keywords = ["technology", "ai", "data",
            "algorithms", "biotechnology", "surveillance"]
        if any(
            keyword in content.get('title', '').
            lower() or keyword in content.get('description', '').lower()
            for keyword in tech_keywords):
            analysis.technology_society.append(
                "Technology-society relationship discussed")

        # Extract philosophical insights
        philosophy_keywords = ["consciousness", "meaning",
            "purpose", "ethics", "philosophy", "story"]
        if any(
            keyword in content.get('title', '').
            lower() or keyword in content.get('description', '').lower()
            for keyword in philosophy_keywords):
            analysis.philosophical_insights.append(
                "Philosophical insight explored")

        # Extract future humanity insights
        future_keywords = ["future", "humanity",
            "post-human", "intelligence", "consciousness"]
        if any(
            keyword in content.get('title', '').
            lower() or keyword in content.get('description', '').lower()
            for keyword in future_keywords):
            analysis.future_humanity.append("Future of humanity discussed")

        # Generate key takeaways
        analysis.key_takeaways = self._generate_takeaways(content, analysis)

        result = {
            'agent': 'Yuval Noah Harari',
            'analysis': analysis,
            'timestamp': datetime.now().isoformat(),
            'content_type': 'video',
            'insights_generated': len(analysis.key_takeaways)
        }

        self.analysis_history.append(result)
        return result

    def _generate_takeaways(
            self, content: Dict[str, Any],
            analysis: YuvalNoahHarariAgentContentAnalysis) ->List[str]:
        """Generate philosophical takeaways from Yuval Noah Harari content"""
        takeaways = []

        # Human history takeaways
        if analysis.human_history:
            takeaways.append(
                "Human history is driven by shared stories and collective imagination")
            takeaways.append(
                "Agricultural revolution fundamentally changed human society and biology")

        # Technology society takeaways
        if analysis.technology_society:
            takeaways.append(
                "Data is the most valuable resource in the 21st century")
            takeaways.append(
                "AI and biotechnology challenge traditional concepts of humanity")

        # Philosophical insights takeaways
        if analysis.philosophical_insights:
            takeaways.append(
                "Consciousness and intelligence are not the same thing")
            takeaways.append(
                "Humans are meaning-making animals in a universe without inherent meaning")

        # Future humanity takeaways
        if analysis.future_humanity:
            takeaways.append(
                "The future will be determined by our technological choices")
            takeaways.append(
                "We need new stories to navigate the post-human era")

        return takeaways

    def get_strategic_insights(self) -> Dict[str, Any]:
        """Get aggregated strategic insights from Yuval Noah Harari monitoring"""
        return {
            'agent': 'Yuval Noah Harari',
            'total_analyses': len(self.analysis_history),
            'human_history': sum(len(a['analysis'].human_history) for a in self.analysis_history),
            'technology_society': sum(len(a['analysis'].technology_society) for a in self.analysis_history),
            'philosophical_insights': sum(len(a['analysis'].philosophical_insights) for a in self.analysis_history),
            'future_humanity': sum(len(a['analysis'].future_humanity) for a in self.analysis_history),
            'key_themes': self._extract_key_themes(),
            'last_updated': datetime.now().isoformat()
        }

    def _extract_key_themes(self) -> List[str]:
        """Extract key themes from analysis history"""
        themes = []
        if any(len(a['analysis'].human_history) >0
               for a in self.analysis_history):
            themes.append("Human history and civilization development")
        if any(len(a['analysis'].technology_society) >0
               for a in self.analysis_history):
            themes.append("Technology's impact on society")
        if any(len(a['analysis'].philosophical_insights) >0
               for a in self.analysis_history):
            themes.append("Philosophy of consciousness and meaning")
        if any(len(a['analysis'].future_humanity) >0
               for a in self.analysis_history):
            themes.append("Future of humanity and post-human era")
        return themes
