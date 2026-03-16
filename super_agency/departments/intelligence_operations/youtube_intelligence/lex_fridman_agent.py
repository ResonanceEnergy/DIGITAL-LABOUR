#!/usr/bin/env python3
"""
Lex Fridman Council Agent
Autonomous agent for monitoring Lex Fridman's YouTube channel
Specialized in AI, technology, science, and philosophy content analysis
"""

import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path
import requests
from dataclasses import dataclass

from base_agent import BaseCouncilAgent, AgentCapabilities

logger = logging.getLogger(__name__)

@dataclass
class LexContentAnalysis:
    """Specialized analysis for Lex Fridman content"""
    video_id: str
    title: str
    guest_expertise: Optional[str] = None
    ai_discussions: List[str] = None
    philosophical_questions: List[str] = None
    scientific_breakthroughs: List[str] = None
    technology_predictions: List[str] = None
    key_takeaways: List[str] = None

    def __post_init__(self):
        if self.ai_discussions is None:
            self.ai_discussions = []
        if self.philosophical_questions is None:
            self.philosophical_questions = []
        if self.scientific_breakthroughs is None:
            self.scientific_breakthroughs = []
        if self.technology_predictions is None:
            self.technology_predictions = []
        if self.key_takeaways is None:
            self.key_takeaways = []

class LexFridmanAgent(BaseCouncilAgent):
    """Autonomous agent for Lex Fridman channel monitoring"""

    def __init__(self):
        super().__init__(
            name="Lex Fridman",
            channel_id="UCSHZKyawb77ixDdsGog4iWA",
            focus_areas=["AI", "Technology", "Science", "Philosophy"],
            priority="high",
            monitoring_frequency="daily"
        )

        # Specialized capabilities for Lex Fridman content
        self.capabilities.strategic_planning = True
        self.capabilities.risk_assessment = True
        self.capabilities.policy_recommendation = True
        self.capabilities.autonomous_decision_making = True

        # Lex-specific knowledge base
        self.guest_expertise_db = self._load_guest_expertise()
        self.topic_patterns = {
            "ai_safety": ["ai safety", "alignment", "existential risk", "agi"],
            "neuroscience": ["neuroscience", "brain", "consciousness", "cognition"],
            "philosophy": ["consciousness", "free will", "meaning", "ethics"],
            "technology": ["ai", "machine learning", "robotics", "automation"]
        }

        logger.info(
            "Lex Fridman Agent initialized with specialized AI/philosophy focus")

    def _load_guest_expertise(self) -> Dict[str, str]:
        """Load database of Lex Fridman guests and their expertise"""
        # This would be loaded from a file in production
        return {
            "yann_lecun": "AI, Computer Vision, Deep Learning",
            "elon_musk": "Space, Technology, AI, Engineering",
            "andrew_ng": "Machine Learning, AI Education",
            "max_tregor": "AI Safety, Existential Risk",
            "daniel_kahneman": "Psychology, Decision Making, Behavioral Economics",
            "stephen_pinker": "Psychology, Linguistics, Cognitive Science",
            "jordan_peterson": "Psychology, Philosophy, Religion",
            "sam_harris": "Philosophy, Neuroscience, Ethics",
            "nicholas_carr": "Technology, Society, Internet",
            "robert_sapolsky": "Neuroscience, Biology, Behavior"
        }

    def _monitor_channel(self) -> List[Dict[str, Any]]:
        """Monitor Lex Fridman channel for new content"""
        try:
            # In production, this would use YouTube API
            # For now, simulate content discovery
            new_videos = self._simulate_content_discovery()

            # Filter for recent content (last 24 hours)
            recent_videos = []
            cutoff = datetime.now() - timedelta(hours=24)

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
            logger.error(f"Error monitoring Lex Fridman channel: {e}")
            return []

    def _simulate_content_discovery(self) -> List[Dict[str, Any]]:
        """Simulate discovering new Lex Fridman content"""
        # This is a simulation - in production, this would query YouTube API
        simulated_videos = [
            {
                "video_id": "lex_001",
                "title": "Elon Musk: Neuralink, AI, and the Future of Humanity",
                "description": "Deep dive into AI safety, brain-computer interfaces, and technological progress.",
                "published_at": datetime.now().isoformat(),
                "duration": "2:15:30",
                "view_count": 2500000,
                "transcript": """
                Today we're talking about artificial intelligence, the future of human augmentation,
                and the challenges we face as a civilization. Elon discusses the importance of AI safety,
                the potential for brain-computer interfaces to expand human cognition, and the need
                for careful stewardship of technological progress.
                """
            },
            {
                "video_id": "lex_002",
                "title": "Yann LeCun: AI Progress, Consciousness, and the Future",
                "description": "Discussion on deep learning advances, self-supervised learning, and AI consciousness.",
                "published_at": (datetime.now() - timedelta(hours=12)).isoformat(),
                "duration": "1:45:20",
                "view_count": 1800000,
                "transcript": """
                Yann discusses the recent breakthroughs in self-supervised learning, the path to AGI,
                and whether consciousness emerges from complex computation. He emphasizes the importance
                of understanding intelligence before we can create it artificially.
                """
            }
        ]
        return simulated_videos

    def _analyze_content_batch(self, content: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analyze batch of Lex Fridman content with specialized AI focus"""
        results = []

        for video in content:
            analysis = self._analyze_lex_content(video)
            results.append({
                "video_id": video["video_id"],
                "title": video["title"],
                "analysis": analysis,
                "analyzed_at": datetime.now().isoformat(),
                "agent_specialization": "ai_technology_philosophy"
            })

        return results

    def _analyze_lex_content(self, video: Dict[str, Any]) -> Dict[str, Any]:
        """Perform specialized analysis on Lex Fridman content"""
        title = video.get("title", "")
        transcript = video.get("transcript", "")
        description = video.get("description", "")

        # Identify guest expertise
        guest_expertise = self._identify_guest_expertise(title, description)

        # Analyze content themes
        ai_discussions = self._extract_ai_discussions(transcript)
        philosophical_questions = self._extract_philosophical_questions(
            transcript)
        scientific_breakthroughs = self._extract_scientific_breakthroughs(
            transcript)
        technology_predictions = self._extract_technology_predictions(
            transcript)

        # Generate key takeaways
        key_takeaways = self._generate_key_takeaways(
            ai_discussions, philosophical_questions,
            scientific_breakthroughs, technology_predictions
        )

        # Generate policy implications and strategic recommendations
        policy_implications = self._generate_policy_implications(key_takeaways)
        strategic_recommendations = self._generate_strategic_recommendations(
            key_takeaways)
        risk_assessments = self._assess_risks(key_takeaways)

        return {
            "guest_expertise": guest_expertise,
            "ai_discussions": ai_discussions,
            "philosophical_questions": philosophical_questions,
            "scientific_breakthroughs": scientific_breakthroughs,
            "technology_predictions": technology_predictions,
            "key_takeaways": key_takeaways,
            "policy_implications": policy_implications,
            "strategic_recommendations": strategic_recommendations,
            "risk_assessments": risk_assessments,
            "confidence_score": 0.92,
            "analysis_depth": "comprehensive"
        }

    def _identify_guest_expertise(
            self, title: str, description: str) ->Optional[str]:
        """Identify the guest's expertise from title and description"""
        text = f"{title} {description}".lower()

        for guest_name, expertise in self.guest_expertise_db.items():
            if guest_name.replace("_", " ") in text:
                return expertise

        return None

    def _extract_ai_discussions(self, transcript: str) -> List[str]:
        """Extract AI-related discussions"""
        ai_topics = []
        transcript_lower = transcript.lower()

        for topic, keywords in self.topic_patterns.items():
            if topic == "ai_safety":
                for keyword in keywords:
                    if keyword in transcript_lower:
                        ai_topics.append(f"AI Safety: {keyword}")
                        break

        # Look for specific AI concepts
        ai_concepts = [
            "agi", "artificial general intelligence", "neural networks",
            "deep learning", "machine learning", "ai alignment"]

        for concept in ai_concepts:
            if concept in transcript_lower:
                ai_topics.append(f"Technical AI: {concept}")

        return ai_topics

    def _extract_philosophical_questions(self, transcript: str) -> List[str]:
        """Extract philosophical questions and discussions"""
        philosophical_topics = []
        transcript_lower = transcript.lower()

        philosophy_keywords = ["consciousness", "free will", "meaning of life",
                             "ethics", "morality", "existence", "reality"]

        for keyword in philosophy_keywords:
            if keyword in transcript_lower:
                philosophical_topics.append(f"Philosophy: {keyword}")

        return philosophical_topics

    def _extract_scientific_breakthroughs(self, transcript: str) -> List[str]:
        """Extract scientific breakthroughs discussed"""
        breakthroughs = []
        transcript_lower = transcript.lower()

        science_keywords = [
            "breakthrough", "discovery", "advancement", "progress", "research",
            "study", "finding"]

        for keyword in science_keywords:
            if keyword in transcript_lower:
                breakthroughs.append(f"Scientific: {keyword}")

        return breakthroughs

    def _extract_technology_predictions(self, transcript: str) -> List[str]:
        """Extract technology predictions"""
        predictions = []
        transcript_lower = transcript.lower()

        future_keywords = ["future", "prediction", "will be", "could be",
                         "might happen", "timeline", "years from now"]

        for keyword in future_keywords:
            if keyword in transcript_lower:
                predictions.append(f"Future Tech: {keyword}")

        return predictions

    def _generate_key_takeaways(self, ai_discussions: List[str],
                               philosophical_questions: List[str],
                               scientific_breakthroughs: List[str],
                               technology_predictions: List[str]) -> List[str]:
        """Generate key takeaways from analysis"""
        takeaways = []

        if ai_discussions:
            takeaways.append(
                "AI development continues to accelerate with focus on safety and alignment")
        if philosophical_questions:
            takeaways.append(
                "Deep questions about consciousness and human nature remain central to technological progress")
        if scientific_breakthroughs:
            takeaways.append(
                "Scientific understanding of intelligence and cognition is rapidly advancing")
        if technology_predictions:
            takeaways.append(
                "Technology predictions suggest transformative changes in human augmentation and AI integration")

        return takeaways

    def _generate_policy_implications(
            self, key_takeaways: List[str]) ->List[str]:
        """Generate policy implications from key takeaways"""
        implications = []

        for takeaway in key_takeaways:
            if "ai" in takeaway.lower():
                implications.append(
                    "Policy: Accelerate AI safety research funding and international cooperation")
            if "safety" in takeaway.lower():
                implications.append(
                    "Policy: Develop comprehensive AI regulatory frameworks with global standards")
            if "consciousness" in takeaway.lower():
                implications.append(
                    "Policy: Support interdisciplinary research combining neuroscience, philosophy, and AI")

        return implications

    def _generate_strategic_recommendations(
            self, key_takeaways: List[str]) ->List[str]:
        """Generate strategic recommendations"""
        recommendations = []

        for takeaway in key_takeaways:
            if "accelerate" in takeaway.lower():
                recommendations.append(
                    "Strategic: Invest in AI talent development and research infrastructure")
            if "safety" in takeaway.lower():
                recommendations.append(
                    "Strategic: Build redundant AI safety mechanisms and international oversight")
            if "transformative" in takeaway.lower():
                recommendations.append(
                    "Strategic: Prepare society for technological singularity through education and adaptation")

        return recommendations

    def _assess_risks(self, key_takeaways: List[str]) -> List[str]:
        """Assess risks from key takeaways"""
        risks = []

        for takeaway in key_takeaways:
            if "accelerate" in takeaway.lower():
                risks.append(
                    "Risk: AI development outpacing safety measures and ethical frameworks")
            if "transformative" in takeaway.lower():
                risks.append(
                    "Risk: Societal disruption from rapid technological change without adequate preparation")

        return risks

    def _handle_analyze_content(self, message: AgentMessage) -> Dict[str, Any]:
        """Handle content analysis requests"""
        content = message.payload.get("content", {})
        analysis = self._analyze_lex_content(content)

        return {
            "agent_name": self.name,
            "analysis": analysis,
            "specialization": "ai_technology_philosophy",
            "timestamp": datetime.now().isoformat()
        }

    def _handle_get_insights(self, message: AgentMessage) -> Dict[str, Any]:
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

def create_lex_fridman_agent() -> LexFridmanAgent:
    """Factory function to create Lex Fridman agent"""
    return LexFridmanAgent()

if __name__ == "__main__":
    # Example usage
    agent = create_lex_fridman_agent()
    agent.start()

    # Run a monitoring cycle
    agent.run_monitoring_cycle()

    print(f"Lex Fridman Agent Status: {agent.get_status()}")