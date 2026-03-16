#!/usr/bin/env python3
"""
Daniel Kahneman Council Agent
Autonomous agent for monitoring Daniel Kahneman's public communications
Specialized in behavioral economics, cognitive psychology, and decision-making content analysis
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
class DanielKahnemanAgentContentAnalysis:
    """Specialized analysis for Daniel Kahneman content"""
    video_id: str
    title: str
    behavioral_economics: List[str] = None
    cognitive_biases: List[str] = None
    decision_making: List[str] = None
    system1_system2: List[str] = None
    key_takeaways: List[str] = None

    def __post_init__(self):

        if self.behavioral_economics is None:
            self.behavioral_economics = []
        if self.cognitive_biases is None:
            self.cognitive_biases = []
        if self.decision_making is None:
            self.decision_making = []
        if self.system1_system2 is None:
            self.system1_system2 = []
        if self.key_takeaways is None:
            self.key_takeaways = []

class DanielKahnemanAgent(BaseCouncilAgent):
    """Autonomous agent for Daniel Kahneman public communications monitoring"""

    def __init__(self):
        super().__init__(
            name="Daniel Kahneman",
            channel_id="UC8Z-EwvkADzZHqXYbfAXNw",  # Daniel Kahneman related content
            focus_areas=['Behavioral Economics',
                'Cognitive Psychology', 'Decision Making'],
            priority="high",
            capabilities=[
                AgentCapabilities.CONTENT_ANALYSIS,
                AgentCapabilities.TREND_ANALYSIS,
                AgentCapabilities.STRATEGIC_INSIGHT
            ]
        )

        # Daniel Kahneman specific topic patterns
        self.topic_patterns = {
            'economics': ['behavioral economics', 'economics', 'finance', 'markets'],
            'biases': ['bias', 'cognitive bias', 'thinking fast', 'thinking slow'],
            'decision': ['decision making', 'choice', 'judgment', 'reasoning'],
            'psychology': ['psychology', 'cognitive', 'mental', 'mind']
        }

        # Initialize analysis storage
        self.analysis_history = []

    def analyze_content(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze Daniel Kahneman content for behavioral insights"""

        analysis = DanielKahnemanAgentContentAnalysis(
            video_id=content.get('video_id', ''),
            title=content.get('title', '')
        )

        # Extract behavioral economics insights
        economics_keywords = ["behavioral economics",
            "economics", "finance", "markets", "irrational"]
        if any(
            keyword in content.get('title', '').
            lower() or keyword in content.get('description', '').lower()
            for keyword in economics_keywords):
            analysis.behavioral_economics.append(
                "Behavioral economics insight presented")

        # Extract cognitive biases insights
        bias_keywords = ["bias", "cognitive bias",
            "anchoring", "availability", "framing"]
        if any(
            keyword in content.get('title', '').
            lower() or keyword in content.get('description', '').lower()
            for keyword in bias_keywords):
            analysis.cognitive_biases.append(
                "Cognitive bias analysis discussed")

        # Extract decision making insights
        decision_keywords = ["decision making", "choice",
            "judgment", "reasoning", "prospect theory"]
        if any(
            keyword in content.get('title', '').
            lower() or keyword in content.get('description', '').lower()
            for keyword in decision_keywords):
            analysis.decision_making.append("Decision making theory explored")

        # Extract System 1/System 2 insights
        system_keywords = ["system 1", "system 2",
            "thinking fast", "thinking slow", "automatic"]
        if any(
            keyword in content.get('title', '').
            lower() or keyword in content.get('description', '').lower()
            for keyword in system_keywords):
            analysis.system1_system2.append("Dual-process theory discussed")

        # Generate key takeaways
        analysis.key_takeaways = self._generate_takeaways(content, analysis)

        result = {
            'agent': 'Daniel Kahneman',
            'analysis': analysis,
            'timestamp': datetime.now().isoformat(),
            'content_type': 'video',
            'insights_generated': len(analysis.key_takeaways)
        }

        self.analysis_history.append(result)
        return result

    def _generate_takeaways(
            self, content: Dict[str, Any],
            analysis: DanielKahnemanAgentContentAnalysis) ->List[str]:
        """Generate behavioral takeaways from Daniel Kahneman content"""
        takeaways = []

        # Behavioral economics takeaways
        if analysis.behavioral_economics:
            takeaways.append("People are not always rational economic actors")
            takeaways.append(
                "Loss aversion is more powerful than potential gains")

        # Cognitive biases takeaways
        if analysis.cognitive_biases:
            takeaways.append(
                "Cognitive biases systematically distort our thinking")
            takeaways.append(
                "Anchoring effects influence judgments more than we realize")

        # Decision making takeaways
        if analysis.decision_making:
            takeaways.append(
                "Prospect theory explains how people make decisions under risk")
            takeaways.append(
                "Reference points determine whether we perceive outcomes as gains or losses")

        # System 1/System 2 takeaways
        if analysis.system1_system2:
            takeaways.append(
                "System 1 thinking is fast, automatic, and emotional")
            takeaways.append(
                "System 2 thinking is slow, deliberate, and logical")

        return takeaways

    def get_strategic_insights(self) -> Dict[str, Any]:
        """Get aggregated strategic insights from Daniel Kahneman monitoring"""
        return {
            'agent': 'Daniel Kahneman',
            'total_analyses': len(self.analysis_history),
            'behavioral_economics': sum(len(a['analysis'].behavioral_economics) for a in self.analysis_history),
            'cognitive_biases': sum(len(a['analysis'].cognitive_biases) for a in self.analysis_history),
            'decision_making': sum(len(a['analysis'].decision_making) for a in self.analysis_history),
            'system1_system2': sum(len(a['analysis'].system1_system2) for a in self.analysis_history),
            'key_themes': self._extract_key_themes(),
            'last_updated': datetime.now().isoformat()
        }

    def _extract_key_themes(self) -> List[str]:
        """Extract key themes from analysis history"""
        themes = []
        if any(len(a['analysis'].behavioral_economics) >0
               for a in self.analysis_history):
            themes.append("Behavioral economics and irrationality")
        if any(len(a['analysis'].cognitive_biases) >0
               for a in self.analysis_history):
            themes.append("Cognitive biases and mental shortcuts")
        if any(len(a['analysis'].decision_making) >0
               for a in self.analysis_history):
            themes.append("Decision making under uncertainty")
        if any(len(a['analysis'].system1_system2) >0
               for a in self.analysis_history):
            themes.append("Dual-process theory of thinking")
        return themes
