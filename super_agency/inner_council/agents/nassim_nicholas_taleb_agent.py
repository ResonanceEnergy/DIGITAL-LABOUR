#!/usr/bin/env python3
"""
Nassim Nicholas Taleb Council Agent
Autonomous agent for monitoring Nassim Nicholas Taleb's public communications
Specialized in risk management, probability, and philosophical insights content analysis
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
class NassimNicholasTalebAgentContentAnalysis:
    """Specialized analysis for Nassim Nicholas Taleb content"""
    video_id: str
    title: str
    black_swan_events: List[str] = None
    antifragility: List[str] = None
    risk_management: List[str] = None
    philosophical_insights: List[str] = None
    key_takeaways: List[str] = None

    def __post_init__(self):

        if self.black_swan_events is None:
            self.black_swan_events = []
        if self.antifragility is None:
            self.antifragility = []
        if self.risk_management is None:
            self.risk_management = []
        if self.philosophical_insights is None:
            self.philosophical_insights = []
        if self.key_takeaways is None:
            self.key_takeaways = []

class NassimNicholasTalebAgent(BaseCouncilAgent):
    """Autonomous agent for Nassim Nicholas Taleb public communications monitoring"""

    def __init__(self):
        super().__init__(
            name="Nassim Nicholas Taleb",
            channel_id="UC8Z-EwvkADzZHqXYbfAXNw",  # Nassim Nicholas Taleb related content
            focus_areas=['Risk', 'Probability', 'Philosophy', 'Uncertainty'],
            priority="high",
            capabilities=[
                AgentCapabilities.CONTENT_ANALYSIS,
                AgentCapabilities.TREND_ANALYSIS,
                AgentCapabilities.STRATEGIC_INSIGHT
            ]
        )

        # Nassim Nicholas Taleb specific topic patterns
        self.topic_patterns = {
            'black_swan': ['black swan', 'rare event', 'unexpected', 'surprise'],
            'antifragility': ['antifragile', 'fragility', 'robustness', 'resilience'],
            'risk': ['risk', 'probability', 'uncertainty', 'volatility'],
            'philosophy': ['philosophy', 'skin in the game', 'asymmetry', 'convexity']
        }

        # Initialize analysis storage
        self.analysis_history = []

    def analyze_content(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze Nassim Nicholas Taleb content for risk insights"""

        analysis = NassimNicholasTalebAgentContentAnalysis(
            video_id=content.get('video_id', ''),
            title=content.get('title', '')
        )

        # Extract black swan events insights
        black_swan_keywords = ["black swan", "rare event",
            "unexpected", "surprise", "outlier"]
        if any(
            keyword in content.get('title', '').
            lower() or keyword in content.get('description', '').lower()
            for keyword in black_swan_keywords):
            analysis.black_swan_events.append(
                "Black swan event analysis presented")

        # Extract antifragility insights
        antifragility_keywords = [
            "antifragile", "fragility", "robustness", "resilience", "stress"]
        if any(keyword in content.get('title', '').
               lower() or keyword in content.get('description', '').lower()
               for keyword in antifragility_keywords):
            analysis.antifragility.append("Antifragility concept discussed")

        # Extract risk management insights
        risk_keywords = ["risk", "probability",
            "uncertainty", "volatility", "tail risk"]
        if any(
            keyword in content.get('title', '').
            lower() or keyword in content.get('description', '').lower()
            for keyword in risk_keywords):
            analysis.risk_management.append(
                "Risk management strategy explored")

        # Extract philosophical insights
        philosophy_keywords = [
            "skin in the game", "asymmetry", "convexity", "philosophy",
            "epistemology"]
        if any(
            keyword in content.get('title', '').
            lower() or keyword in content.get('description', '').lower()
            for keyword in philosophy_keywords):
            analysis.philosophical_insights.append(
                "Philosophical insight presented")

        # Generate key takeaways
        analysis.key_takeaways = self._generate_takeaways(content, analysis)

        result = {
            'agent': 'Nassim Nicholas Taleb',
            'analysis': analysis,
            'timestamp': datetime.now().isoformat(),
            'content_type': 'video',
            'insights_generated': len(analysis.key_takeaways)
        }

        self.analysis_history.append(result)
        return result

    def _generate_takeaways(
            self, content: Dict[str, Any],
            analysis: NassimNicholasTalebAgentContentAnalysis) ->List[str]:
        """Generate risk and philosophy takeaways from Nassim Nicholas Taleb content"""
        takeaways = []

        # Black swan events takeaways
        if analysis.black_swan_events:
            takeaways.append(
                "Black swan events are unpredictable but have massive impact")
            takeaways.append(
                "Past data is insufficient to predict rare events")

        # Antifragility takeaways
        if analysis.antifragility:
            takeaways.append(
                "Antifragile systems benefit from volatility and stress")
            takeaways.append("Robustness is not the same as antifragility")

        # Risk management takeaways
        if analysis.risk_management:
            takeaways.append("Risk is not volatility; risk is ruin")
            takeaways.append("Tail risk matters more than average performance")

        # Philosophical insights takeaways
        if analysis.philosophical_insights:
            takeaways.append(
                "Skin in the game aligns incentives and reduces moral hazard")
            takeaways.append(
                "Asymmetric payoffs favor optionality over prediction")

        return takeaways

    def get_strategic_insights(self) -> Dict[str, Any]:
        """Get aggregated strategic insights from Nassim Nicholas Taleb monitoring"""
        return {
            'agent': 'Nassim Nicholas Taleb',
            'total_analyses': len(self.analysis_history),
            'black_swan_events': sum(len(a['analysis'].black_swan_events) for a in self.analysis_history),
            'antifragility': sum(len(a['analysis'].antifragility) for a in self.analysis_history),
            'risk_management': sum(len(a['analysis'].risk_management) for a in self.analysis_history),
            'philosophical_insights': sum(len(a['analysis'].philosophical_insights) for a in self.analysis_history),
            'key_themes': self._extract_key_themes(),
            'last_updated': datetime.now().isoformat()
        }

    def _extract_key_themes(self) -> List[str]:
        """Extract key themes from analysis history"""
        themes = []
        if any(len(a['analysis'].black_swan_events) >0
               for a in self.analysis_history):
            themes.append("Black swan events and unpredictability")
        if any(len(a['analysis'].antifragility) >0
               for a in self.analysis_history):
            themes.append("Antifragility and system resilience")
        if any(len(a['analysis'].risk_management) >0
               for a in self.analysis_history):
            themes.append("Risk management and tail events")
        if any(len(a['analysis'].philosophical_insights) >0
               for a in self.analysis_history):
            themes.append("Philosophy of uncertainty and incentives")
        return themes
