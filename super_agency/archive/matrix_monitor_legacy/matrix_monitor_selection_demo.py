#!/usr/bin/env python3
"""
Matrix Monitor Project Selection Demo
Demonstrates selecting top 3 projects from Matrix Monitor for operations centers
"""

import asyncio
import json
from datetime import datetime

from matrix_monitor_project_selector import project_selector, SelectionCriteria

async def demo_project_selection():
    """Demonstrate project selection from Matrix Monitor"""
    print("🎯 Matrix Monitor Project Selection Demo")
    print("=" * 60)

    # Step 1: Load repository data
    print("📊 Step 1: Loading repository data...")
    repos = await project_selector.load_repository_data()
    print(f"✅ Loaded {len(repos)} repositories from Matrix Monitor")

    # Step 2: Show top repositories by different criteria
    print("\n📈 Step 2: Analyzing repositories by different criteria...")

    criteria_to_test = [
        ("priority", "Combined priority score"),
        ("size", "Repository size"),
        ("stars", "GitHub stars"),
        ("activity", "Recent activity")
    ]

    for criteria_name, description in criteria_to_test:
        print(f"\n🏆 Top 5 by {description}:")
        criteria_enum = SelectionCriteria(criteria_name)
        selected = await project_selector.select_top_projects(5, criteria_enum)

        for i, repo in enumerate(selected[:5], 1):
            if criteria_name == "size":
                metric = f"{repo.size_mb:.1f}MB"
            elif criteria_name == "stars":
                metric = f"{repo.stars} ⭐"
            elif criteria_name == "activity":
                metric = f"{repo.activity_score:.1f} activity"
            else:
                metric = f"{repo.priority_score:.2f} priority"

            print(f"  {i}. {repo.full_name} ({metric})")

    # Step 3: Select top 3 for operations centers
    print("\n🎯 Step 3: Selecting top 3 projects for operations centers...")
    selected_projects = await project_selector.select_top_projects(3, SelectionCriteria.PRIORITY)

    print("✅ Selected projects for operations centers:")
    center_names = ["Core Agency", "Enterprise Systems", "Neural Control"]

    for i, (center_name, repo) in enumerate(zip(center_names, selected_projects)):
        print(f"  🏢 {center_name}: {repo.full_name}")
        print(f"     Size: {repo.size_mb:.2f}MB, Stars: {repo.stars}, Priority: {repo.priority_score:.2f}")
        print(f"     Language: {repo.language or 'Unknown'}")
        print()

    # Step 3.5: Show progress indicators for all projects
    print("📊 Step 3.5: Project Progress Analysis - All Repositories Ranked")
    print("-" * 80)

    # Get all repositories sorted by priority score
    all_repos = sorted(project_selector.repositories, key=lambda r: r.priority_score, reverse=True)

    # Find the minimum and maximum priority scores for progress calculation
    if all_repos:
        max_score = all_repos[0].priority_score
        min_score = all_repos[-1].priority_score
        score_range = max_score - min_score if max_score != min_score else 1

        print("🏆 RANK | PROGRESS | REPOSITORY | SIZE | STARS | ACTIVITY | PRIORITY")
        print("-" * 80)

        for rank, repo in enumerate(all_repos, 1):
            # Calculate progress percentage (0-100)
            progress_pct = ((repo.priority_score - min_score) / score_range) * 100

            # Create progress bar (20 characters wide)
            filled_chars = int(progress_pct / 5)  # 5% per character
            progress_bar = "█" * filled_chars + "░" * (20 - filled_chars)

            # Status indicator
            if rank <= 3:
                status = "✅ SELECTED"
            elif progress_pct >= 80:
                status = "🔥 HOT"
            elif progress_pct >= 60:
                status = "⚡ READY"
            elif progress_pct >= 40:
                status = "👀 WATCH"
            else:
                status = "📋 BACKLOG"

            print(f"{rank:2d} | [{progress_bar}] {progress_pct:2.0f}% | {repo.full_name[:20]:20s} | {repo.size_mb:5.1f}MB | {repo.stars:4d}⭐ | {repo.activity_score:5.1f} | {repo.priority_score:.2f} | {status}")

            # Show additional details for top 10 or if requested
            if rank <= 10:
                desc = (repo.description or 'No description')[:50]
                print(f"        Language: {repo.language or 'Unknown':8s} | Forks: {repo.forks:3d} | Issues: {repo.open_issues:2d} | {desc}")
                print()

        # Summary statistics
        selected_count = sum(1 for r in all_repos if r.priority_score >= all_repos[2].priority_score)
        hot_count = sum(1 for r in all_repos if 80 <= ((r.priority_score - min_score) / score_range) * 100 < 100 and r not in all_repos[:3])
        ready_count = sum(1 for r in all_repos if 60 <= ((r.priority_score - min_score) / score_range) * 100 < 80)
        watch_count = sum(1 for r in all_repos if 40 <= ((r.priority_score - min_score) / score_range) * 100 < 60)
        backlog_count = len(all_repos) - selected_count - hot_count - ready_count - watch_count

        print("📈 Project Status Summary:")
        print(f"   ✅ SELECTED: {selected_count} projects (Top priority for operations centers)")
        print(f"   🔥 HOT: {hot_count} projects (High potential, monitor closely)")
        print(f"   ⚡ READY: {ready_count} projects (Good candidates for future selection)")
        print(f"   👀 WATCH: {watch_count} projects (Keep an eye on development)")
        print(f"   📋 BACKLOG: {backlog_count} projects (Lower priority, periodic review)")
        print()
    print("🔄 Step 4: Updating operations centers with selected projects...")
    update_result = await project_selector.update_operations_centers(selected_projects)

    if update_result.get("success"):
        print("✅ Operations centers updated successfully!")
        print(f"   Centers updated: {len(update_result.get('centers_updated', []))}")

        for center_update in update_result.get('centers_updated', []):
            print(f"   • {center_update['center_id']}: {center_update['old_repository']} → {center_update['new_repository']}")
    else:
        print("❌ Failed to update operations centers:")
        for error in update_result.get('errors', []):
            print(f"   • {error}")

    # Step 5: Get Matrix Monitor data
    print("\n📊 Step 5: Getting Matrix Monitor integration data...")
    monitor_data = await project_selector.get_matrix_monitor_data()

    print("✅ Matrix Monitor data generated:")
    print(f"   Total repositories: {monitor_data['project_selector']['total_repositories']}")
    print(f"   Selected projects: {monitor_data['project_selector']['selected_projects']}")

    # Step 6: Export selection report
    print("\n💾 Step 6: Exporting selection report...")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = f"matrix_monitor_selection_demo_{timestamp}.json"

    report = {
        "demo_timestamp": datetime.now().isoformat(),
        "selected_projects": [
            {
                "name": repo.name,
                "full_name": repo.full_name,
                "size_mb": repo.size_mb,
                "stars": repo.stars,
                "forks": repo.forks,
                "issues": repo.open_issues,
                "activity_score": repo.activity_score,
                "priority_score": repo.priority_score,
                "language": repo.language,
                "description": repo.description
            }
            for repo in selected_projects
        ],
        "operations_centers_update": update_result,
        "matrix_monitor_data": monitor_data
    }

    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False, default=str)

    print(f"✅ Demo report exported to: {report_path}")

    # Final summary
    print("\n🎉 Demo Complete!")
    print("=" * 60)
    print("✅ Repository data loaded from Matrix Monitor")
    print("✅ Top projects analyzed by multiple criteria")
    print("✅ Projects selected for operations centers")
    print("✅ Operations centers updated with new assignments")
    print("✅ Matrix Monitor integration data generated")
    print("✅ Selection report exported")
    print("\n🚀 The DIGITAL LABOUR can now dynamically select projects")
    print("   from Matrix Monitor data for optimal operations center assignment!")

if __name__ == "__main__":
    asyncio.run(demo_project_selection())
