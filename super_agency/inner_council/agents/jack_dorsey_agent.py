#!/usr/bin/env python3
"""
Jack Dorsey Council Agent
Autonomous agent for monitoring Jack Dorsey's public communications
Specialized in social media, decentralization, bitcoin, and free speech content analysis
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
class JackDorseyAgentContentAnalysis:
    """Specialized analysis for Jack Dorsey content"""
    video_id: str
    title: str
    decentralization: List[str] = None
    bitcoin_vision: List[str] = None
    free_speech: List[str] = None
    social_platforms: List[str] = None
    key_takeaways: List[str] = None

    def __post_init__(self):

        if self.decentralization is None:
            self.decentralization = []
        if self.bitcoin_vision is None:
            self.bitcoin_vision = []
        if self.free_speech is None:
            self.free_speech = []
        if self.social_platforms is None:
            self.social_platforms = []
        if self.key_takeaways is None:
            self.key_takeaways = []

class JackDorseyAgent(BaseCouncilAgent):
    """Autonomous agent for Jack Dorsey public communications monitoring"""

    def __init__(self):
        super().__init__(
            name="Jack Dorsey",
            channel_id="UC8Z-EwvkADzZHqXYbfAXNw",  # Twitter/Block related content
            focus_areas=['Decentralization', 'Bitcoin',
                'Free Speech', 'Social Platforms'],
            priority="high",
            capabilities=[
                AgentCapabilities.CONTENT_ANALYSIS,
                AgentCapabilities.TREND_ANALYSIS,
                AgentCapabilities.STRATEGIC_INSIGHT
            ]
        )

        # Jack Dorsey specific topic patterns
        self.topic_patterns = {
            'decentralization': ['decentralization', 'decentralized', 'distributed', 'web3', 'blockchain'],
            'bitcoin': ['bitcoin', 'btc', 'cryptocurrency', 'digital currency', 'mining'],
            'free_speech': ['free speech', 'censorship', 'moderation', 'expression', 'speech'],
            'social': ['social', 'platform', 'twitter', 'algorithm', 'content']
        }

        # Initialize analysis storage
        self.analysis_history = []

    def analyze_content(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze Jack Dorsey content for decentralization and freedom insights"""

        analysis = JackDorseyAgentContentAnalysis(
            video_id=content.get('video_id', ''),
            title=content.get('title', '')
        )

        # Extract decentralization insights
        decentralization_keywords = [
            "decentralization", "decentralized", "distributed", "web3",
            "blockchain"]
        if any(keyword in content.get('title', '').
               lower() or keyword in content.get('description', '').lower()
               for keyword in decentralization_keywords):
            analysis.decentralization.append(
                "Decentralization principle discussed")

        # Extract bitcoin vision insights
        bitcoin_keywords = ["bitcoin", "btc", "cryptocurrency",
            "digital currency", "mining", "satoshi"]
        if any(
            keyword in content.get('title', '').
            lower() or keyword in content.get('description', '').lower()
            for keyword in bitcoin_keywords):
            analysis.bitcoin_vision.append("Bitcoin vision presented")

        # Extract free speech insights
        speech_keywords = ["free speech", "censorship",
            "moderation", "expression", "speech", "freedom"]
        if any(
            keyword in content.get('title', '').
            lower() or keyword in content.get('description', '').lower()
            for keyword in speech_keywords):
            analysis.free_speech.append("Free speech topic identified")

        # Extract social platforms insights
        social_keywords = ["social", "platform", "twitter",
            "algorithm", "content", "moderation"]
        if any(
            keyword in content.get('title', '').
            lower() or keyword in content.get('description', '').lower()
            for keyword in social_keywords):
            analysis.social_platforms.append(
                "Social platform dynamics discussed")

        # Generate key takeaways
        analysis.key_takeaways = self._generate_takeaways(content, analysis)

        result = {
            'agent': 'Jack Dorsey',
            'analysis': analysis,
            'timestamp': datetime.now().isoformat(),
            'content_type': 'video',
            'insights_generated': len(analysis.key_takeaways)
        }

        self.analysis_history.append(result)
        return result

    def _generate_takeaways(
            self, content: Dict[str, Any],
            analysis: JackDorseyAgentContentAnalysis) ->List[str]:
        """Generate decentralization takeaways from Jack Dorsey content"""
        takeaways = []

        # Decentralization takeaways
        if analysis.decentralization:
            takeaways.append(
                "Decentralization returns control and freedom to individuals")
            takeaways.append(
                "Web3 represents the next evolution of the internet")

        # Bitcoin vision takeaways
        if analysis.bitcoin_vision:
            takeaways.append(
                "Bitcoin is digital gold and a hedge against inflation")
            takeaways.append(
                "Cryptocurrency enables financial freedom globally")

        # Free speech takeaways
        if analysis.free_speech:
            takeaways.append(
                "Free speech is essential for democratic discourse")
            takeaways.append(
                "Content moderation should be transparent and accountable")

        # Social platforms takeaways
        if analysis.social_platforms:
            takeaways.append(
                "Algorithms should serve users, not manipulate them")
            takeaways.append(
                "Social platforms have responsibility for public discourse")

        return takeaways

    def get_strategic_insights(self) -> Dict[str, Any]:
        """Get aggregated strategic insights from Jack Dorsey monitoring"""
        return {
            'agent': 'Jack Dorsey',
            'total_analyses': len(self.analysis_history),
            'decentralization': sum(len(a['analysis'].decentralization) for a in self.analysis_history),
            'bitcoin_vision': sum(len(a['analysis'].bitcoin_vision) for a in self.analysis_history),
            'free_speech': sum(len(a['analysis'].free_speech) for a in self.analysis_history),
            'social_platforms': sum(len(a['analysis'].social_platforms) for a in self.analysis_history),
            'key_themes': self._extract_key_themes(),
            'last_updated': datetime.now().isoformat()
        }

    def _extract_key_themes(self) -> List[str]:
        """Extract key themes from analysis history"""
        themes = []
        if any(len(a['analysis'].decentralization) >0
               for a in self.analysis_history):
            themes.append("Decentralization and individual sovereignty")
        if any(len(a['analysis'].bitcoin_vision) >0
               for a in self.analysis_history):
            themes.append("Bitcoin as digital gold")
        if any(len(a['analysis'].free_speech) >0 for a in
                self.analysis_history):
            themes.append("Free speech and content moderation")
        if any(len(a['analysis'].social_platforms) >0
               for a in self.analysis_history):
            themes.append("Social platform governance")
        return themes
