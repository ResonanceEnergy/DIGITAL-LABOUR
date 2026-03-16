#!/usr/bin/env python3
"""
NCC Intelligence Synthesizer
Combines Council 52 intelligence with operational data for command decisions
"""

import json
import os
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging
from collections import defaultdict

class NCCIntelligenceSynthesizer:
    """Neural Command Center - Intelligence synthesis and analysis"""

    def __init__(self, config_path: str = "ncc_intelligence_config.json"):
        self.config_path = config_path
        self.config = self.load_config()
        self.setup_logging()
        self.intelligence_cache = {}
        self.synthesis_history = []

    def load_config(self) -> Dict:
        """Load intelligence synthesis configuration"""
        default_config = {
            "synthesis": {
                "max_cache_age_hours": 24,
                "correlation_threshold": 0.7,
                "priority_weighting": {
                    "critical": 1.0,
                    "high": 0.8,
                    "medium": 0.6,
                    "low": 0.4
                },
                "source_reliability": {
                    "council_52": 0.95,
                    "ncl_processing": 0.90,
                    "api_monitoring": 0.85,
                    "system_logs": 0.75
                }
            },
            "analysis": {
                "trend_detection": True,
                "anomaly_detection": True,
                "predictive_insights": True,
                "ethical_filtering": True
            }
        }

        if os.path.exists(self.config_path):
            with open(self.config_path, 'r') as f:
                user_config = json.load(f)
                self.deep_update(default_config, user_config)

        return default_config

    def deep_update(self, base_dict: Dict, update_dict: Dict):
        """Deep update dictionary"""
        for key, value in update_dict.items():
            if isinstance(value, dict) and key in base_dict:
                self.deep_update(base_dict[key], value)
            else:
                base_dict[key] = value

    def setup_logging(self):
        """Setup intelligence synthesis logging"""
        os.makedirs("ncc_logs", exist_ok=True)

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - NCC-Intelligence - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('ncc_logs/intelligence_synthesis.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger("NCC-Intelligence")

    def synthesize_intelligence(self, sources: List[Dict]) -> Dict:
        """Synthesize intelligence from multiple sources"""

        synthesis_id = f"synth_{int(datetime.now().timestamp())}"

        # Collect intelligence from all sources
        raw_intelligence = []
        for source in sources:
            intelligence = self.extract_source_intelligence(source)
            if intelligence:
                raw_intelligence.extend(intelligence)

        # Correlate and deduplicate
        correlated_intelligence = self.correlate_intelligence(raw_intelligence)

        # Apply priority weighting
        prioritized_intelligence = self.apply_priority_weighting(
            correlated_intelligence)

        # Generate insights
        insights = self.generate_insights(prioritized_intelligence)

        # Create synthesis report
        synthesis = {
            "id": synthesis_id,
            "timestamp": datetime.now().isoformat(),
            "sources_processed": len(sources),
            "intelligence_items": len(correlated_intelligence),
            "insights_generated": len(insights),
            "top_insights": insights[:5],  # Top 5 insights
            "priority_distribution": self.analyze_priority_distribution(prioritized_intelligence),
            "confidence_metrics": self.calculate_confidence_metrics(correlated_intelligence),
            "recommendations": self.generate_recommendations(insights)
        }

        # Cache synthesis
        self.intelligence_cache[synthesis_id] = synthesis
        self.synthesis_history.append(synthesis)

        # Keep cache size manageable
        if len(self.intelligence_cache) > 100:
            oldest_key = min(
                self.intelligence_cache.keys(),
                key=lambda k: self.intelligence_cache[k] ["timestamp"])
            del self.intelligence_cache[oldest_key]

        self.logger.info(
            f"Intelligence synthesis completed: {synthesis_id} - {len(insights)} insights")
        return synthesis

    def extract_source_intelligence(self, source: Dict) -> List[Dict]:
        """Extract intelligence from a specific source"""

        source_type = source.get("type", "unknown")
        source_data = source.get("data", {})

        intelligence_items = []

        if source_type == "council_52":
            intelligence_items.extend(
                self.extract_council_52_intelligence(source_data))
        elif source_type == "ncl_processing":
            intelligence_items.extend(
                self.extract_ncl_intelligence(source_data))
        elif source_type == "api_monitoring":
            intelligence_items.extend(
                self.extract_api_intelligence(source_data))
        elif source_type == "system_logs":
            intelligence_items.extend(
                self.extract_system_intelligence(source_data))

        return intelligence_items

    def extract_council_52_intelligence(self, data: Dict) -> List[Dict]:
        """Extract intelligence from Council 52 data"""
        intelligence = []

        # Process directives from intelligence monitor
        directives = data.get("directives", [])
        for directive in directives:
            intelligence.append({
                "source": "council_52",
                "type": "directive",
                "content": directive.get("summary", ""),
                "priority": directive.get("priority_level", "medium"),
                "confidence": directive.get("confidence_score", 0.5),
                "timestamp": directive.get("created_at", datetime.now().isoformat()),
                "metadata": {
                    "channel": directive.get("source_channel", ""),
                    "role": directive.get("source_role", "")
                }
            })

        return intelligence

    def extract_ncl_intelligence(self, data: Dict) -> List[Dict]:
        """Extract intelligence from NCL processing"""
        intelligence = []

        # Process NCL classifications and routing
        classifications = data.get("classifications", [])
        for classification in classifications:
            intelligence.append({
                "source": "ncl_processing",
                "type": "classification",
                "content": f"Categorized as: {classification.get('category', 'unknown')}",
                "priority": "medium",
                "confidence": classification.get("confidence", 0.5),
                "timestamp": datetime.now().isoformat(),
                "metadata": classification
            })

        return intelligence

    def extract_api_intelligence(self, data: Dict) -> List[Dict]:
        """Extract intelligence from API monitoring"""
        intelligence = []

        # Process API call patterns and errors
        api_calls = data.get("api_calls", [])
        for call in api_calls:
            if call.get("success") == False:
                intelligence.append({
                    "source": "api_monitoring",
                    "type": "api_issue",
                    "content": f"API failure: {call.get('endpoint', 'unknown')} - {call.get('error_details', '')}",
                    "priority": "high" if "rate limit" in str(call).lower() else "medium",
                    "confidence": 0.8,
                    "timestamp": call.get("timestamp", datetime.now().isoformat()),
                    "metadata": call
                })

        return intelligence

    def extract_system_intelligence(self, data: Dict) -> List[Dict]:
        """Extract intelligence from system logs"""
        intelligence = []

        # Process system events and anomalies
        events = data.get("events", [])
        for event in events:
            if "error" in event.get(
                "level", "").lower() or "warning" in event.get(
                "level", "").lower():
                intelligence.append(
                    {"source": "system_logs", "type": "system_event",
                     "content": event.get("message", ""),
                     "priority": "high"
                     if "error" in event.get("level", "").lower() else
                      "medium", "confidence": 0.7, "timestamp": event.get(
                         "timestamp", datetime.now().isoformat()),
                     "metadata": event})

        return intelligence

    def correlate_intelligence(
            self, intelligence_items: List[Dict]) ->List[Dict]:
        """Correlate and deduplicate intelligence items"""

        # Group by content similarity
        content_groups = defaultdict(list)

        for item in intelligence_items:
            # Create content signature for grouping
            content_sig = self.create_content_signature(item["content"])
            content_groups[content_sig].append(item)

        # Merge correlated items
        correlated = []
        for sig, items in content_groups.items():
            if len(items) == 1:
                correlated.append(items[0])
            else:
                # Merge multiple items
                merged = self.merge_similar_intelligence(items)
                correlated.append(merged)

        return correlated

    def create_content_signature(self, content: str) -> str:
        """Create a signature for content similarity matching"""
        # Simple signature based on key terms
        words = re.findall(r'\b\w+\b', content.lower())
        key_terms = [w for w in words if len(w) > 3]
        return "_".join(sorted(set(key_terms))[:5])  # Top 5 key terms

    def merge_similar_intelligence(self, items: List[Dict]) -> Dict:
        """Merge similar intelligence items"""
        # Use highest priority and confidence
        priorities = ["low", "medium", "high", "critical"]
        priority_values = {p: i for i, p in enumerate(priorities)}

        best_item = max(items, key=lambda x: (
            priority_values.get(x["priority"], 0),
            x["confidence"]
        ))

        # Combine metadata
        all_metadata = {}
        for item in items:
            all_metadata.update(item.get("metadata", {}))

        merged = best_item.copy()
        merged["metadata"] = all_metadata
        merged["correlation_count"] = len(items)
        merged["sources"] = list(set(item["source"] for item in items))

        return merged

    def apply_priority_weighting(self, intelligence: List[Dict]) -> List[Dict]:
        """Apply priority weighting to intelligence items"""

        weights = self.config["synthesis"]["priority_weighting"]

        for item in intelligence:
            base_priority = item["priority"]
            weight = weights.get(base_priority, 0.5)

            # Adjust confidence based on source reliability
            source_reliability = self.config["synthesis"] [
                "source_reliability"].get(
                item["source"],
                0.5)
            item["weighted_confidence"] = item["confidence"] * \
                weight * source_reliability

        # Sort by weighted confidence
        intelligence.sort(key=lambda x: x["weighted_confidence"], reverse=True)

        return intelligence

    def generate_insights(self, intelligence: List[Dict]) -> List[Dict]:
        """Generate strategic insights from intelligence"""

        insights = []

        # Group by themes
        themes = self.identify_themes(intelligence)

        for theme, items in themes.items():
            if len(items) >= 2:  # Require at least 2 related items for insight
                insight = self.create_theme_insight(theme, items)
                if insight:
                    insights.append(insight)

        # Sort by significance
        insights.sort(key=lambda x: x.get(
            "significance_score", 0), reverse=True)

        return insights

    def identify_themes(self, intelligence: List[Dict]) -> Dict[str, List]:
        """Identify thematic groupings in intelligence"""

        themes = defaultdict(list)

        for item in intelligence:
            # Extract theme keywords
            content = item["content"].lower()
            theme_keywords = []

            # Technology themes
            if any(
                word in content
                for word
                in ["ai", "artificial", "machine", "tech", "innovation"]):
                theme_keywords.append("technology")

            # Economic themes
            if any(
                word in content
                for word
                in ["economy", "market", "finance", "trading", "investment"]):
                theme_keywords.append("economy")

            # Social themes
            if any(
                word in content
                for word in ["social", "community", "people", "society"]):
                theme_keywords.append("social")

            # Risk themes
            if any(
                word in content
                for word in ["risk", "threat", "warning", "error", "failure"]):
                theme_keywords.append("risk")

            # Default theme
            if not theme_keywords:
                theme_keywords.append("general")

            # Add to themes
            for keyword in theme_keywords:
                themes[keyword].append(item)

        return themes

    def create_theme_insight(
            self, theme: str, items: List[Dict]) ->Optional[Dict]:
        """Create an insight from a thematic grouping"""

        # Calculate theme significance
        avg_confidence = sum(item["weighted_confidence"]
                             for item in items) / len(items)
        priority_scores = {"low": 1, "medium": 2, "high": 3, "critical": 4}
        avg_priority = sum(priority_scores.get(
            item["priority"], 1) for item in items) / len(items)

        significance_score = (avg_confidence * 0.6) + (avg_priority * 0.4)

        if significance_score < 0.5:
            return None  # Not significant enough

        # Generate insight summary
        sources = list(set(item["source"] for item in items))
        priorities = list(set(item["priority"] for item in items))

        insight = {
            "theme": theme,
            "significance_score": significance_score,
            "item_count": len(items),
            "sources": sources,
            "priorities": priorities,
            "summary": f"Detected {len(items)} intelligence items related to {theme} from {len(sources)} sources",
            # Top 3 points
            "key_points": [item["content"][:100] + "..." for item in items[:3]],
            "recommended_action": self.generate_theme_action(theme, significance_score),
            "timestamp": datetime.now().isoformat()
        }

        return insight

    def generate_theme_action(self, theme: str, significance: float) -> str:
        """Generate recommended action for a theme"""

        if significance > 0.8:
            if theme == "risk":
                return "Immediate attention required - escalate to command"
            elif theme == "technology":
                return "High-priority intelligence gathering - allocate resources"
            elif theme == "economy":
                return "Strategic analysis required - coordinate with Council 52"
            else:
                return "Critical insight - command review recommended"
        elif significance > 0.6:
            return "Monitor closely - potential strategic importance"
        else:
            return "Track for trends - background monitoring sufficient"

    def analyze_priority_distribution(self, intelligence: List[Dict]) -> Dict:
        """Analyze the distribution of priorities in intelligence"""

        distribution = defaultdict(int)
        for item in intelligence:
            distribution[item["priority"]] += 1

        return dict(distribution)

    def calculate_confidence_metrics(self, intelligence: List[Dict]) -> Dict:
        """Calculate confidence metrics for the intelligence set"""

        if not intelligence:
            return {"average": 0, "high_confidence_ratio": 0}

        confidences = [item["weighted_confidence"] for item in intelligence]
        avg_confidence = sum(confidences) / len(confidences)
        high_confidence_count = sum(1 for c in confidences if c > 0.8)

        return {
            "average": avg_confidence,
            "high_confidence_ratio": high_confidence_count / len(confidences),
            "total_items": len(intelligence)
        }

    def generate_recommendations(self, insights: List[Dict]) -> List[str]:
        """Generate strategic recommendations based on insights"""

        recommendations = []

        if not insights:
            recommendations.append(
                "Continue standard intelligence gathering operations")
            return recommendations

        # Analyze top insights
        top_insights = insights[:3]

        for insight in top_insights:
            if insight["significance_score"] > 0.8:
                if insight["theme"] == "risk":
                    recommendations.append(
                        "Implement immediate risk mitigation protocols")
                elif insight["theme"] == "technology":
                    recommendations.append(
                        "Increase technology intelligence monitoring")
                elif insight["theme"] == "economy":
                    recommendations.append(
                        "Enhance economic trend analysis capabilities")

        if len(insights) > 5:
            recommendations.append(
                "High volume of intelligence - consider resource allocation increase")

        return recommendations if recommendations else ["Maintain current operational posture"]

# Global intelligence synthesizer instance
intelligence_synthesizer = NCCIntelligenceSynthesizer()

def synthesize_intelligence(sources: List[Dict]) -> Dict:
    """Convenience function for intelligence synthesis"""
    return intelligence_synthesizer.synthesize_intelligence(sources)

if __name__ == "__main__":
    # Test Intelligence Synthesizer
    print("🧠 NCC Intelligence Synthesizer Test")
    print("=" * 45)

    # Create test intelligence sources
    test_sources = [
        {
            "type": "council_52",
            "data": {
                "directives": [
                    {
                        "summary": "AI technology breakthrough detected",
                        "priority_level": "high",
                        "confidence_score": 0.9,
                        "source_channel": "Tom Bilyeu",
                        "created_at": datetime.now().isoformat()
                    }
                ]
            }
        },
        {
            "type": "api_monitoring",
            "data": {
                "api_calls": [
                    {
                        "endpoint": "/youtube/channels",
                        "success": False,
                        "error_details": "Rate limit exceeded",
                        "timestamp": datetime.now().isoformat()
                    }
                ]
            }
        }
    ]

    # Synthesize intelligence
    synthesis = synthesize_intelligence(test_sources)

    print(f"Synthesis ID: {synthesis['id']}")
    print(f"Intelligence items processed: {synthesis['intelligence_items']}")
    print(f"Insights generated: {synthesis['insights_generated']}")
    print(f"Confidence metrics: {synthesis['confidence_metrics']}")

    if synthesis['top_insights']:
        print(f"\nTop Insight: {synthesis['top_insights'][0]['summary']}")

    print("\n✅ NCC Intelligence Synthesizer Ready!")
    print("   • Multi-source intelligence processing: Active")
    print("   • Thematic analysis: Operational")
    print("   • Insight generation: Functional")
    print("   • Strategic recommendations: Enabled")