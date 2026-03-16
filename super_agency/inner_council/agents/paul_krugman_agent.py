#!/usr/bin/env python3
"""
Paul Krugman Council Agent
Autonomous agent for monitoring Paul Krugman's public communications
Specialized in economics, international trade, and economic policy content analysis
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
class PaulKrugmanAgentContentAnalysis:
    """Specialized analysis for Paul Krugman content"""
    video_id: str
    title: str
    macroeconomics: List[str] = None
    international_trade: List[str] = None
    economic_policy: List[str] = None
    inequality: List[str] = None
    key_takeaways: List[str] = None

    def __post_init__(self):

        if self.macroeconomics is None:
            self.macroeconomics = []
        if self.international_trade is None:
            self.international_trade = []
        if self.economic_policy is None:
            self.economic_policy = []
        if self.inequality is None:
            self.inequality = []
        if self.key_takeaways is None:
            self.key_takeaways = []

class PaulKrugmanAgent(BaseCouncilAgent):
    """Autonomous agent for Paul Krugman public communications monitoring"""

    def __init__(self):
        super().__init__(
            name="Paul Krugman",
            channel_id="UC8Z-EwvkADzZHqXYbfAXNw",  # Paul Krugman related content
            focus_areas=['Macroeconomics', 'International Trade',
                'Economic Policy', 'Inequality'],
            priority="high",
            capabilities=[
                AgentCapabilities.CONTENT_ANALYSIS,
                AgentCapabilities.TREND_ANALYSIS,
                AgentCapabilities.STRATEGIC_INSIGHT
            ]
        )

        # Paul Krugman specific topic patterns
        self.topic_patterns = {
            'macroeconomics': ['macroeconomics', 'gdp', 'inflation', 'unemployment', 'recession'],
            'trade': ['trade', 'globalization', 'tariffs', 'imports', 'exports', 'wto'],
            'policy': ['policy', 'stimulus', 'fiscal', 'monetary', 'regulation', 'government'],
            'inequality': ['inequality', 'wealth gap', 'income distribution', 'poverty', 'social mobility']
        }

        # Initialize analysis storage
        self.analysis_history = []

    def analyze_content(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze Paul Krugman content for economic and policy insights"""

        analysis = PaulKrugmanAgentContentAnalysis(
            video_id=content.get('video_id', ''),
            title=content.get('title', '')
        )

        # Extract macroeconomics insights
        macro_keywords = ["macroeconomics", "gdp", "inflation",
            "unemployment", "recession", "economic growth"]
        if any(
            keyword in content.get('title', '').
            lower() or keyword in content.get('description', '').lower()
            for keyword in macro_keywords):
            analysis.macroeconomics.append("Macroeconomics concept analyzed")

        # Extract international trade insights
        trade_keywords = ["trade", "globalization", "tariffs",
            "imports", "exports", "wto", "free trade"]
        if any(
            keyword in content.get('title', '').
            lower() or keyword in content.get('description', '').lower()
            for keyword in trade_keywords):
            analysis.international_trade.append(
                "International trade policy discussed")

        # Extract economic policy insights
        policy_keywords = ["policy", "stimulus", "fiscal",
            "monetary", "regulation", "government spending"]
        if any(
            keyword in content.get('title', '').
            lower() or keyword in content.get('description', '').lower()
            for keyword in policy_keywords):
            analysis.economic_policy.append(
                "Economic policy recommendation presented")

        # Extract inequality insights
        inequality_keywords = ["inequality", "wealth gap",
            "income distribution", "poverty", "social mobility"]
        if any(
            keyword in content.get('title', '').
            lower() or keyword in content.get('description', '').lower()
            for keyword in inequality_keywords):
            analysis.inequality.append("Economic inequality issue addressed")

        # Generate key takeaways
        analysis.key_takeaways = self._generate_takeaways(content, analysis)

        result = {
            'agent': 'Paul Krugman',
            'analysis': analysis,
            'timestamp': datetime.now().isoformat(),
            'content_type': 'video',
            'insights_generated': len(analysis.key_takeaways)
        }

        self.analysis_history.append(result)
        return result

    def _generate_takeaways(
            self, content: Dict[str, Any],
            analysis: PaulKrugmanAgentContentAnalysis) ->List[str]:
        """Generate economic takeaways from Paul Krugman content"""
        takeaways = []

        # Macroeconomics takeaways
        if analysis.macroeconomics:
            takeaways.append(
                "Fiscal policy can stabilize economies during recessions")
            takeaways.append(
                "Inflation and unemployment are interconnected economic forces")

        # International trade takeaways
        if analysis.international_trade:
            takeaways.append(
                "Free trade generally benefits participating countries")
            takeaways.append(
                "Protectionism often harms both importers and exporters")

        # Economic policy takeaways
        if analysis.economic_policy:
            takeaways.append(
                "Government intervention can correct market failures")
            takeaways.append(
                "Monetary policy affects economic activity through interest rates")

        # Inequality takeaways
        if analysis.inequality:
            takeaways.append(
                "Economic inequality has social and political consequences")
            takeaways.append(
                "Progressive taxation can reduce wealth concentration")

        return takeaways

    def get_strategic_insights(self) -> Dict[str, Any]:
        """Get aggregated strategic insights from Paul Krugman monitoring"""
        return {
            'agent': 'Paul Krugman',
            'total_analyses': len(self.analysis_history),
            'macroeconomics': sum(len(a['analysis'].macroeconomics) for a in self.analysis_history),
            'international_trade': sum(len(a['analysis'].international_trade) for a in self.analysis_history),
            'economic_policy': sum(len(a['analysis'].economic_policy) for a in self.analysis_history),
            'inequality': sum(len(a['analysis'].inequality) for a in self.analysis_history),
            'key_themes': self._extract_key_themes(),
            'last_updated': datetime.now().isoformat()
        }

    def _extract_key_themes(self) -> List[str]:
        """Extract key themes from analysis history"""
        themes = []
        if any(len(a['analysis'].macroeconomics) >0
               for a in self.analysis_history):
            themes.append("Macroeconomics and business cycles")
        if any(len(a['analysis'].international_trade) >0
               for a in self.analysis_history):
            themes.append("International trade and globalization")
        if any(len(a['analysis'].economic_policy) >0
               for a in self.analysis_history):
            themes.append("Economic policy and government intervention")
        if any(len(a['analysis'].inequality) > 0 for a in self.analysis_history):
            themes.append("Economic inequality and social mobility")
        return themes
