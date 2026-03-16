#!/usr/bin/env python3
"""
Neil deGrasse Tyson Council Agent
Autonomous agent for monitoring Neil deGrasse Tyson's public communications
Specialized in astrophysics, cosmology, and science communication content analysis
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
class NeilDeGrasseTysonAgentContentAnalysis:
    """Specialized analysis for Neil deGrasse Tyson content"""
    video_id: str
    title: str
    astrophysics: List[str] = None
    cosmology: List[str] = None
    science_communication: List[str] = None
    space_exploration: List[str] = None
    key_takeaways: List[str] = None

    def __post_init__(self):

        if self.astrophysics is None:
            self.astrophysics = []
        if self.cosmology is None:
            self.cosmology = []
        if self.science_communication is None:
            self.science_communication = []
        if self.space_exploration is None:
            self.space_exploration = []
        if self.key_takeaways is None:
            self.key_takeaways = []

class NeilDeGrasseTysonAgent(BaseCouncilAgent):
    """Autonomous agent for Neil deGrasse Tyson public communications monitoring"""

    def __init__(self):
        super().__init__(
            name="Neil deGrasse Tyson",
            channel_id="UC8Z-EwvkADzZHqXYbfAXNw",  # Neil deGrasse Tyson related content
            focus_areas=['Astrophysics', 'Cosmology',
                'Science Communication', 'Space Exploration'],
            priority="high",
            capabilities=[
                AgentCapabilities.CONTENT_ANALYSIS,
                AgentCapabilities.TREND_ANALYSIS,
                AgentCapabilities.STRATEGIC_INSIGHT
            ]
        )

        # Neil deGrasse Tyson specific topic patterns
        self.topic_patterns = {
            'astrophysics': ['astrophysics', 'stars', 'galaxies', 'black holes', 'neutron stars'],
            'cosmology': ['cosmology', 'universe', 'big bang', 'dark matter', 'dark energy'],
            'science_comm': ['science communication', 'education', 'public understanding', 'wonder'],
            'space': ['space exploration', 'nasa', 'mars', 'moon', 'space travel']
        }

        # Initialize analysis storage
        self.analysis_history = []

    def analyze_content(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze Neil deGrasse Tyson content for astrophysical and cosmological insights"""

        analysis = NeilDeGrasseTysonAgentContentAnalysis(
            video_id=content.get('video_id', ''),
            title=content.get('title', '')
        )

        # Extract astrophysics insights
        astrophysics_keywords = [
            "astrophysics", "stars", "galaxies", "black holes",
             "neutron stars", "supernova"]
        if any(
            keyword in content.get('title', '').
            lower() or keyword in content.get('description', '').lower()
            for keyword in astrophysics_keywords):
            analysis.astrophysics.append("Astrophysical phenomenon discussed")

        # Extract cosmology insights
        cosmology_keywords = ["cosmology", "universe",
            "big bang", "dark matter", "dark energy", "expansion"]
        if any(
            keyword in content.get('title', '').
            lower() or keyword in content.get('description', '').lower()
            for keyword in cosmology_keywords):
            analysis.cosmology.append("Cosmological concept explored")

        # Extract science communication insights
        comm_keywords = ["science communication", "education",
            "public understanding", "wonder", "curiosity"]
        if any(
            keyword in content.get('title', '').
            lower() or keyword in content.get('description', '').lower()
            for keyword in comm_keywords):
            analysis.science_communication.append(
                "Science communication strategy presented")

        # Extract space exploration insights
        space_keywords = ["space exploration", "nasa",
            "mars", "moon", "space travel", "colonization"]
        if any(
            keyword in content.get('title', '').
            lower() or keyword in content.get('description', '').lower()
            for keyword in space_keywords):
            analysis.space_exploration.append(
                "Space exploration topic covered")

        # Generate key takeaways
        analysis.key_takeaways = self._generate_takeaways(content, analysis)

        result = {
            'agent': 'Neil deGrasse Tyson',
            'analysis': analysis,
            'timestamp': datetime.now().isoformat(),
            'content_type': 'video',
            'insights_generated': len(analysis.key_takeaways)
        }

        self.analysis_history.append(result)
        return result

    def _generate_takeaways(
            self, content: Dict[str, Any],
            analysis: NeilDeGrasseTysonAgentContentAnalysis) ->List[str]:
        """Generate astrophysical takeaways from Neil deGrasse Tyson content"""
        takeaways = []

        # Astrophysics takeaways
        if analysis.astrophysics:
            takeaways.append(
                "The universe is governed by physical laws we can understand")
            takeaways.append(
                "Stars are the fundamental building blocks of galaxies")

        # Cosmology takeaways
        if analysis.cosmology:
            takeaways.append("The Big Bang is the origin of our universe")
            takeaways.append(
                "Dark matter and dark energy shape cosmic evolution")

        # Science communication takeaways
        if analysis.science_communication:
            takeaways.append(
                "Science communication should inspire wonder and curiosity")
            takeaways.append(
                "Public understanding of science is essential for progress")

        # Space exploration takeaways
        if analysis.space_exploration:
            takeaways.append(
                "Space exploration expands human knowledge and potential")
            takeaways.append("We are all made of star stuff")

        return takeaways

    def get_strategic_insights(self) -> Dict[str, Any]:
        """Get aggregated strategic insights from Neil deGrasse Tyson monitoring"""
        return {
            'agent': 'Neil deGrasse Tyson',
            'total_analyses': len(self.analysis_history),
            'astrophysics': sum(len(a['analysis'].astrophysics) for a in self.analysis_history),
            'cosmology': sum(len(a['analysis'].cosmology) for a in self.analysis_history),
            'science_communication': sum(len(a['analysis'].science_communication) for a in self.analysis_history),
            'space_exploration': sum(len(a['analysis'].space_exploration) for a in self.analysis_history),
            'key_themes': self._extract_key_themes(),
            'last_updated': datetime.now().isoformat()
        }

    def _extract_key_themes(self) -> List[str]:
        """Extract key themes from analysis history"""
        themes = []
        if any(len(a['analysis'].astrophysics) >0 for a in
                self.analysis_history):
            themes.append("Astrophysical phenomena and stellar evolution")
        if any(len(a['analysis'].cosmology) > 0 for a in self.analysis_history):
            themes.append("Cosmological origins and universal structure")
        if any(len(a['analysis'].science_communication) >0
               for a in self.analysis_history):
            themes.append("Science communication and public education")
        if any(len(a['analysis'].space_exploration) >0
               for a in self.analysis_history):
            themes.append("Space exploration and human destiny")
        return themes
