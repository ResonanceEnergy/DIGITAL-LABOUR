#!/usr/bin/env python3
"""
Demis Hassabis Council Agent
Autonomous agent for monitoring Demis Hassabis's YouTube channel
Specialized in ai, deep learning, neuroscience, technology content analysis
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
class DemisHassabisAgentContentAnalysis:
    """Specialized analysis for Demis Hassabis content"""
    video_id: str
    title: str
    ai_discussions: List[str] = None
    technology_predictions: List[str] = None
    scientific_breakthroughs: List[str] = None
    key_takeaways: List[str] = None

    def __post_init__(self):
        
        if self.ai_discussions is None:
            self.ai_discussions = []
        if self.technology_predictions is None:
            self.technology_predictions = []
        if self.scientific_breakthroughs is None:
            self.scientific_breakthroughs = []
        if self.key_takeaways is None:
            self.key_takeaways = []

class DemisHassabisAgent(BaseCouncilAgent):
    """Autonomous agent for Demis Hassabis channel monitoring"""

    def __init__(self):
        super().__init__(
            name="Demis Hassabis",
            channel_id="UCdWdJ8bRr5wlkA8Rf6Je9Hg",
            focus_areas=['AI', 'Deep Learning', 'Neuroscience', 'Technology'],
            priority="high",
            monitoring_frequency="daily"
        )

        # Specialized capabilities for Demis Hassabis content
        self.capabilities.strategic_planning = True
        self.capabilities.risk_assessment = True
        self.capabilities.policy_recommendation = True
        self.capabilities.autonomous_decision_making = True

        # Demis Hassabis-specific knowledge base
        self.topic_patterns = {
            'ai':
            ['artificial intelligence', 'machine learning', 'neural',
             'deep learning'],
            'deep learning': ['deep learning', 'deep learning related'],
            'neuroscience': ['neuroscience', 'neuroscience related'],
            'technology':
            ['tech', 'innovation', 'software', 'hardware', 'blockchain']}

        logger.info(
            "Demis Hassabis Agent initialized with specialized ai, deep learning, neuroscience, technology focus")

    def _monitor_channel(self) -> List[Dict[str, Any]]:
        """Monitor Demis Hassabis channel for new content"""
        try:
            # In production, this would use YouTube API
            # For now, simulate content discovery
            new_videos = self._simulate_content_discovery()

            # Filter for recent content (last 24 hours for daily, 7 days for weekly)
            cutoff_hours = 24 if self.monitoring_frequency == "daily" else 168
            cutoff = datetime.now() - timedelta(hours=cutoff_hours)

            recent_videos = []
            for video in new_videos:
                try:
                    published = datetime.fromisoformat(
                        video.get("published_at", "").replace("Z", "+00:00"))
                    if published > cutoff:
                        recent_videos.append(video)
                except:
                    continue

            return recent_videos

        except Exception as e:
            logger.error(f"Error monitoring Demis Hassabis channel: {e}")
            return []

    def _simulate_content_discovery(self) -> List[Dict[str, Any]]:
        """Simulate discovering new Demis Hassabis content"""
        # This is a simulation - in production, this would query YouTube API
        simulated_videos = [
            {
                "video_id": "demis_hassabis_001",
                "title": "Demis Hassabis discusses AI and future implications",
                "description": "Deep dive into ai, deep learning, neuroscience, technology with expert insights.",
                "published_at": datetime.now().isoformat(),
                "duration": "1:30:00",
                "view_count": 500000,
                "transcript": """
                Today we're exploring ai, deep learning, neuroscience, technology, the challenges we face,
                and the opportunities ahead. Demis Hassabis discusses the latest developments and their
                implications for society and technology.
                """
            }
        ]
        return simulated_videos

    def _analyze_content_batch(self, content: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analyze batch of Demis Hassabis content with specialized ai, deep learning, neuroscience, technology focus"""
        results = []

        for video in content:
            analysis = self._analyze_demis_hassabis_content(video)
            results.append({
                "video_id": video["video_id"],
                "title": video["title"],
                "analysis": analysis,
                "analyzed_at": datetime.now().isoformat(),
                "agent_specialization": "ai_deep learning_neuroscience_technology"
            })

        return results

    def _analyze_demis_hassabis_content(self, video: Dict[str, Any]) -> Dict[str, Any]:
        """Perform specialized analysis on Demis Hassabis content"""
        title = video.get("title", "")
        transcript = video.get("transcript", "")
        description = video.get("description", "")

        # Analyze content themes
        ai_discussions = self._extract_ai_discussions(transcript)
        technology_predictions = self._extract_technology_predictions(
            transcript)
        scientific_breakthroughs = self._extract_scientific_breakthroughs(
            transcript)

        # Generate key takeaways
        key_takeaways = self._generate_key_takeaways(
            ai_discussions, technology_predictions, scientific_breakthroughs)

        # Generate policy implications and strategic recommendations
        policy_implications = self._generate_policy_implications(key_takeaways)
        strategic_recommendations = self._generate_strategic_recommendations(
            key_takeaways)
        risk_assessments = self._assess_risks(key_takeaways)

        return {
            "ai_discussions": ai_discussions,
            "technology_predictions": technology_predictions,
            "scientific_breakthroughs": scientific_breakthroughs,
            "key_takeaways": key_takeaways,
            "policy_implications": policy_implications,
            "strategic_recommendations": strategic_recommendations,
            "risk_assessments": risk_assessments,
            "confidence_score": 0.90,
            "analysis_depth": "comprehensive"
        }

    
    def _extract_ai_discussions(self, transcript: str) -> List[str]:
        discussions = []
        transcript_lower = transcript.lower()
        ai_keywords = ["ai", "artificial intelligence",
            "machine learning", "neural", "deep learning"]
        for keyword in ai_keywords:
            if keyword in transcript_lower:
                discussions.append(f"AI Discussion: {keyword}")
        return discussions

    def _extract_technology_predictions(self, transcript: str) -> List[str]:
        predictions = []
        transcript_lower = transcript.lower()
        future_keywords = ["future", "prediction",
            "will", "could", "might", "timeline"]
        for keyword in future_keywords:
            if keyword in transcript_lower:
                predictions.append(f"Tech Prediction: {keyword}")
        return predictions

    def _extract_scientific_breakthroughs(self, transcript: str) -> List[str]:
        breakthroughs = []
        transcript_lower = transcript.lower()
        science_keywords = ["breakthrough",
            "discovery", "advancement", "research"]
        for keyword in science_keywords:
            if keyword in transcript_lower:
                breakthroughs.append(f"Scientific: {keyword}")
        return breakthroughs

    def _generate_key_takeaways(
            self, ai_discussions: List[str],
            technology_predictions: List[str],
            scientific_breakthroughs: List[str]) ->List[str]:
        """Generate key takeaways from analysis"""
        takeaways = []

        
        if ai_discussions:
            takeaways.append(
                "AI development continues to advance with new breakthroughs")
        if technology_predictions:
            takeaways.append(
                "Technology predictions suggest transformative changes ahead")
        if scientific_breakthroughs:
            takeaways.append(
                "Scientific understanding of intelligence is rapidly progressing")

        return takeaways

    def _generate_policy_implications(
            self, key_takeaways: List[str]) ->List[str]:
        """Generate policy implications from key takeaways"""
        implications = []

        for takeaway in key_takeaways:
            takeaway_lower = takeaway.lower()
            if "ai" in takeaway_lower:
                implications.append(
                    "Policy: Develop comprehensive AI governance frameworks")
            if "tech" in takeaway_lower:
                implications.append(
                    "Policy: Support technology innovation and infrastructure development")

        return implications

    def _generate_strategic_recommendations(
            self, key_takeaways: List[str]) ->List[str]:
        """Generate strategic recommendations"""
        recommendations = []

        for takeaway in key_takeaways:
            takeaway_lower = takeaway.lower()
            if "ai" in takeaway_lower:
                recommendations.append(
                    "Strategic: Invest in AI talent development and ethical AI practices")
            if "tech" in takeaway_lower:
                recommendations.append(
                    "Strategic: Accelerate technology adoption and digital transformation")

        return recommendations

    def _assess_risks(self, key_takeaways: List[str]) -> List[str]:
        """Assess risks from key takeaways"""
        risks = []

        for takeaway in key_takeaways:
            takeaway_lower = takeaway.lower()
            if "ai" in takeaway_lower:
                risks.append(
                    "Risk: AI development may outpace safety and ethical considerations")
            if "tech" in takeaway_lower:
                risks.append(
                    "Risk: Rapid technological change may cause societal disruption")

        return risks

    def _handle_analyze_content(self, message) -> Dict[str, Any]:
        """Handle content analysis requests"""
        content = message.payload.get("content", {})
        analysis = self._analyze_demis_hassabis_content(content)

        return {
            "agent_name": self.name,
            "analysis": analysis,
            "specialization": "ai_deep learning_neuroscience_technology",
            "timestamp": datetime.now().isoformat()
        }

    def _handle_get_insights(self, message) -> Dict[str, Any]:
        """Handle insight requests"""
        insights = self._get_recent_insights()

        return {
            "agent_name": self.name,
            "insights": insights,
            "focus_areas": self.focus_areas,
            "timestamp": datetime.now().isoformat()
        }

    def _get_recent_insights(self) -> List[Dict[str, Any]]:
        """Get recent insights from stored analysis"""
        try:
            # Get latest analysis file
            analysis_files = list(self.data_dir.glob("analysis_*.json"))
            if not analysis_files:
                return []

            latest_file = max(analysis_files, key=lambda x: x.stat().st_mtime)

            with open(latest_file, 'r') as f:
                data = json.load(f)

            # Extract insights from analysis
            insights = []
            for item in data:
                analysis = item.get("analysis", {})
                insights.extend(analysis.get("key_takeaways", []))

            return insights

        except Exception as e:
            logger.error(f"Error getting recent insights: {e}")
            return []

def create_demis_hassabis_agent():
    """Factory function to create Demis Hassabis agent"""
    return DemisHassabisAgent()

if __name__ == "__main__":
    # Example usage
    agent = create_demis_hassabis_agent()
    agent.start()

    # Run a monitoring cycle
    agent.run_monitoring_cycle()

    print(f"{name} Agent Status: {agent.get_status()}")
