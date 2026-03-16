#!/usr/bin/env python3
"""
Steven Pinker Council Agent
Autonomous agent for monitoring Steven Pinker's public communications
Specialized in cognitive psychology, linguistics, and human progress content analysis
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
class StevenPinkerAgentContentAnalysis:
    """Specialized analysis for Steven Pinker content"""
    video_id: str
    title: str
    cognitive_science: List[str] = None
    language_psychology: List[str] = None
    human_progress: List[str] = None
    rationality_debate: List[str] = None
    key_takeaways: List[str] = None

    def __post_init__(self):

        if self.cognitive_science is None:
            self.cognitive_science = []
        if self.language_psychology is None:
            self.language_psychology = []
        if self.human_progress is None:
            self.human_progress = []
        if self.rationality_debate is None:
            self.rationality_debate = []
        if self.key_takeaways is None:
            self.key_takeaways = []

class StevenPinkerAgent(BaseCouncilAgent):
    """Autonomous agent for Steven Pinker public communications monitoring"""

    def __init__(self):
        super().__init__(
            name="Steven Pinker",
            channel_id="UC8Z-EwvkADzZHqXYbfAXNw",  # Steven Pinker related content
            focus_areas=['Cognitive Science',
                'Linguistics', 'Psychology', 'Progress'],
            priority="high",
            capabilities=[
                AgentCapabilities.CONTENT_ANALYSIS,
                AgentCapabilities.TREND_ANALYSIS,
                AgentCapabilities.STRATEGIC_INSIGHT
            ]
        )

        # Steven Pinker specific topic patterns
        self.topic_patterns = {
            'cognitive': ['cognitive', 'psychology', 'mind', 'brain', 'thinking'],
            'language': ['language', 'linguistics', 'grammar', 'syntax', 'communication'],
            'progress': ['progress', 'enlightenment', 'improvement', 'advancement'],
            'rationality': ['rationality', 'reason', 'logic', 'science', 'evidence']
        }

        # Initialize analysis storage
        self.analysis_history = []

    def analyze_content(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze Steven Pinker content for cognitive and progress insights"""

        analysis = StevenPinkerAgentContentAnalysis(
            video_id=content.get('video_id', ''),
            title=content.get('title', '')
        )

        # Extract cognitive science insights
        cognitive_keywords = ["cognitive", "psychology",
            "mind", "brain", "thinking", "cognition"]
        if any(
            keyword in content.get('title', '').
            lower() or keyword in content.get('description', '').lower()
            for keyword in cognitive_keywords):
            analysis.cognitive_science.append(
                "Cognitive science insight presented")

        # Extract language psychology insights
        language_keywords = ["language", "linguistics",
            "grammar", "syntax", "communication", "words"]
        if any(
            keyword in content.get('title', '').
            lower() or keyword in content.get('description', '').lower()
            for keyword in language_keywords):
            analysis.language_psychology.append(
                "Language psychology discussed")

        # Extract human progress insights
        progress_keywords = ["progress", "enlightenment",
            "improvement", "advancement", "civilization"]
        if any(
            keyword in content.get('title', '').
            lower() or keyword in content.get('description', '').lower()
            for keyword in progress_keywords):
            analysis.human_progress.append("Human progress analysis presented")

        # Extract rationality debate insights
        rationality_keywords = ["rationality", "reason",
            "logic", "science", "evidence", "truth"]
        if any(
            keyword in content.get('title', '').
            lower() or keyword in content.get('description', '').lower()
            for keyword in rationality_keywords):
            analysis.rationality_debate.append("Rationality debate explored")

        # Generate key takeaways
        analysis.key_takeaways = self._generate_takeaways(content, analysis)

        result = {
            'agent': 'Steven Pinker',
            'analysis': analysis,
            'timestamp': datetime.now().isoformat(),
            'content_type': 'video',
            'insights_generated': len(analysis.key_takeaways)
        }

        self.analysis_history.append(result)
        return result

    def _generate_takeaways(
            self, content: Dict[str, Any],
            analysis: StevenPinkerAgentContentAnalysis) ->List[str]:
        """Generate cognitive takeaways from Steven Pinker content"""
        takeaways = []

        # Cognitive science takeaways
        if analysis.cognitive_science:
            takeaways.append(
                "The mind is a complex system of cognitive modules")
            takeaways.append(
                "Evolution shapes both our bodies and our mental faculties")

        # Language psychology takeaways
        if analysis.language_psychology:
            takeaways.append(
                "Language is an instinct, not just a learned skill")
            takeaways.append("Grammar is universal across human languages")

        # Human progress takeaways
        if analysis.human_progress:
            takeaways.append(
                "Humanity has made remarkable progress in reducing violence and poverty")
            takeaways.append(
                "The Enlightenment values of reason and science drive progress")

        # Rationality debate takeaways
        if analysis.rationality_debate:
            takeaways.append(
                "Humans are capable of reason despite cognitive biases")
            takeaways.append(
                "Science and evidence provide the best path to truth")

        return takeaways

    def get_strategic_insights(self) -> Dict[str, Any]:
        """Get aggregated strategic insights from Steven Pinker monitoring"""
        return {
            'agent': 'Steven Pinker',
            'total_analyses': len(self.analysis_history),
            'cognitive_science': sum(len(a['analysis'].cognitive_science) for a in self.analysis_history),
            'language_psychology': sum(len(a['analysis'].language_psychology) for a in self.analysis_history),
            'human_progress': sum(len(a['analysis'].human_progress) for a in self.analysis_history),
            'rationality_debate': sum(len(a['analysis'].rationality_debate) for a in self.analysis_history),
            'key_themes': self._extract_key_themes(),
            'last_updated': datetime.now().isoformat()
        }

    def _extract_key_themes(self) -> List[str]:
        """Extract key themes from analysis history"""
        themes = []
        if any(len(a['analysis'].cognitive_science) >0
               for a in self.analysis_history):
            themes.append("Cognitive science and mental architecture")
        if any(len(a['analysis'].language_psychology) >0
               for a in self.analysis_history):
            themes.append("Language psychology and linguistics")
        if any(len(a['analysis'].human_progress) >0
               for a in self.analysis_history):
            themes.append("Human progress and enlightenment")
        if any(len(a['analysis'].rationality_debate) >0
               for a in self.analysis_history):
            themes.append("Rationality and scientific thinking")
        return themes
