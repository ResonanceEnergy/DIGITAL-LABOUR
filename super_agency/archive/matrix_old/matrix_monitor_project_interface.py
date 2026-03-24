#!/usr/bin/env python3
"""
Matrix Monitor Project Selection Interface
Interactive interface for selecting top projects and updating operations centers
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Any

from matrix_monitor_project_selector import project_selector, SelectionCriteria

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ProjectSelectionInterface:
    """Interactive interface for project selection"""

    def __init__(self):
        self.selected_projects = []

    async def display_available_repositories(self, limit: int = 20):
        """Display available repositories for selection"""
        print("\n🔍 Available Repositories (Top {})".format(limit))
        print("=" * 80)

        if not project_selector.repositories:
            await project_selector.load_repository_data()

        # Sort by priority score for display
        project_selector.calculate_priority_scores()
        sorted_repos = sorted(project_selector.repositories,
                            key=lambda r: r.priority_score, reverse=True)[:limit]

        print("<10")
        print("-" * 80)

        for i, repo in enumerate(sorted_repos, 1):
            print("<10")

        print("\n📊 Selection Criteria Available:")
        print("  • priority  - Combined score (size, stars, activity, issues)")
        print("  • size      - Repository size in MB")
        print("  • stars     - GitHub stars")
        print("  • activity  - Recent activity score")
        print("  • forks     - Number of forks")

    async def select_projects_interactive(self):
        """Interactive project selection"""
        print("🎯 Matrix Monitor Project Selection")
        print("=" * 50)

        # Display available repositories
        await self.display_available_repositories()

        # Get user preferences
        print("\n🔧 Selection Configuration:")

        # Choose criteria
        criteria_options = {
            "1": ("priority", "Combined priority score"),
            "2": ("size", "Repository size"),
            "3": ("stars", "GitHub stars"),
            "4": ("activity", "Recent activity"),
            "5": ("forks", "Number of forks")
        }

        print("Available criteria:")
        for key, (criteria, desc) in criteria_options.items():
            print(f"  {key}. {criteria} - {desc}")

        while True:
            try:
                criteria_choice = input("\nSelect criteria (1-5): ").strip()
                if criteria_choice in criteria_options:
                    criteria_name, _ = criteria_options[criteria_choice]
                    break
                else:
                    print("Invalid choice. Please select 1-5.")
            except KeyboardInterrupt:
                print("\nOperation cancelled.")
                return

        # Choose count
        while True:
            try:
                count = int(input("Number of projects to select (1-10): ").strip())
                if 1 <= count <= 10:
                    break
                else:
                    print("Please enter a number between 1 and 10.")
            except ValueError:
                print("Please enter a valid number.")
            except KeyboardInterrupt:
                print("\nOperation cancelled.")
                return

        # Select projects
        print(f"\n🎯 Selecting top {count} projects by {criteria_name}...")

        criteria_enum = SelectionCriteria(criteria_name)
        selected = await project_selector.select_top_projects(count, criteria_enum)

        if not selected:
            print("❌ No projects selected.")
            return

        self.selected_projects = selected

        # Display selected projects
        print(f"\n✅ Selected {len(selected)} projects:")
        print("-" * 80)

        for i, repo in enumerate(selected, 1):
            print("<10")

        return selected

    async def update_operations_centers(self):
        """Update operations centers with selected projects"""
        if not self.selected_projects:
            print("❌ No projects selected. Please select projects first.")
            return

        if len(self.selected_projects) < 3:
            print(f"⚠️  Only {len(self.selected_projects)} projects selected. Need at least 3 for operations centers.")
            return

        print("\n🏢 Updating Operations Centers...")
        print("=" * 50)

        # Show current assignments
        print("Current center assignments:")
        current_centers = ["Super-Agency", "ResonanceEnergy_Enterprise", "NCL"]
        for i, repo in enumerate(current_centers):
            center_names = ["Core Agency", "Enterprise Systems", "Neural Control"]
            print(f"  {center_names[i]}: {repo}")

        # Show new assignments
        print("\nNew assignments:")
        center_names = ["Core Agency", "Enterprise Systems", "Neural Control"]
        for i, repo in enumerate(self.selected_projects[:3]):
            print(f"  {center_names[i]}: {repo.full_name}")

        # Confirm update
        while True:
            try:
                confirm = input("\nProceed with update? (y/N): ").strip().lower()
                if confirm in ['y', 'yes']:
                    break
                elif confirm in ['n', 'no', '']:
                    print("Update cancelled.")
                    return
                else:
                    print("Please enter 'y' or 'n'.")
            except KeyboardInterrupt:
                print("\nOperation cancelled.")
                return

        # Perform update
        print("\n🔄 Updating operations centers...")
        result = await project_selector.update_operations_centers(self.selected_projects)

        if result.get("success"):
            print("✅ Operations centers updated successfully!")
            print(f"   Centers updated: {len(result.get('centers_updated', []))}")

            for center_update in result.get('centers_updated', []):
                print(f"   • {center_update['center_id']}: {center_update['old_repository']} → {center_update['new_repository']}")
        else:
            print("❌ Failed to update operations centers:")
            for error in result.get('errors', []):
                print(f"   • {error}")

    async def show_current_status(self):
        """Show current project selection and operations centers status"""
        print("\n📊 Current Status")
        print("=" * 50)

        # Show selected projects
        if self.selected_projects:
            print(f"Selected Projects: {len(self.selected_projects)}")
            for i, repo in enumerate(self.selected_projects, 1):
                print(f"  {i}. {repo.full_name} ({repo.size_mb:.1f}MB)")
        else:
            print("Selected Projects: None")

        # Show operations centers status
        try:
            from operations_centers import operations_manager
            status = await operations_manager.get_operations_status()

            print(f"\nOperations Centers: {len(status['centers'])}")
            for center_id, center_data in status['centers'].items():
                print(f"  • {center_data['name']}: {center_data['repository']} ({center_data['agents']['total']} agents)")
        except Exception as e:
            print(f"Error getting operations centers status: {e}")

    async def run_interface(self):
        """Run the interactive interface"""
        print("🎯 Matrix Monitor Project Selection Interface")
        print("Select top projects from Matrix Monitor data for operations centers")
        print("=" * 70)

        while True:
            print("\n📋 Available Commands:")
            print("  1. Display available repositories")
            print("  2. Select projects interactively")
            print("  3. Update operations centers")
            print("  4. Show current status")
            print("  5. Export selection report")
            print("  0. Exit")

            try:
                choice = input("\nEnter command (0-5): ").strip()

                if choice == "0":
                    print("👋 Goodbye!")
                    break
                elif choice == "1":
                    await self.display_available_repositories()
                elif choice == "2":
                    await self.select_projects_interactive()
                elif choice == "3":
                    await self.update_operations_centers()
                elif choice == "4":
                    await self.show_current_status()
                elif choice == "5":
                    await self.export_selection_report()
                else:
                    print("❌ Invalid command. Please enter 0-5.")

            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")

    async def export_selection_report(self):
        """Export selection report"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_path = f"project_selection_report_{timestamp}.json"

            report = {
                "timestamp": datetime.now().isoformat(),
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
                    for repo in self.selected_projects
                ],
                "total_selected": len(self.selected_projects)
            }

            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)

            print(f"✅ Selection report exported to: {report_path}")

        except Exception as e:
            print(f"❌ Failed to export report: {e}")

# Global interface instance
selection_interface = ProjectSelectionInterface()

async def run_project_selection_interface():
    """Run the project selection interface"""
    await selection_interface.run_interface()

async def quick_select_and_update(criteria: str = "priority", count: int = 3):
    """Quick select and update operations centers"""
    print(f"🎯 Quick selection: Top {count} projects by {criteria}")

    # Select projects
    criteria_enum = SelectionCriteria(criteria)
    selected = await project_selector.select_top_projects(count, criteria_enum)

    if not selected:
        print("❌ No projects selected")
        return False

    # Update operations centers
    result = await project_selector.update_operations_centers(selected)

    if result.get("success"):
        print("✅ Operations centers updated successfully!")
        return True
    else:
        print("❌ Failed to update operations centers")
        return False

if __name__ == "__main__":
    # Run interactive interface
    asyncio.run(run_project_selection_interface())
