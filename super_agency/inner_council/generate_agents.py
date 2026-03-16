#!/usr/bin/env python3
"""
Inner Council Agent Generator
Automatically generate specialized agents for all council members
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

def load_council_config() -> List[Dict[str, Any]]:
    """Load council member configuration"""
    config_path = Path(__file__).parent / "config" / "settings.json"
    with open(config_path, 'r') as f:
        config = json.load(f)
    return config.get("council_members", [])

def generate_agent_code(member: Dict[str, Any]) -> str:
    """Generate agent code for a council member"""

    name = member["name"]
    channel_id = member["channel_id"]
    focus_areas = member["focus_areas"]
    priority = member["priority"]
    monitoring_frequency = member["monitoring_frequency"]

    # Create safe filename
    safe_name = name.lower().replace(
        " ", "_").replace(
        "'", "").replace(
        "-", "_")
    class_name = f"{safe_name.title().replace('_', '')}Agent"

    # Determine specialization based on focus areas
    specialization = get_specialization_from_focus_areas(focus_areas)

    agent_code = f'''#!/usr/bin/env python3
"""
{name} Council Agent
Autonomous agent for monitoring {name}'s YouTube channel
Specialized in {", ".join(focus_areas).lower()} content analysis
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
class {class_name}ContentAnalysis:
    """Specialized analysis for {name} content"""
    video_id: str
    title: str
    {generate_specialization_fields(specialization)}
    key_takeaways: List[str] = None

    def __post_init__(self):
        {generate_field_initializations(specialization)}
        if self.key_takeaways is None:
            self.key_takeaways = []

class {class_name}(BaseCouncilAgent):
    """Autonomous agent for {name} channel monitoring"""

    def __init__(self):
        super().__init__(
            name="{name}",
            channel_id="{channel_id}",
            focus_areas={focus_areas},
            priority="{priority}",
            monitoring_frequency="{monitoring_frequency}"
        )

        # Specialized capabilities for {name} content
        {generate_capabilities(specialization)}

        # {name}-specific knowledge base
        self.topic_patterns = {generate_topic_patterns(focus_areas)}

        logger.info("{name} Agent initialized with specialized {', '.join(focus_areas).lower()} focus")

    def _monitor_channel(self) -> List[Dict[str, Any]]:
        """Monitor {name} channel for new content"""
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
                    published = datetime.fromisoformat(video.get("published_at", "").replace("Z", "+00:00"))
                    if published > cutoff:
                        recent_videos.append(video)
                except:
                    continue

            return recent_videos

        except Exception as e:
            logger.error(f"Error monitoring {name} channel: {{e}}")
            return []

    def _simulate_content_discovery(self) -> List[Dict[str, Any]]:
        """Simulate discovering new {name} content"""
        # This is a simulation - in production, this would query YouTube API
        simulated_videos = [
            {{
                "video_id": "{safe_name}_001",
                "title": "{name} discusses {focus_areas[0]} and future implications",
                "description": "Deep dive into {', '.join(focus_areas).lower()} with expert insights.",
                "published_at": datetime.now().isoformat(),
                "duration": "1:30:00",
                "view_count": 500000,
                "transcript": """
                Today we're exploring {', '.join(focus_areas).lower()}, the challenges we face,
                and the opportunities ahead. {name} discusses the latest developments and their
                implications for society and technology.
                """
            }}
        ]
        return simulated_videos

    def _analyze_content_batch(self, content: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analyze batch of {name} content with specialized {', '.join(focus_areas).lower()} focus"""
        results = []

        for video in content:
            analysis = self._analyze_{safe_name}_content(video)
            results.append({{
                "video_id": video["video_id"],
                "title": video["title"],
                "analysis": analysis,
                "analyzed_at": datetime.now().isoformat(),
                "agent_specialization": "{"_".join(focus_areas).lower()}"
            }})

        return results

    def _analyze_{safe_name}_content(self, video: Dict[str, Any]) -> Dict[str, Any]:
        """Perform specialized analysis on {name} content"""
        title = video.get("title", "")
        transcript = video.get("transcript", "")
        description = video.get("description", "")

        # Analyze content themes
        {generate_analysis_methods(specialization, safe_name)}

        # Generate key takeaways
        key_takeaways = self._generate_key_takeaways({generate_takeaways_params(specialization)})

        # Generate policy implications and strategic recommendations
        policy_implications = self._generate_policy_implications(key_takeaways)
        strategic_recommendations = self._generate_strategic_recommendations(key_takeaways)
        risk_assessments = self._assess_risks(key_takeaways)

        return {{
            {generate_return_fields(specialization)}
            "key_takeaways": key_takeaways,
            "policy_implications": policy_implications,
            "strategic_recommendations": strategic_recommendations,
            "risk_assessments": risk_assessments,
            "confidence_score": 0.90,
            "analysis_depth": "comprehensive"
        }}

    {generate_analysis_implementations(specialization, safe_name)}

    def _generate_key_takeaways(self, {generate_takeaways_signature(specialization)}) -> List[str]:
        """Generate key takeaways from analysis"""
        takeaways = []

        {generate_takeaways_logic(specialization)}

        return takeaways

    def _generate_policy_implications(self, key_takeaways: List[str]) -> List[str]:
        """Generate policy implications from key takeaways"""
        implications = []

        for takeaway in key_takeaways:
            takeaway_lower = takeaway.lower()
            {generate_policy_logic(focus_areas)}

        return implications

    def _generate_strategic_recommendations(self, key_takeaways: List[str]) -> List[str]:
        """Generate strategic recommendations"""
        recommendations = []

        for takeaway in key_takeaways:
            takeaway_lower = takeaway.lower()
            {generate_strategy_logic(focus_areas)}

        return recommendations

    def _assess_risks(self, key_takeaways: List[str]) -> List[str]:
        """Assess risks from key takeaways"""
        risks = []

        for takeaway in key_takeaways:
            takeaway_lower = takeaway.lower()
            {generate_risk_logic(focus_areas)}

        return risks

    def _handle_analyze_content(self, message) -> Dict[str, Any]:
        """Handle content analysis requests"""
        content = message.payload.get("content", {{}})
        analysis = self._analyze_{safe_name}_content(content)

        return {{
            "agent_name": self.name,
            "analysis": analysis,
            "specialization": "{"_".join(focus_areas).lower()}",
            "timestamp": datetime.now().isoformat()
        }}

    def _handle_get_insights(self, message) -> Dict[str, Any]:
        """Handle insight requests"""
        insights = self._get_recent_insights()

        return {{
            "agent_name": self.name,
            "insights": insights,
            "focus_areas": self.focus_areas,
            "timestamp": datetime.now().isoformat()
        }}

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
                analysis = item.get("analysis", {{}})
                insights.extend(analysis.get("key_takeaways", []))

            return insights

        except Exception as e:
            logger.error(f"Error getting recent insights: {{e}}")
            return []

def create_{safe_name}_agent():
    """Factory function to create {name} agent"""
    return {class_name}()

if __name__ == "__main__":
    # Example usage
    agent = create_{safe_name}_agent()
    agent.start()

    # Run a monitoring cycle
    agent.run_monitoring_cycle()

    print(f"{{name}} Agent Status: {{agent.get_status()}}")
'''

    return agent_code

def get_specialization_from_focus_areas(focus_areas: List[str]) -> str:
    """Determine specialization type from focus areas"""
    if "AI" in focus_areas or "Technology" in focus_areas:
        return "tech_ai"
    elif "Business" in focus_areas or "Entrepreneurship" in focus_areas:
        return "business"
    elif "Science" in focus_areas or "Neuroscience" in focus_areas:
        return "science"
    elif "Politics" in focus_areas or "Culture" in focus_areas:
        return "politics_culture"
    else:
        return "general"

def generate_specialization_fields(specialization: str) -> str:
    """Generate specialization-specific fields"""
    if specialization == "tech_ai":
        return """ai_discussions: List[str] = None
    technology_predictions: List[str] = None
    scientific_breakthroughs: List[str] = None"""
    elif specialization == "business":
        return """business_strategies: List[str] = None
    market_insights: List[str] = None
    leadership_lessons: List[str] = None"""
    elif specialization == "science":
        return """scientific_discoveries: List[str] = None
    research_findings: List[str] = None
    methodological_advances: List[str] = None"""
    elif specialization == "politics_culture":
        return """political_analysis: List[str] = None
    cultural_insights: List[str] = None
    societal_trends: List[str] = None"""
    else:
        return """general_insights: List[str] = None"""

def generate_field_initializations(specialization: str) -> str:
    """Generate field initializations"""
    if specialization == "tech_ai":
        return """
        if self.ai_discussions is None:
            self.ai_discussions = []
        if self.technology_predictions is None:
            self.technology_predictions = []
        if self.scientific_breakthroughs is None:
            self.scientific_breakthroughs = []"""
    elif specialization == "business":
        return """
        if self.business_strategies is None:
            self.business_strategies = []
        if self.market_insights is None:
            self.market_insights = []
        if self.leadership_lessons is None:
            self.leadership_lessons = []"""
    elif specialization == "science":
        return """
        if self.scientific_discoveries is None:
            self.scientific_discoveries = []
        if self.research_findings is None:
            self.research_findings = []
        if self.methodological_advances is None:
            self.methodological_advances = []"""
    elif specialization == "politics_culture":
        return """
        if self.political_analysis is None:
            self.political_analysis = []
        if self.cultural_insights is None:
            self.cultural_insights = []
        if self.societal_trends is None:
            self.societal_trends = []"""
    else:
        return """
        if self.general_insights is None:
            self.general_insights = []"""

def generate_capabilities(specialization: str) -> str:
    """Generate agent capabilities based on specialization"""
    if specialization == "tech_ai":
        return """self.capabilities.strategic_planning = True
        self.capabilities.risk_assessment = True
        self.capabilities.policy_recommendation = True
        self.capabilities.autonomous_decision_making = True"""
    elif specialization == "business":
        return """self.capabilities.strategic_planning = True
        self.capabilities.policy_recommendation = True
        self.capabilities.autonomous_decision_making = False"""
    elif specialization == "science":
        return """self.capabilities.risk_assessment = True
        self.capabilities.policy_recommendation = True
        self.capabilities.autonomous_decision_making = False"""
    elif specialization == "politics_culture":
        return """self.capabilities.strategic_planning = True
        self.capabilities.risk_assessment = True
        self.capabilities.autonomous_decision_making = False"""
    else:
        return """# General capabilities
        self.capabilities.strategic_planning = False
        self.capabilities.risk_assessment = False
        self.capabilities.policy_recommendation = False
        self.capabilities.autonomous_decision_making = False"""

def generate_topic_patterns(focus_areas: List[str]) -> str:
    """Generate topic patterns based on focus areas"""
    patterns = {}
    for area in focus_areas:
        area_lower = area.lower()
        if area_lower == "ai":
            patterns["ai"] = ["artificial intelligence",
                "machine learning", "neural", "deep learning"]
        elif area_lower == "technology":
            patterns["technology"] = ["tech", "innovation",
                "software", "hardware", "blockchain"]
        elif area_lower == "business":
            patterns["business"] = ["business", "startup",
                "entrepreneur", "finance", "market"]
        elif area_lower == "science":
            patterns["science"] = ["science", "research",
                "biology", "physics", "study"]
        else:
            patterns[area_lower] = [area_lower, f"{area_lower} related"]

    return str(patterns)

def generate_analysis_methods(specialization: str, safe_name: str) -> str:
    """Generate analysis method calls"""
    if specialization == "tech_ai":
        return f"""ai_discussions = self._extract_ai_discussions(transcript)
        technology_predictions = self._extract_technology_predictions(transcript)
        scientific_breakthroughs = self._extract_scientific_breakthroughs(transcript)"""
    elif specialization == "business":
        return f"""
            business_strategies = self._extract_business_strategies(transcript)
        market_insights = self._extract_market_insights(transcript)
        leadership_lessons = self._extract_leadership_lessons(transcript)
            """
    elif specialization == "science":
        return f"""
            scientific_discoveries = self._extract_scientific_discoveries(transcript)
        research_findings = self._extract_research_findings(transcript)
        methodological_advances = self._extract_methodological_advances(transcript)
            """
    elif specialization == "politics_culture":
        return f"""
            political_analysis = self._extract_political_analysis(transcript)
        cultural_insights = self._extract_cultural_insights(transcript)
        societal_trends = self._extract_societal_trends(transcript)
            """
    else:
        return f"""
            general_insights = self._extract_general_insights(transcript) """

def generate_takeaways_params(specialization: str) -> str:
    """Generate takeaways method parameters"""
    if specialization == "tech_ai":
        return "ai_discussions, technology_predictions, scientific_breakthroughs"
    elif specialization == "business":
        return "business_strategies, market_insights, leadership_lessons"
    elif specialization == "science":
        return "scientific_discoveries, research_findings, methodological_advances"
    elif specialization == "politics_culture":
        return "political_analysis, cultural_insights, societal_trends"
    else:
        return "general_insights"

def generate_return_fields(specialization: str) -> str:
    """Generate return fields for analysis"""
    if specialization == "tech_ai":
        return """"ai_discussions": ai_discussions,
            "technology_predictions": technology_predictions,
            "scientific_breakthroughs": scientific_breakthroughs,"""
    elif specialization == "business":
        return """"business_strategies": business_strategies,
            "market_insights": market_insights,
            "leadership_lessons": leadership_lessons,"""
    elif specialization == "science":
        return """"scientific_discoveries": scientific_discoveries,
            "research_findings": research_findings,
            "methodological_advances": methodological_advances,"""
    elif specialization == "politics_culture":
        return """"political_analysis": political_analysis,
            "cultural_insights": cultural_insights,
            "societal_trends": societal_trends,"""
    else:
        return """"general_insights": general_insights,"""

def generate_analysis_implementations(
        specialization: str, safe_name: str) ->str:
    """Generate analysis implementation methods"""
    methods = []

    if specialization == "tech_ai":
        methods.extend([
            """
    def _extract_ai_discussions(self, transcript: str) -> List[str]:
        discussions = []
        transcript_lower = transcript.lower()
        ai_keywords = ["ai", "artificial intelligence", "machine learning", "neural", "deep learning"]
        for keyword in ai_keywords:
            if keyword in transcript_lower:
                discussions.append(f"AI Discussion: {keyword}")
        return discussions""",
            """
    def _extract_technology_predictions(self, transcript: str) -> List[str]:
        predictions = []
        transcript_lower = transcript.lower()
        future_keywords = ["future", "prediction", "will", "could", "might", "timeline"]
        for keyword in future_keywords:
            if keyword in transcript_lower:
                predictions.append(f"Tech Prediction: {keyword}")
        return predictions""",
            """
    def _extract_scientific_breakthroughs(self, transcript: str) -> List[str]:
        breakthroughs = []
        transcript_lower = transcript.lower()
        science_keywords = ["breakthrough", "discovery", "advancement", "research"]
        for keyword in science_keywords:
            if keyword in transcript_lower:
                breakthroughs.append(f"Scientific: {keyword}")
        return breakthroughs"""
        ])
    elif specialization == "business":
        methods.extend([
            """
    def _extract_business_strategies(self, transcript: str) -> List[str]:
        strategies = []
        transcript_lower = transcript.lower()
        strategy_keywords = ["strategy", "business model", "growth", "scaling"]
        for keyword in strategy_keywords:
            if keyword in transcript_lower:
                strategies.append(f"Business Strategy: {keyword}")
        return strategies""",
            """
    def _extract_market_insights(self, transcript: str) -> List[str]:
        insights = []
        transcript_lower = transcript.lower()
        market_keywords = ["market", "industry", "trend", "opportunity"]
        for keyword in market_keywords:
            if keyword in transcript_lower:
                insights.append(f"Market Insight: {keyword}")
        return insights""",
            """
    def _extract_leadership_lessons(self, transcript: str) -> List[str]:
        lessons = []
        transcript_lower = transcript.lower()
        leadership_keywords = ["leadership", "team", "management", "culture"]
        for keyword in leadership_keywords:
            if keyword in transcript_lower:
                lessons.append(f"Leadership: {keyword}")
        return lessons"""
        ])

    return "\n".join(methods)

def generate_takeaways_signature(specialization: str) -> str:
    """Generate takeaways method signature"""
    if specialization == "tech_ai":
        return "ai_discussions: List[str], technology_predictions: List[str], scientific_breakthroughs: List[str]"
    elif specialization == "business":
        return "business_strategies: List[str], market_insights: List[str], leadership_lessons: List[str]"
    elif specialization == "science":
        return "scientific_discoveries: List[str], research_findings: List[str], methodological_advances: List[str]"
    elif specialization == "politics_culture":
        return "political_analysis: List[str], cultural_insights: List[str], societal_trends: List[str]"
    else:
        return "general_insights: List[str]"

def generate_takeaways_logic(specialization: str) -> str:
    """Generate takeaways logic"""
    if specialization == "tech_ai":
        return """
        if ai_discussions:
            takeaways.append("AI development continues to advance with new breakthroughs")
        if technology_predictions:
            takeaways.append("Technology predictions suggest transformative changes ahead")
        if scientific_breakthroughs:
            takeaways.append("Scientific understanding of intelligence is rapidly progressing")"""
    elif specialization == "business":
        return """
        if business_strategies:
            takeaways.append("New business strategies emerging for competitive advantage")
        if market_insights:
            takeaways.append("Market dynamics shifting with new opportunities and challenges")
        if leadership_lessons:
            takeaways.append("Leadership approaches evolving to meet modern business demands")"""
    else:
        return """
        takeaways.append("Content analysis reveals important insights and trends")
        takeaways.append("Key themes and patterns identified for further consideration")"""

def generate_policy_logic(focus_areas: List[str]) -> str:
    """Generate policy implication logic"""
    logic = []
    for area in focus_areas:
        if area == "AI":
            logic.append(f"""if "ai" in takeaway_lower:
                implications.append("Policy: Develop comprehensive AI governance frameworks")""")
        elif area == "Technology":
            logic.append(f"""if "tech" in takeaway_lower:
                implications.append("Policy: Support technology innovation and infrastructure development")""")
        elif area == "Business":
            logic.append(f"""if "business" in takeaway_lower:
                implications.append("Policy: Foster entrepreneurship and economic growth initiatives")""")
        elif area == "Science":
            logic.append(f"""if "science" in takeaway_lower:
                implications.append("Policy: Increase funding for scientific research and education")""")
    return "\n            ".join(logic) if logic else """implications.append("Policy: Monitor developments and assess regulatory needs")"""

def generate_strategy_logic(focus_areas: List[str]) -> str:
    """Generate strategic recommendation logic"""
    logic = []
    for area in focus_areas:
        if area == "AI":
            logic.append(f"""if "ai" in takeaway_lower:
                recommendations.append("Strategic: Invest in AI talent development and ethical AI practices")""")
        elif area == "Technology":
            logic.append(f"""if "tech" in takeaway_lower:
                recommendations.append("Strategic: Accelerate technology adoption and digital transformation")""")
        elif area == "Business":
            logic.append(f"""if "business" in takeaway_lower:
                recommendations.append("Strategic: Adapt business models to emerging market conditions")""")
        elif area == "Science":
            logic.append(f"""if "science" in takeaway_lower:
                recommendations.append("Strategic: Build interdisciplinary research collaborations")""")
    return "\n            ".join(logic) if logic else """recommendations.append("Strategic: Monitor trends and prepare for emerging opportunities")"""

def generate_risk_logic(focus_areas: List[str]) -> str:
    """Generate risk assessment logic"""
    logic = []
    for area in focus_areas:
        if area == "AI":
            logic.append(f"""if "ai" in takeaway_lower:
                risks.append("Risk: AI development may outpace safety and ethical considerations")""")
        elif area == "Technology":
            logic.append(f"""if "tech" in takeaway_lower:
                risks.append("Risk: Rapid technological change may cause societal disruption")""")
        elif area == "Business":
            logic.append(f"""if "business" in takeaway_lower:
                risks.append("Risk: Market volatility and competitive pressures increasing")""")
        elif area == "Science":
            logic.append(f"""if "science" in takeaway_lower:
                risks.append("Risk: Scientific advances may raise ethical and societal concerns")""")
    return "\n            ".join(logic) if logic else """risks.append("Risk: Monitor developments for potential challenges and concerns")"""

def generate_agents():
    """Generate agent files for all council members"""
    council_members = load_council_config()

    agents_dir = Path(__file__).parent / "agents"
    agents_dir.mkdir(exist_ok=True)

    generated_agents = []

    for member in council_members:
        name = member["name"]
        safe_name = name.lower().replace(
            " ", "_").replace(
            "'", "").replace(
            "-", "_")

        # Skip if already exists
        agent_file = agents_dir / f"{safe_name}_agent.py"
        if agent_file.exists():
            print(f"Skipping {name} - agent already exists")
            continue

        # Generate agent code
        agent_code = generate_agent_code(member)

        # Write agent file
        with open(agent_file, 'w') as f:
            f.write(agent_code)

        generated_agents.append(name)
        print(f"Generated agent for {name}")

    # Generate agent registry
    generate_agent_registry(council_members)

    print(f"\nGenerated {len(generated_agents)} new agents")
    return generated_agents

def generate_agent_registry(council_members: List[Dict[str, Any]]):
    """Generate agent registry for easy importing"""
    registry_code = '''#!/usr/bin/env python3
"""
Inner Council Agent Registry
Central registry for all council member agents
"""

from typing import Dict, Type, Any
import importlib

# Agent registry
AGENT_REGISTRY = {}

def register_agent(agent_class: Type[Any]):
    """Register an agent class"""
    agent_name = agent_class.__name__.replace("Agent", "").lower()
    AGENT_REGISTRY[agent_name] = agent_class

def get_agent_class(agent_name: str) -> Type[Any]:
    """Get agent class by name"""
    return AGENT_REGISTRY.get(agent_name.lower())

def create_all_agents() -> Dict[str, Any]:
    """Create instances of all registered agents"""
    agents = {}
    for name, agent_class in AGENT_REGISTRY.items():
        try:
            agent = agent_class()
            agents[name] = agent
        except Exception as e:
            print(f"Error creating agent {name}: {e}")
    return agents

# Import all agent modules
'''

    # Add imports for all agents
    for member in council_members:
        safe_name = member["name"].lower().replace(
            " ", "_").replace("'", "").replace("-", "_")
        registry_code += f"from {safe_name}_agent import *\n"

    registry_code += '''

# Register all agents
'''

    # Add registration calls
    for member in council_members:
        safe_name = member["name"].lower().replace(
            " ", "_").replace("'", "").replace("-", "_")
        class_name = f"{safe_name.title().replace('_', '')}Agent"
        registry_code += f"register_agent({class_name})\n"

    # Write registry file
    registry_path = Path(__file__).parent / "agents" / "agent_registry.py"
    with open(registry_path, 'w') as f:
        f.write(registry_code)

    print("Generated agent registry")

if __name__ == "__main__":
    generate_agents()