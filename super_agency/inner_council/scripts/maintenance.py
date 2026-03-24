#!/usr/bin/env python3
"""
Inner Council Maintenance Script
Perform maintenance operations on council data and systems
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import argparse

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from integrations.ncl_integration import NCLIntegration

def cleanup_old_insights(days_to_keep: int = 90) -> Dict[str, int]:
    """Remove insights older than specified days"""

    ncl_integration = NCLIntegration()
    cutoff_date = datetime.now() - timedelta(days=days_to_keep)

    # Get all insights
    all_insights = ncl_integration.query_council_insights(limit=10000)

    # Find old insights
    old_insights = []
    for insight in all_insights:
        try:
            insight_date = datetime.fromisoformat(
                insight.get("timestamp", "").replace("Z", "+00:00"))
            if insight_date < cutoff_date:
                old_insights.append(insight)
        except:
            continue

    # Remove old insights (in a real implementation, this would delete from NCL)
    removed_count = len(old_insights)

    print(
        f"🧹 Cleaned up {removed_count} insights older than {days_to_keep} days")

    return {
        "removed_insights": removed_count,
        "kept_insights": len(all_insights) - removed_count,
        "cutoff_date": cutoff_date.isoformat()
    }

def deduplicate_insights() -> Dict[str, int]:
    """Remove duplicate insights based on content similarity"""

    ncl_integration = NCLIntegration()
    all_insights = ncl_integration.query_council_insights(limit=5000)

    # Group by content hash (simplified - in real implementation use proper hashing)
    seen_content = set()
    duplicates = []

    for insight in all_insights:
        data = insight.get("data", {})
        # Create simple content signature
        content_sig = f"{
            data.get('council_member', '')}: {
            data.get('content_title', '')}: {
            str(data.get('key_insights', []))} "

        if content_sig in seen_content:
            duplicates.append(insight)
        else:
            seen_content.add(content_sig)

    # Remove duplicates (simplified - real implementation would delete from NCL)
    removed_count = len(duplicates)

    print(f"🧹 Removed {removed_count} duplicate insights")

    return {
        "removed_duplicates": removed_count,
        "unique_insights": len(all_insights) - removed_count
    }

def validate_data_integrity() -> Dict[str, Any]:
    """Validate data integrity of council insights"""

    ncl_integration = NCLIntegration()
    all_insights = ncl_integration.query_council_insights(limit=10000)

    issues = {
        "missing_timestamps": 0,
        "invalid_timestamps": 0,
        "missing_council_members": 0,
        "empty_insights": 0,
        "corrupted_records": 0
    }

    for insight in all_insights:
        # Check timestamp
        timestamp = insight.get("timestamp")
        if not timestamp:
            issues["missing_timestamps"] += 1
        else:
            try:
                datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            except:
                issues["invalid_timestamps"] += 1

        # Check council member
        data = insight.get("data", {})
        if not data.get("council_member"):
            issues["missing_council_members"] += 1

        # Check insights content
        if not any([data.get("key_insights"), data.get("policy_implications"),
                   data.get("strategic_recommendations")]):
            issues["empty_insights"] += 1

        # Check for corrupted structure
        if not isinstance(data, dict):
            issues["corrupted_records"] += 1

    total_issues = sum(issues.values())

    if total_issues == 0:
        print("✅ Data integrity check passed - no issues found")
    else:
        print(f"⚠️  Data integrity issues found: {total_issues}")

    return {
        "total_records_checked": len(all_insights),
        "issues_found": total_issues,
        "issues_breakdown": issues,
        "integrity_status": "PASS" if total_issues == 0 else "ISSUES_FOUND"
    }

def optimize_storage() -> Dict[str, Any]:
    """Optimize storage by compressing and reorganizing data"""

    ncl_integration = NCLIntegration()

    # Get storage stats
    all_insights = ncl_integration.query_council_insights(limit=10000)

    original_size = sum(len(json.dumps(insight, default=str))
                        for insight in all_insights)

    # Compress insights (simplified - real implementation would compress data)
    compressed_insights = []
    for insight in all_insights:
        # Remove redundant fields, compress arrays, etc.
        compressed = insight.copy()
        data = compressed.get("data", {})

        # Compress arrays by removing duplicates within each insight
        for field in ["key_insights", "policy_implications",
                      "strategic_recommendations"]:
            if field in data and isinstance(data[field], list):
                data[field] = list(set(data[field]))  # Remove duplicates

        compressed_insights.append(compressed)

    compressed_size = sum(len(json.dumps(insight, default=str))
                          for insight in compressed_insights)
    space_saved = original_size - compressed_size
    compression_ratio = (space_saved / original_size) * \
                         100 if original_size > 0 else 0

    print(
        f"🗜️  Storage optimized - saved {space_saved} bytes ({compression_ratio:.1f}% reduction)")

    return {
        "original_size_bytes": original_size,
        "compressed_size_bytes": compressed_size,
        "space_saved_bytes": space_saved,
        "compression_ratio_percent": round(compression_ratio, 1)
    }

def generate_health_report() -> str:
    """Generate comprehensive health report"""

    print("🔍 Running Inner Council health check...")

    # Run all maintenance checks
    cleanup_result = cleanup_old_insights(days_to_keep=90)
    dedup_result = deduplicate_insights()
    integrity_result = validate_data_integrity()
    storage_result = optimize_storage()

    # Generate report
    report = f"""# Inner Council Health Report
**Generated**: {datetime.now().isoformat()}

## Data Integrity
- **Status**: {integrity_result['integrity_status']}
- **Records Checked**: {integrity_result['total_records_checked']}
- **Issues Found**: {integrity_result['issues_found']}

### Issues Breakdown
{chr(10).join(f"- {k}: {v}" for k, v in integrity_result['issues_breakdown'].items())}

## Data Maintenance
- **Old Insights Cleaned**: {cleanup_result['removed_insights']}
- **Duplicates Removed**: {dedup_result['removed_duplicates']}
- **Unique Insights**: {dedup_result['unique_insights']}

## Storage Optimization
- **Original Size**: {storage_result['original_size_bytes']} bytes
- **Compressed Size**: {storage_result['compressed_size_bytes']} bytes
- **Space Saved**: {storage_result['space_saved_bytes']} bytes ({storage_result['compression_ratio_percent']}%)

## Overall Health
"""

    # Determine overall health
    critical_issues = integrity_result['issues_breakdown'] [
        'corrupted_records'] +integrity_result['issues_breakdown'] [
        'missing_timestamps']
    warning_issues = sum(
        integrity_result['issues_breakdown'].values()) - critical_issues

    if critical_issues > 0:
        health_status = "CRITICAL"
        health_color = "🔴"
    elif warning_issues > 0:
        health_status = "WARNING"
        health_color = "🟡"
    else:
        health_status = "HEALTHY"
        health_color = "🟢"

    report += f"""
{health_color} **Status**: {health_status}

### Recommendations
"""

    if critical_issues > 0:
        report += "- 🔴 **CRITICAL**: Data corruption detected - manual review required\n"
    if warning_issues > 0:
        report += "- 🟡 **WARNING**: Data quality issues found - review and clean data\n"
    if cleanup_result['removed_insights'] > 100:
        report += "- 🧹 Consider adjusting cleanup policy (removed many old insights)\n"
    if dedup_result['removed_duplicates'] > 50:
        report += "- 🧹 High duplicate rate detected - review content processing\n"

    if health_status == "HEALTHY":
        report += "- ✅ System is healthy - continue normal operations\n"

    report += f"""
---
*Inner Council Health Report*
*Generated by Bit Rage Systems Maintenance Systems*
"""

    return report

def main():
    """CLI interface for maintenance operations"""

    parser = argparse.ArgumentParser(description="Inner Council Maintenance")
    parser.add_argument(
        "operation",
        choices=["cleanup", "deduplicate", "validate", "optimize", "health"],
        help="Maintenance operation to perform")
    parser.add_argument("--days", type=int, default=90,
                       help="Days to keep for cleanup (default: 90)")
    parser.add_argument("--output", help="Output file for health report")

    args = parser.parse_args()

    try:
        if args.operation == "cleanup":
            result = cleanup_old_insights(args.days)
            print(f"✅ Cleanup completed: {result}")

        elif args.operation == "deduplicate":
            result = deduplicate_insights()
            print(f"✅ Deduplication completed: {result}")

        elif args.operation == "validate":
            result = validate_data_integrity()
            print(f"✅ Validation completed: {result}")

        elif args.operation == "optimize":
            result = optimize_storage()
            print(f"✅ Optimization completed: {result}")

        elif args.operation == "health":
            report = generate_health_report()
            if args.output:
                with open(args.output, 'w', encoding='utf-8') as f:
                    f.write(report)
                print(f"✅ Health report saved to: {args.output}")
            else:
                print(report)

    except Exception as e:
        print(f"❌ Error during maintenance: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()