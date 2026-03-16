#!/usr/bin/env python3
"""
Jane Goodall Council Agent
Autonomous agent for monitoring Jane Goodall's public communications
Specialized in primatology, animal behavior, and conservation content analysis
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
class JaneGoodallAgentContentAnalysis:
    """Specialized analysis for Jane Goodall content"""
    video_id: str
    title: str
    primatology: List[str] = None
    animal_behavior: List[str] = None
    conservation: List[str] = None
    chimpanzee_research: List[str] = None
    key_takeaways: List[str] = None

    def __post_init__(self):

        if self.primatology is None:
            self.primatology = []
        if self.animal_behavior is None:
            self.animal_behavior = []
        if self.conservation is None:
            self.conservation = []
        if self.chimpanzee_research is None:
            self.chimpanzee_research = []
        if self.key_takeaways is None:
            self.key_takeaways = []

class JaneGoodallAgent(BaseCouncilAgent):
    """Autonomous agent for Jane Goodall public communications monitoring"""

    def __init__(self):
        super().__init__(
            name="Jane Goodall",
            channel_id="UC8Z-EwvkADzZHqXYbfAXNw",  # Jane Goodall related content
            focus_areas=['Primatology', 'Animal Behavior',
                'Conservation', 'Chimpanzee Research'],
            priority="high",
            capabilities=[
                AgentCapabilities.CONTENT_ANALYSIS,
                AgentCapabilities.TREND_ANALYSIS,
                AgentCapabilities.STRATEGIC_INSIGHT
            ]
        )

        # Jane Goodall specific topic patterns
        self.topic_patterns = {
            'primatology': ['primatology', 'primates', 'apes', 'chimpanzees', 'gorillas'],
            'behavior': ['animal behavior', 'social behavior', 'intelligence', 'emotions', 'culture'],
            'conservation': ['conservation', 'wildlife', 'habitat', 'protection', 'endangered'],
            'research': ['research', 'gombe', 'field study', 'observation', 'chimpanzee']
        }

        # Initialize analysis storage
        self.analysis_history = []

    def analyze_content(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze Jane Goodall content for primatology and conservation insights"""

        analysis = JaneGoodallAgentContentAnalysis(
            video_id=content.get('video_id', ''),
            title=content.get('title', '')
        )

        # Extract primatology insights
        primatology_keywords = ["primatology", "primates",
            "apes", "chimpanzees", "gorillas", "monkeys"]
        if any(
            keyword in content.get('title', '').
            lower() or keyword in content.get('description', '').lower()
            for keyword in primatology_keywords):
            analysis.primatology.append("Primatology research discussed")

        # Extract animal behavior insights
        behavior_keywords = ["animal behavior", "social behavior",
            "intelligence", "emotions", "culture", "learning"]
        if any(
            keyword in content.get('title', '').
            lower() or keyword in content.get('description', '').lower()
            for keyword in behavior_keywords):
            analysis.animal_behavior.append("Animal behavior pattern explored")

        # Extract conservation insights
        conservation_keywords = ["conservation", "wildlife",
            "habitat", "protection", "endangered", "threatened"]
        if any(
            keyword in content.get('title', '').
            lower() or keyword in content.get('description', '').lower()
            for keyword in conservation_keywords):
            analysis.conservation.append("Conservation strategy presented")

        # Extract chimpanzee research insights
        chimp_keywords = ["chimpanzee", "gombe",
            "field study", "observation", "research", "study"]
        if any(
            keyword in content.get('title', '').
            lower() or keyword in content.get('description', '').lower()
            for keyword in chimp_keywords):
            analysis.chimpanzee_research.append(
                "Chimpanzee research findings shared")

        # Generate key takeaways
        analysis.key_takeaways = self._generate_takeaways(content, analysis)

        result = {
            'agent': 'Jane Goodall',
            'analysis': analysis,
            'timestamp': datetime.now().isoformat(),
            'content_type': 'video',
            'insights_generated': len(analysis.key_takeaways)
        }

        self.analysis_history.append(result)
        return result

    def _generate_takeaways(
            self, content: Dict[str, Any],
            analysis: JaneGoodallAgentContentAnalysis) ->List[str]:
        """Generate primatology takeaways from Jane Goodall content"""
        takeaways = []

        # Primatology takeaways
        if analysis.primatology:
            takeaways.append(
                "Primates share complex social structures and emotional intelligence")
            takeaways.append(
                "Chimpanzees demonstrate remarkable cognitive abilities")

        # Animal behavior takeaways
        if analysis.animal_behavior:
            takeaways.append(
                "Animals exhibit complex emotions and social relationships")
            takeaways.append(
                "Culture and learning are widespread in animal societies")

        # Conservation takeaways
        if analysis.conservation:
            takeaways.append(
                "Conservation requires understanding and protecting habitats")
            takeaways.append(
                "Every individual can contribute to wildlife protection")

        # Chimpanzee research takeaways
        if analysis.chimpanzee_research:
            takeaways.append(
                "Long-term field research reveals the complexity of primate societies")
            takeaways.append(
                "Chimpanzees show both cooperation and conflict in social groups")

        return takeaways

    def get_strategic_insights(self) -> Dict[str, Any]:
        """Get aggregated strategic insights from Jane Goodall monitoring"""
        return {
            'agent': 'Jane Goodall',
            'total_analyses': len(self.analysis_history),
            'primatology': sum(len(a['analysis'].primatology) for a in self.analysis_history),
            'animal_behavior': sum(len(a['analysis'].animal_behavior) for a in self.analysis_history),
            'conservation': sum(len(a['analysis'].conservation) for a in self.analysis_history),
            'chimpanzee_research': sum(len(a['analysis'].chimpanzee_research) for a in self.analysis_history),
            'key_themes': self._extract_key_themes(),
            'last_updated': datetime.now().isoformat()
        }

    def _extract_key_themes(self) -> List[str]:
        """Extract key themes from analysis history"""
        themes = []
        if any(len(a['analysis'].primatology) >0 for a in
                self.analysis_history):
            themes.append("Primatology and primate behavior")
        if any(len(a['analysis'].animal_behavior) >0
               for a in self.analysis_history):
            themes.append("Animal behavior and intelligence")
        if any(len(a['analysis'].conservation) >0 for a in
                self.analysis_history):
            themes.append("Conservation and wildlife protection")
        if any(len(a['analysis'].chimpanzee_research) >0
               for a in self.analysis_history):
            themes.append("Chimpanzee research and Gombe studies")
        return themes
