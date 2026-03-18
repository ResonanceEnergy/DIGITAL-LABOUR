#!/usr/bin/env python3
"""
Inner Council Intelligence Monitor - BIT RAGE LABOUR
Monitors the Inner Council of YouTube channels for daily policy adjustments,
steering, planning, and execution intelligence gathering.
"""

import json
import os
import time
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging
from dataclasses import dataclass
from urllib.parse import urlencode

# Import oversight framework
from oversight_framework import audit_api_call, audit_intelligence_operation

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('inner_council_intelligence.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class CouncilMember:
    """Represents an Inner Council member with their intelligence role"""
    channel_key: str
    channel_id: str
    channel_name: str
    description: str
    priority: str
    role: str
    intelligence_score: float = 0.0
    last_activity: Optional[datetime] = None
    policy_influence: float = 0.0

@dataclass
class IntelligenceDirective:
    """Represents a policy directive or strategic adjustment"""
    directive_id: str
    source_channel: str
    source_role: str
    content_type: str
    title: str
    summary: str
    implications: List[str]
    recommended_actions: List[str]
    priority_level: str
    execution_timeline: str
    created_at: datetime
    confidence_score: float

class InnerCouncilIntelligence:
    """Inner Council intelligence gathering and policy formulation system"""

    def __init__(self, config_path: str = "inner_council_config.json"):
        self.config = self.load_config(config_path)
        self.api_key = self.get_youtube_api_key()
        self.council_members = self.initialize_council()
        self.intelligence_directives = []
        self.daily_policy_adjustments = []
        self.session_start = datetime.now()

        # Create data directory
        os.makedirs("inner_council_intelligence", exist_ok=True)
        os.makedirs("daily_policy_directives", exist_ok=True)

    def load_config(self, config_path: str) -> Dict:
        """Load Inner Council configuration"""
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"Configuration file not found: {config_path}")
            raise

    def get_youtube_api_key(self) -> str:
        """Get YouTube API key from environment or config"""
        api_key = os.getenv('YOUTUBE_API_KEY')
        if not api_key:
            api_key = self.config.get('youtube_api_key')
        if not api_key:
            logger.warning("No YouTube API key found. Set YOUTUBE_API_KEY environment variable or add to config.")
            return None
        return api_key

    def initialize_council(self) -> Dict[str, CouncilMember]:
        """Initialize the Inner Council members"""
        council = {}
        for channel_key, channel_data in self.config['youtube_channels']['inner_council'].items():
            council[channel_key] = CouncilMember(
                channel_key=channel_key,
                channel_id=channel_data['channel_id'],
                channel_name=channel_data['channel_name'],
                description=channel_data['description'],
                priority=channel_data['priority'],
                role=channel_data['role']
            )
        return council

    def get_channel_videos(self, channel_id: str, max_results: int = 50) -> List[Dict]:
        """Get recent videos from a council member's channel"""
        if not self.api_key:
            logger.warning("No API key available, skipping YouTube API calls")
            return []

        try:
            start_time = time.time()

            # Get uploads playlist ID
            channel_url = "https://www.googleapis.com/youtube/v3/channels"
            channel_params = {
                'part': 'contentDetails',
                'id': channel_id,
                'key': self.api_key
            }

            response = requests.get(channel_url, params=channel_params)
            response_time = time.time() - start_time

            # Audit API call
            audit_api_call(
                api_name="youtube",
                endpoint="/channels",
                response_time=response_time,
                success=response.status_code == 200,
                error_details=None if response.status_code == 200 else f"HTTP {response.status_code}"
            )

            response.raise_for_status()
            channel_data = response.json()

            if not channel_data['items']:
                logger.warning(f"No channel found for ID: {channel_id}")
                return []

            uploads_playlist_id = channel_data['items'][0]['contentDetails']['relatedPlaylists']['uploads']

            # Get videos from uploads playlist
            playlist_url = "https://www.googleapis.com/youtube/v3/playlistItems"
            playlist_params = {
                'part': 'snippet,contentDetails,status',
                'playlistId': uploads_playlist_id,
                'maxResults': max_results,
                'key': self.api_key
            }

            start_time = time.time()
            response = requests.get(playlist_url, params=playlist_params)
            response_time = time.time() - start_time

            # Audit API call
            audit_api_call(
                api_name="youtube",
                endpoint="/playlistItems",
                response_time=response_time,
                success=response.status_code == 200,
                error_details=None if response.status_code == 200 else f"HTTP {response.status_code}"
            )

            response.raise_for_status()
            return response.json()['items']

        except requests.RequestException as e:
            logger.error(f"Error fetching videos for channel {channel_id}: {e}")
            return []

    def get_video_statistics(self, video_ids: List[str]) -> Dict[str, Dict]:
        """Get detailed statistics for videos"""
        if not self.api_key or not video_ids:
            return {}

        try:
            chunks = [video_ids[i:i+50] for i in range(0, len(video_ids), 50)]
            all_stats = {}

            for chunk in chunks:
                stats_url = "https://www.googleapis.com/youtube/v3/videos"
                stats_params = {
                    'part': 'statistics,contentDetails',
                    'id': ','.join(chunk),
                    'key': self.api_key
                }

                start_time = time.time()
                response = requests.get(stats_url, params=stats_params)
                response_time = time.time() - start_time

                # Audit API call
                audit_api_call(
                    api_name="youtube",
                    endpoint="/videos",
                    response_time=response_time,
                    success=response.status_code == 200,
                    error_details=None if response.status_code == 200 else f"HTTP {response.status_code}"
                )

                response.raise_for_status()
                data = response.json()

                for item in data['items']:
                    all_stats[item['id']] = {
                        'view_count': int(item['statistics'].get('viewCount', 0)),
                        'like_count': int(item['statistics'].get('likeCount', 0)),
                        'comment_count': int(item['statistics'].get('commentCount', 0)),
                        'duration': item['contentDetails']['duration']
                    }

            return all_stats

        except requests.RequestException as e:
            logger.error(f"Error fetching video statistics: {e}")
            return {}

    def analyze_council_content(self, channel_key: str, videos: List[Dict]) -> List[IntelligenceDirective]:
        """Analyze content from a council member for intelligence directives"""
        council_member = self.council_members[channel_key]
        directives = []

        for video_data in videos:
            try:
                directive = self.extract_intelligence_directive(video_data, council_member)
                if directive:
                    directives.append(directive)
                    council_member.intelligence_score += directive.confidence_score
                    council_member.last_activity = directive.created_at

            except Exception as e:
                logger.error(f"Error analyzing video for {channel_key}: {e}")
                continue

        return directives

    def extract_intelligence_directive(self, video_data: Dict, council_member: CouncilMember) -> Optional[IntelligenceDirective]:
        """Extract intelligence directive from video content"""
        snippet = video_data['snippet']
        content_details = video_data['contentDetails']

        # Get video statistics
        stats = self.get_video_statistics([content_details['videoId']])
        video_stats = stats.get(content_details['videoId'], {})

        title = snippet['title']
        description = snippet.get('description', '')
        published_at = datetime.fromisoformat(snippet['publishedAt'].replace('Z', '+00:00'))

        # Check if content is recent (last 7 days for daily policy adjustments)
        if published_at < (datetime.now() - timedelta(days=7)):
            return None

        # Analyze content for policy implications
        implications = self.analyze_policy_implications(title, description, council_member.role)
        if not implications:
            return None

        # Determine priority level
        priority_level = self.determine_priority_level(title, description, video_stats, council_member.priority)

        # Generate recommended actions
        recommended_actions = self.generate_recommended_actions(implications, council_member.role)

        # Calculate confidence score
        confidence_score = self.calculate_confidence_score(video_stats, implications, council_member.priority)

        directive = IntelligenceDirective(
            directive_id=f"{council_member.channel_key}_{content_details['videoId']}",
            source_channel=council_member.channel_name,
            source_role=council_member.role,
            content_type="video",
            title=title,
            summary=description[:500] + "..." if len(description) > 500 else description,
            implications=implications,
            recommended_actions=recommended_actions,
            priority_level=priority_level,
            execution_timeline=self.determine_execution_timeline(priority_level),
            created_at=published_at,
            confidence_score=confidence_score
        )

        # Audit intelligence operation
        audit_intelligence_operation(
            operation_type="intelligence_extraction",
            source=council_member.channel_name,
            data_quality_score=confidence_score,
            ethical_compliance=True  # Council 52 doctrine compliance
        )

        return directive

    def analyze_policy_implications(self, title: str, description: str, role: str) -> List[str]:
        """Analyze content for policy implications based on council role"""
        implications = []
        content = (title + " " + description).lower()

        # Role-specific analysis
        if role == "intelligence_coordinator":
            if any(word in content for word in ["strategy", "planning", "coordination", "intelligence"]):
                implications.append("Strategic coordination adjustments needed")
        elif role == "business_strategy":
            if any(word in content for word in ["business", "strategy", "growth", "scaling", "acquisition"]):
                implications.append("Business strategy optimization required")
        elif role == "ai_technology":
            if any(word in content for word in ["ai", "artificial intelligence", "machine learning", "technology"]):
                implications.append("AI technology policy updates needed")
        elif role == "financial_intelligence":
            if any(word in content for word in ["market", "finance", "economy", "investment", "trading"]):
                implications.append("Financial market adjustments required")
        elif role == "geopolitical_analyst":
            if any(word in content for word in ["geopolitics", "international", "policy", "relations", "strategy"]):
                implications.append("Geopolitical strategy updates needed")
        elif role == "operations_expert":
            if any(word in content for word in ["operations", "efficiency", "process", "optimization"]):
                implications.append("Operational process improvements needed")

        # General policy implications
        critical_keywords = self.config['monitoring_config']['alert_triggers']['critical_keywords']
        if any(keyword in content for keyword in critical_keywords):
            implications.append("Critical policy review required")

        return implications

    def determine_priority_level(self, title: str, description: str, stats: Dict, member_priority: str) -> str:
        """Determine priority level of intelligence directive"""
        content = (title + " " + description).lower()
        view_count = stats.get('view_count', 0)

        # Critical priority triggers
        if member_priority == "critical" or view_count > 500000:
            return "critical"
        elif any(word in content for word in ["urgent", "emergency", "crisis", "immediate"]):
            return "high"
        elif view_count > 100000 or member_priority == "high":
            return "medium"
        elif member_priority == "secondary":
            return "secondary"
        else:
            return "low"

    def generate_recommended_actions(self, implications: List[str], role: str) -> List[str]:
        """Generate recommended actions based on implications and role"""
        actions = []

        for implication in implications:
            if "strategy" in implication.lower():
                actions.extend([
                    "Review current strategic plans",
                    "Update policy frameworks",
                    "Conduct stakeholder analysis"
                ])
            elif "business" in implication.lower():
                actions.extend([
                    "Analyze market positioning",
                    "Review business development plans",
                    "Update operational procedures"
                ])
            elif "financial" in implication.lower():
                actions.extend([
                    "Monitor market indicators",
                    "Review investment strategies",
                    "Update risk management protocols"
                ])
            elif "technology" in implication.lower():
                actions.extend([
                    "Evaluate technology adoption",
                    "Review innovation pipeline",
                    "Update technical standards"
                ])

        return list(set(actions))  # Remove duplicates

    def determine_execution_timeline(self, priority_level: str) -> str:
        """Determine execution timeline based on priority"""
        timelines = {
            "critical": "Immediate (within 24 hours)",
            "high": "Short-term (within 3-7 days)",
            "medium": "Medium-term (within 2-4 weeks)",
            "secondary": "Background monitoring (monthly review)",
            "low": "Long-term (strategic planning)"
        }
        return timelines.get(priority_level, "Review as needed")

    def calculate_confidence_score(self, stats: Dict, implications: List[str], member_priority: str) -> float:
        """Calculate confidence score for intelligence directive"""
        base_score = 0.5

        # Statistics factor
        view_count = stats.get('view_count', 0)
        if view_count > 100000:
            base_score += 0.2
        elif view_count > 50000:
            base_score += 0.1

        # Implications factor
        base_score += min(len(implications) * 0.1, 0.3)

        # Priority factor
        if member_priority == "critical":
            base_score += 0.2
        elif member_priority == "high":
            base_score += 0.1

        return min(base_score, 1.0)

    def conduct_council_session(self) -> Dict[str, List[IntelligenceDirective]]:
        """Conduct a full Inner Council intelligence gathering session"""
        logger.info("Conducting Inner Council intelligence session...")

        all_directives = {}

        for channel_key, council_member in self.council_members.items():
            logger.info(f"Gathering intelligence from {council_member.channel_name} ({council_member.role})")

            # Get recent videos
            videos_data = self.get_channel_videos(
                council_member.channel_id,
                self.config['monitoring_config']['max_videos_per_channel']
            )

            if not videos_data:
                logger.warning(f"No videos found for council member: {channel_key}")
                continue

            # Analyze content for intelligence directives
            directives = self.analyze_council_content(channel_key, videos_data)
            all_directives[channel_key] = directives

            # Brief pause to respect API limits
            time.sleep(0.1)

        logger.info(f"Intelligence session completed. Generated {sum(len(d) for d in all_directives.values())} directives")
        return all_directives

    def formulate_daily_policy_adjustments(self, all_directives: Dict[str, List[IntelligenceDirective]]) -> List[Dict]:
        """Formulate daily policy adjustments based on council intelligence"""
        policy_adjustments = []

        # Group directives by priority
        critical_directives = []
        high_directives = []
        medium_directives = []

        for channel_directives in all_directives.values():
            for directive in channel_directives:
                if directive.priority_level == "critical":
                    critical_directives.append(directive)
                elif directive.priority_level == "high":
                    high_directives.append(directive)
                elif directive.priority_level == "medium":
                    medium_directives.append(directive)

        # Process critical directives first
        if critical_directives:
            policy_adjustments.append({
                "adjustment_type": "critical_policy_review",
                "directives": len(critical_directives),
                "focus_areas": list(set(d.source_role for d in critical_directives)),
                "recommended_actions": self.consolidate_actions(critical_directives),
                "execution_priority": "immediate",
                "rationale": "Critical intelligence from Inner Council requires immediate policy adjustments"
            })

        # Process high priority directives
        if high_directives:
            policy_adjustments.append({
                "adjustment_type": "strategic_adjustments",
                "directives": len(high_directives),
                "focus_areas": list(set(d.source_role for d in high_directives)),
                "recommended_actions": self.consolidate_actions(high_directives),
                "execution_priority": "high",
                "rationale": "High-priority intelligence indicates need for strategic policy adjustments"
            })

        # Process medium priority directives
        if medium_directives:
            policy_adjustments.append({
                "adjustment_type": "operational_optimizations",
                "directives": len(medium_directives),
                "focus_areas": list(set(d.source_role for d in medium_directives)),
                "recommended_actions": self.consolidate_actions(medium_directives),
                "execution_priority": "medium",
                "rationale": "Medium-priority intelligence suggests operational improvements"
            })

        return policy_adjustments

    def consolidate_actions(self, directives: List[IntelligenceDirective]) -> List[str]:
        """Consolidate recommended actions from multiple directives"""
        all_actions = []
        for directive in directives:
            all_actions.extend(directive.recommended_actions)

        # Remove duplicates and prioritize
        unique_actions = list(set(all_actions))
        return unique_actions[:10]  # Limit to top 10 actions

    def generate_council_report(self, all_directives: Dict[str, List[IntelligenceDirective]],
                              policy_adjustments: List[Dict]) -> str:
        """Generate comprehensive Inner Council intelligence report"""
        report_time = datetime.now()

        report = f"""# Inner Council Intelligence Report
**Generated:** {report_time.strftime('%Y-%m-%d %H:%M:%S')}
**Session Start:** {self.session_start.strftime('%Y-%m-%d %H:%M:%S')}
**Council Members:** {len(self.council_members)}
**Total Intelligence Directives:** {sum(len(d) for d in all_directives.values())}

## Executive Summary

### Council Activity Overview
- **Active Council Members:** {len([m for m in self.council_members.values() if m.last_activity])}
- **Intelligence Directives Generated:** {sum(len(d) for d in all_directives.values())}
- **Policy Adjustments Recommended:** {len(policy_adjustments)}
- **Critical Priority Items:** {sum(1 for d in [item for sublist in all_directives.values() for item in sublist] if d.priority_level == 'critical')}

### Daily Policy Adjustments Summary
"""

        # Add policy adjustments summary
        for adjustment in policy_adjustments:
            report += f"""#### {adjustment['adjustment_type'].replace('_', ' ').title()}
- **Directives:** {adjustment['directives']}
- **Focus Areas:** {', '.join(adjustment['focus_areas'])}
- **Priority:** {adjustment['execution_priority'].upper()}
- **Rationale:** {adjustment['rationale']}

**Recommended Actions:**
"""
            for action in adjustment['recommended_actions'][:5]:  # Top 5 actions
                report += f"- {action}\n"
            report += "\n"

        # Add detailed council member analysis
        report += """## Council Member Intelligence Analysis

"""

        for channel_key, council_member in self.council_members.items():
            directives = all_directives.get(channel_key, [])
            if not directives:
                continue

            report += f"""### {council_member.channel_name}
**Role:** {council_member.role.replace('_', ' ').title()}
**Priority:** {council_member.priority.upper()}
**Intelligence Score:** {council_member.intelligence_score:.2f}
**Directives Generated:** {len(directives)}

#### Key Intelligence Directives:
"""

            # Sort directives by confidence score
            sorted_directives = sorted(directives, key=lambda x: x.confidence_score, reverse=True)

            for directive in sorted_directives[:3]:  # Top 3 directives per member
                report += f"""- **{directive.title}**
  - Priority: {directive.priority_level.upper()}
  - Confidence: {directive.confidence_score:.2f}
  - Timeline: {directive.execution_timeline}
  - Key Implications: {', '.join(directive.implications[:2])}

"""

        # Save detailed data
        self.save_council_intelligence(all_directives, policy_adjustments, report_time)

        return report

    def save_council_intelligence(self, all_directives: Dict[str, List[IntelligenceDirective]],
                                policy_adjustments: List[Dict], timestamp: datetime):
        """Save comprehensive council intelligence data"""
        # Save directives
        directives_filename = f"inner_council_intelligence/directives_{timestamp.strftime('%Y%m%d_%H%M%S')}.json"
        serializable_directives = {}

        for channel_key, directives in all_directives.items():
            serializable_directives[channel_key] = [
                {
                    'directive_id': d.directive_id,
                    'source_channel': d.source_channel,
                    'source_role': d.source_role,
                    'title': d.title,
                    'summary': d.summary,
                    'implications': d.implications,
                    'recommended_actions': d.recommended_actions,
                    'priority_level': d.priority_level,
                    'execution_timeline': d.execution_timeline,
                    'created_at': d.created_at.isoformat(),
                    'confidence_score': d.confidence_score
                }
                for d in directives
            ]

        with open(directives_filename, 'w') as f:
            json.dump(serializable_directives, f, indent=2, default=str)

        # Save policy adjustments
        policy_filename = f"daily_policy_directives/adjustments_{timestamp.strftime('%Y%m%d_%H%M%S')}.json"
        with open(policy_filename, 'w') as f:
            json.dump(policy_adjustments, f, indent=2, default=str)

        logger.info(f"Council intelligence saved to: {directives_filename}")
        logger.info(f"Policy adjustments saved to: {policy_filename}")

    def run_daily_council_session(self):
        """Run a complete daily Inner Council intelligence session"""
        try:
            logger.info("Starting daily Inner Council intelligence session")

            # Conduct council intelligence gathering
            all_directives = self.conduct_council_session()

            # Formulate policy adjustments
            policy_adjustments = self.formulate_daily_policy_adjustments(all_directives)

            # Generate comprehensive report
            report = self.generate_council_report(all_directives, policy_adjustments)

            # Save report
            report_filename = f"inner_council_intelligence/daily_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            with open(report_filename, 'w') as f:
                f.write(report)

            logger.info(f"Daily council session completed. Report saved to: {report_filename}")

            return all_directives, policy_adjustments

        except Exception as e:
            logger.error(f"Error in daily council session: {e}")
            return {}, []

def main():
    """Main execution function"""
    council = InnerCouncilIntelligence()

    print("🎯 Inner Council Intelligence System - BIT RAGE LABOUR")
    print("=" * 60)
    print("Daily Policy Adjustments, Steering, Planning & Execution")
    print("Council 52 - Supreme Intelligence Council")
    print("=" * 60)

    if not council.api_key:
        print("⚠️  WARNING: No YouTube API key found!")
        print("   Set YOUTUBE_API_KEY environment variable or add to config")
        print("   Continuing with limited functionality...")
        print()

    # Run daily council session
    directives, adjustments = council.run_daily_council_session()

    if directives:
        print("✅ Inner Council session completed!")
        print(f"   Council members analyzed: {len(directives)}")
        print(f"   Intelligence directives: {sum(len(d) for d in directives.values())}")
        print(f"   Policy adjustments: {len(adjustments)}")
        print()
        print("📋 Key Policy Adjustments:")
        for adjustment in adjustments[:3]:  # Show top 3
            print(f"   • {adjustment['adjustment_type'].replace('_', ' ').title()}")
            print(f"     Priority: {adjustment['execution_priority'].upper()}")
            print(f"     Actions: {len(adjustment['recommended_actions'])}")
    else:
        print("❌ Council session failed or no intelligence gathered")

if __name__ == "__main__":
    main()