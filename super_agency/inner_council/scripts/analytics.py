#!/usr/bin/env python3
"""
Inner Council Analytics Script
Advanced analytics and insights from council intelligence data
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
from collections import Counter, defaultdict
from typing import Dict, List, Any, Optional, Tuple
import argparse

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from integrations.ncl_integration import NCLIntegration

def analyze_council_activity(days_back: int = 30) -> Dict[str, Any]:
    """Analyze council member activity patterns"""

    ncl_integration = NCLIntegration()
    all_insights = ncl_integration.query_council_insights(limit=5000)

    # Filter by date
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)

    recent_insights = []
    for insight in all_insights:
        try:
            insight_date = datetime.fromisoformat(
                insight.get("timestamp", "").replace("Z", "+00:00"))
            if start_date <= insight_date <= end_date:
                recent_insights.append(insight)
        except:
            continue

    # Analyze by council member
    member_activity = Counter()
    member_types = Counter()
    daily_activity = defaultdict(int)

    for insight in recent_insights:
        data = insight.get("data", {})
        member = data.get("council_member", "Unknown")
        member_activity[member] += 1

        # Categorize member type
        if "lex" in member.lower() or "fridman" in member.lower():
            member_types["AI/Tech"] += 1
        elif "bilyeu" in member.lower() or "impact" in member.lower():
            member_types["Business"] += 1
        elif "huberman" in member.lower():
            member_types["Science"] += 1
        else:
            member_types["Other"] += 1

        # Daily activity
        try:
            date = datetime.fromisoformat(insight.get(
                "timestamp", "").replace("Z", "+00:00")).date()
            daily_activity[date] += 1
        except:
            continue

    return {
        "period_days": days_back,
        "total_insights": len(recent_insights),
        "member_activity": dict(member_activity.most_common(10)),
        "member_types": dict(member_types),
        "daily_activity": dict(sorted(daily_activity.items())),
        "avg_daily_insights": len(recent_insights) / days_back,
        "most_active_member": member_activity.most_common(1)[0][0] if member_activity else "None"
    }

def analyze_content_themes(days_back: int = 30) -> Dict[str, Any]:
    """Analyze themes and topics in council content"""

    ncl_integration = NCLIntegration()
    all_insights = ncl_integration.query_council_insights(limit=5000)

    # Filter by date
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)

    recent_insights = []
    for insight in all_insights:
        try:
            insight_date = datetime.fromisoformat(
                insight.get("timestamp", "").replace("Z", "+00:00"))
            if start_date <= insight_date <= end_date:
                recent_insights.append(insight)
        except:
            continue

    # Extract themes from insights
    all_themes = []
    theme_keywords = Counter()

    # Common theme keywords to look for
    theme_patterns = {
        "AI": ["ai", "artificial intelligence", "machine learning", "neural", "gpt", "llm"],
        "Technology": ["tech", "software", "hardware", "innovation", "blockchain", "crypto"],
        "Business": ["business", "startup", "entrepreneur", "finance", "economy", "market"],
        "Science": ["science", "research", "biology", "physics", "chemistry", "neuroscience"],
        "Society": ["society", "culture", "politics", "education", "health", "environment"],
        "Future": ["future", "prediction", "trend", "forecast", "emerging", "disruption"]
    }

    for insight in recent_insights:
        data = insight.get("data", {})

        # Extract from key insights
        for insight_text in data.get("key_insights", []):
            insight_lower = insight_text.lower()
            for theme, keywords in theme_patterns.items():
                if any(keyword in insight_lower for keyword in keywords):
                    all_themes.append(theme)
                    theme_keywords[theme] += 1

        # Extract from policy implications
        for policy_text in data.get("policy_implications", []):
            policy_lower = policy_text.lower()
            for theme, keywords in theme_patterns.items():
                if any(keyword in policy_lower for keyword in keywords):
                    all_themes.append(theme)
                    theme_keywords[theme] += 1

    return {
        "period_days": days_back,
        "total_insights_analyzed": len(recent_insights),
        "theme_distribution": dict(theme_keywords.most_common()),
        "dominant_themes": list(theme_keywords.most_common(3)),
        "total_theme_mentions": sum(theme_keywords.values()),
        "themes_per_insight": sum(theme_keywords.values()) / len(recent_insights) if recent_insights else 0
    }

def analyze_sentiment_trends(days_back: int = 30) -> Dict[str, Any]:
    """Analyze sentiment trends in council insights (simplified sentiment analysis)"""

    ncl_integration = NCLIntegration()
    all_insights = ncl_integration.query_council_insights(limit=5000)

    # Filter by date
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)

    recent_insights = []
    for insight in all_insights:
        try:
            insight_date = datetime.fromisoformat(
                insight.get("timestamp", "").replace("Z", "+00:00"))
            if start_date <= insight_date <= end_date:
                recent_insights.append(insight)
        except:
            continue

    # Simple sentiment analysis based on keywords
    positive_words = ["opportunity", "growth", "positive",
        "success", "breakthrough", "innovation", "advance"]
    negative_words = ["risk", "threat", "concern",
        "problem", "challenge", "crisis", "decline"]
    neutral_words = ["analysis", "review",
        "assessment", "consideration", "evaluation"]

    sentiment_counts = {"positive": 0, "negative": 0, "neutral": 0}
    daily_sentiment = defaultdict(
        lambda: {"positive": 0, "negative": 0, "neutral": 0})

    for insight in recent_insights:
        data = insight.get("data", {})
        content = " ".join(data.get("key_insights", []) + \
                           data.get("policy_implications", [])).lower()

        sentiment = "neutral"
        if any(word in content for word in positive_words):
            sentiment = "positive"
        elif any(word in content for word in negative_words):
            sentiment = "negative"

        sentiment_counts[sentiment] += 1

        # Daily sentiment
        try:
            date = datetime.fromisoformat(insight.get(
                "timestamp", "").replace("Z", "+00:00")).date()
            daily_sentiment[date][sentiment] += 1
        except:
            continue

    return {
        "period_days": days_back,
        "total_insights": len(recent_insights),
        "sentiment_distribution": sentiment_counts,
        "sentiment_percentages": {
            k: round((v / len(recent_insights)) * \
                     100, 1) if recent_insights else 0
            for k, v in sentiment_counts.items()
        },
        "daily_sentiment": dict(sorted(daily_sentiment.items())),
        "dominant_sentiment": max(sentiment_counts, key=sentiment_counts.get)
    }

def analyze_impact_assessment(days_back: int = 30) -> Dict[str, Any]:
    """Assess impact of council insights on operations"""

    ncl_integration = NCLIntegration()
    all_insights = ncl_integration.query_council_insights(limit=5000)

    # Filter by date
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)

    recent_insights = []
    for insight in all_insights:
        try:
            insight_date = datetime.fromisoformat(
                insight.get("timestamp", "").replace("Z", "+00:00"))
            if start_date <= insight_date <= end_date:
                recent_insights.append(insight)
        except:
            continue

    # Analyze impact indicators
    impact_metrics = {
        "policy_changes": 0,
        "strategic_actions": 0,
        "risk_mitigations": 0,
        "opportunity_identifications": 0,
        "decision_influences": 0
    }

    impact_keywords = {
        "policy_changes": ["policy", "guideline", "framework", "regulation", "standard"],
        "strategic_actions": ["strategic", "action", "initiative", "program", "campaign"],
        "risk_mitigations": ["risk", "mitigation", "prevention", "safeguard", "protection"],
        "opportunity_identifications": ["opportunity", "potential", "advantage", "breakthrough"],
        "decision_influences": ["decision", "choice", "recommendation", "advice", "guidance"]
    }

    for insight in recent_insights:
        data = insight.get("data", {})
        content = " ".join(
            data.get("key_insights", []) +
            data.get("policy_implications", []) +
            data.get("strategic_recommendations", [])
        ).lower()

        for impact_type, keywords in impact_keywords.items():
            if any(keyword in content for keyword in keywords):
                impact_metrics[impact_type] += 1

    return {
        "period_days": days_back,
        "total_insights": len(recent_insights),
        "impact_metrics": impact_metrics,
        "impact_rate": sum(impact_metrics.values()) / len(recent_insights) if recent_insights else 0,
        "most_common_impact": max(impact_metrics, key=impact_metrics.get),
        "impact_distribution": {k: round((v / sum(impact_metrics.values())) * 100, 1)
                               for k, v in impact_metrics.items() if sum(impact_metrics.values()) > 0}
    }

def generate_comprehensive_analytics_report(days_back: int = 30) -> str:
    """Generate comprehensive analytics report"""

    print("📊 Generating comprehensive analytics report...")

    activity_analysis = analyze_council_activity(days_back)
    theme_analysis = analyze_content_themes(days_back)
    sentiment_analysis = analyze_sentiment_trends(days_back)
    impact_analysis = analyze_impact_assessment(days_back)

    report = f"""# Inner Council Analytics Report
**Analysis Period**: Last {days_back} days
**Generated**: {datetime.now().isoformat()}

## Council Activity Analysis
- **Total Insights**: {activity_analysis['total_insights']}
- **Average Daily Insights**: {activity_analysis['avg_daily_insights']:.1f}
- **Most Active Member**: {activity_analysis['most_active_member']}

### Member Activity (Top 10)
{chr(10).join(f"- {member}: {count} insights" for member, count in activity_analysis['member_activity'].items())}

### Member Types Distribution
{chr(10).join(f"- {member_type}: {count} insights" for member_type, count in activity_analysis['member_types'].items())}

## Content Theme Analysis
- **Insights Analyzed**: {theme_analysis['total_insights_analyzed']}
- **Total Theme Mentions**: {theme_analysis['total_theme_mentions']}
- **Themes per Insight**: {theme_analysis['themes_per_insight']:.2f}

### Dominant Themes
{chr(10).join(f"- {theme}: {count} mentions" for theme, count in theme_analysis['theme_distribution'].items())}

## Sentiment Analysis
- **Dominant Sentiment**: {sentiment_analysis['dominant_sentiment'].title()}

### Sentiment Distribution
{chr(10).join(f"- {sentiment}: {count} ({sentiment_analysis['sentiment_percentages'][sentiment]}%)"
              for sentiment, count in sentiment_analysis['sentiment_distribution'].items())}

## Impact Assessment
- **Impact Rate**: {impact_analysis['impact_rate']:.2f} impacts per insight
- **Most Common Impact**: {impact_analysis['most_common_impact'].replace('_', ' ').title()}

### Impact Distribution
{chr(10).join(f"- {impact}: {count} ({impact_analysis['impact_distribution'].get(impact, 0)}%)"
              for impact, count in impact_analysis['impact_metrics'].items())}

## Key Insights
"""

    # Generate key insights
    insights = []

    if activity_analysis['avg_daily_insights'] > 5:
        insights.append("🔥 High activity level - council is highly engaged")
    elif activity_analysis['avg_daily_insights'] < 1:
        insights.append(
            "⚠️ Low activity level - consider increasing monitoring frequency")

    if theme_analysis['dominant_themes']:
        top_theme = theme_analysis['dominant_themes'][0][0]
        insights.append(
            f"🎯 Dominant theme: {top_theme} - focus area for strategic planning")

    if sentiment_analysis['dominant_sentiment'] == "positive":
        insights.append(
            "✅ Positive sentiment dominant - favorable environment")
    elif sentiment_analysis['dominant_sentiment'] == "negative":
        insights.append(
            "⚠️ Negative sentiment dominant - monitor risks closely")

    if impact_analysis['impact_rate'] > 0.5:
        insights.append(
            "💪 High impact rate - council insights driving significant changes")
    elif impact_analysis['impact_rate'] < 0.2:
        insights.append(
            "📉 Low impact rate - consider improving insight quality or implementation")

    report += chr(10).join(f"- {insight}" for insight in insights)

    report += f"""

---
*Inner Council Analytics Report*
*Generated by Bit Rage Systems Intelligence Systems*
"""

    return report

def main():
    """CLI interface for analytics operations"""

    parser = argparse.ArgumentParser(description="Inner Council Analytics")
    parser.add_argument(
        "analysis",
        choices=["activity", "themes", "sentiment", "impact", "comprehensive"],
        help="Type of analysis to perform")
    parser.add_argument("--days", type=int, default=30,
                       help="Days back to analyze (default: 30)")
    parser.add_argument("--output", help="Output file path")
    parser.add_argument("--format", choices=["text", "json"], default="text",
                       help="Output format")

    args = parser.parse_args()

    try:
        if args.analysis == "activity":
            result = analyze_council_activity(args.days)
        elif args.analysis == "themes":
            result = analyze_content_themes(args.days)
        elif args.analysis == "sentiment":
            result = analyze_sentiment_trends(args.days)
        elif args.analysis == "impact":
            result = analyze_impact_assessment(args.days)
        elif args.analysis == "comprehensive":
            report = generate_comprehensive_analytics_report(args.days)
            if args.output:
                with open(args.output, 'w', encoding='utf-8') as f:
                    f.write(report)
                print(f"✅ Analytics report saved to: {args.output}")
            else:
                print(report)
            return

        # Output results
        if args.format == "json":
            output = json.dumps(result, indent=2, default=str)
        else:
            output = f"Analysis Results ({
                args.analysis}):\n"+"\n".join(
                f"- {k}: {v} "for k, v in result.items())

        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(output)
            print(f"✅ Analysis saved to: {args.output}")
        else:
            print(output)

    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()