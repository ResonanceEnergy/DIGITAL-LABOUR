#!/usr/bin/env python3
"""
Matrix Monitor Project Selector
Allows selection of top 3 projects from Matrix Monitor data for operations centers
"""

import json
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

class SelectionCriteria(Enum):
    """Criteria for selecting top projects"""
    SIZE = "size"  # Repository size in MB
    STARS = "stars"  # GitHub stars
    FORKS = "forks"  # Number of forks
    ISSUES = "issues"  # Open issues count
    ACTIVITY = "activity"  # Recent activity score
    PRIORITY = "priority"  # Custom priority score

@dataclass
class RepositoryInfo:
    """Repository information for selection"""
    name: str
    full_name: str
    size: int  # Size in KB
    stars: int
    forks: int
    open_issues: int
    created_at: str
    updated_at: str
    language: Optional[str] = None
    description: Optional[str] = None
    priority_score: float = 0.0

    @property
    def size_mb(self) -> float:
        """Size in MB"""
        return self.size / 1024

    @property
    def activity_score(self) -> float:
        """Calculate activity score based on recent updates"""
        try:
            updated = datetime.fromisoformat(self.updated_at.replace('Z', '+00:00'))
            days_since_update = (datetime.now(updated.tzinfo) - updated).days
            # Higher score for more recent updates
            return max(0, 100 - days_since_update)
        except:
            return 50.0

class MatrixMonitorProjectSelector:
    """Select top projects from Matrix Monitor data"""

    def __init__(self, repo_index_path: str = "REPO_INDEX.json"):
        self.repo_index_path = repo_index_path
        self.repositories: List[RepositoryInfo] = []
        self.selected_projects: List[RepositoryInfo] = []
        self.logger = logging.getLogger(__name__)

    async def load_repository_data(self) -> List[RepositoryInfo]:
        """Load repository data from index file"""
        try:
            with open(self.repo_index_path, 'r', encoding='utf-8') as f:
                repo_data = json.load(f)

            repositories = []
            for repo in repo_data:
                repo_info = RepositoryInfo(
                    name=repo.get('name', ''),
                    full_name=repo.get('full_name', ''),
                    size=repo.get('size', 0),
                    stars=repo.get('stargazers_count', 0),
                    forks=repo.get('forks_count', 0),
                    open_issues=repo.get('open_issues_count', 0),
                    created_at=repo.get('created_at', ''),
                    updated_at=repo.get('updated_at', ''),
                    language=repo.get('language'),
                    description=repo.get('description', '')
                )
                repositories.append(repo_info)

            self.repositories = repositories
            self.logger.info(f"Loaded {len(repositories)} repositories from index")
            return repositories

        except Exception as e:
            self.logger.error(f"Failed to load repository data: {e}")
            return []

    def calculate_priority_scores(self, criteria_weights: Dict[SelectionCriteria, float] = None) -> None:
        """Calculate priority scores for all repositories"""
        if criteria_weights is None:
            # Default weights
            criteria_weights = {
                SelectionCriteria.SIZE: 0.3,
                SelectionCriteria.STARS: 0.25,
                SelectionCriteria.ACTIVITY: 0.25,
                SelectionCriteria.ISSUES: -0.1,  # Negative because more issues = lower priority
                SelectionCriteria.FORKS: 0.2
            }

        # Normalize values for fair comparison
        if not self.repositories:
            return

        # Get max values for normalization
        max_size = max(r.size for r in self.repositories)
        max_stars = max(r.stars for r in self.repositories)
        max_forks = max(r.forks for r in self.repositories)
        max_issues = max(r.open_issues for r in self.repositories) or 1

        for repo in self.repositories:
            # Normalize each metric (0-1 scale)
            size_score = repo.size / max_size if max_size > 0 else 0
            stars_score = repo.stars / max_stars if max_stars > 0 else 0
            forks_score = repo.forks / max_forks if max_forks > 0 else 0
            issues_score = 1 - (repo.open_issues / max_issues)  # Invert issues (fewer issues = higher score)
            activity_score = repo.activity_score / 100  # Already 0-100

            # Calculate weighted priority score
            priority_score = (
                criteria_weights[SelectionCriteria.SIZE] * size_score +
                criteria_weights[SelectionCriteria.STARS] * stars_score +
                criteria_weights[SelectionCriteria.FORKS] * forks_score +
                criteria_weights[SelectionCriteria.ISSUES] * issues_score +
                criteria_weights[SelectionCriteria.ACTIVITY] * activity_score
            )

            repo.priority_score = priority_score

    async def select_top_projects(self, count: int = 3,
                                criteria: SelectionCriteria = SelectionCriteria.PRIORITY,
                                custom_weights: Dict[SelectionCriteria, float] = None) -> List[RepositoryInfo]:
        """Select top projects based on criteria"""
        if not self.repositories:
            await self.load_repository_data()

        if not self.repositories:
            self.logger.warning("No repository data available")
            return []

        # Calculate priority scores if needed
        if criteria == SelectionCriteria.PRIORITY or custom_weights:
            self.calculate_priority_scores(custom_weights)

        # Sort repositories based on criteria
        if criteria == SelectionCriteria.SIZE:
            sorted_repos = sorted(self.repositories, key=lambda r: r.size, reverse=True)
        elif criteria == SelectionCriteria.STARS:
            sorted_repos = sorted(self.repositories, key=lambda r: r.stars, reverse=True)
        elif criteria == SelectionCriteria.FORKS:
            sorted_repos = sorted(self.repositories, key=lambda r: r.forks, reverse=True)
        elif criteria == SelectionCriteria.ISSUES:
            sorted_repos = sorted(self.repositories, key=lambda r: r.open_issues, reverse=False)  # Fewer issues first
        elif criteria == SelectionCriteria.ACTIVITY:
            sorted_repos = sorted(self.repositories, key=lambda r: r.activity_score, reverse=True)
        elif criteria == SelectionCriteria.PRIORITY:
            sorted_repos = sorted(self.repositories, key=lambda r: r.priority_score, reverse=True)
        else:
            sorted_repos = self.repositories

        # Select top projects
        self.selected_projects = sorted_repos[:count]

        self.logger.info(f"Selected top {count} projects using {criteria.value} criteria:")
        for i, repo in enumerate(self.selected_projects, 1):
            self.logger.info(f"  {i}. {repo.full_name} (Score: {repo.priority_score:.2f})")

        return self.selected_projects

    def get_selection_options(self) -> Dict[str, Any]:
        """Get available selection options for Matrix Monitor UI"""
        return {
            "criteria_options": [c.value for c in SelectionCriteria],
            "current_selection": [
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
            "total_repositories": len(self.repositories),
            "selection_timestamp": datetime.now().isoformat()
        }

    async def update_operations_centers(self, selected_projects: List[RepositoryInfo]) -> Dict[str, Any]:
        """Update operations centers to work on selected projects"""
        if len(selected_projects) < 3:
            self.logger.warning("Need at least 3 projects for operations centers")
            return {"success": False, "message": "Need at least 3 projects"}

        # Import operations centers manager
        from operations_centers import operations_manager

        # Create new center configurations
        new_centers = {
            "core_agency": {
                "name": "Core Agency Operations Center",
                "repository": selected_projects[0].full_name,
                "priority": 1,
                "agent_count": 12
            },
            "enterprise": {
                "name": "Enterprise Systems Operations Center",
                "repository": selected_projects[1].full_name,
                "priority": 2,
                "agent_count": 10
            },
            "neural_control": {
                "name": "Neural Control Operations Center",
                "repository": selected_projects[2].full_name,
                "priority": 3,
                "agent_count": 8
            }
        }

        # Update operations centers
        update_result = await operations_manager.update_operations_centers(new_centers)

        self.logger.info("Operations centers updated with new project selections")
        return {
            "success": True,
            "centers_updated": update_result.get("centers_updated", []),
            "projects_assigned": [p.full_name for p in selected_projects[:3]],
            "update_result": update_result
        }

    async def get_matrix_monitor_data(self) -> Dict[str, Any]:
        """Get data formatted for Matrix Monitor display"""
        if not self.repositories:
            await self.load_repository_data()

        return {
            "project_selector": {
                "total_repositories": len(self.repositories),
                "selected_projects": len(self.selected_projects),
                "selection_options": self.get_selection_options(),
                "available_criteria": [c.value for c in SelectionCriteria],
                "last_updated": datetime.now().isoformat()
            },
            "top_projects": [
                {
                    "rank": i + 1,
                    "name": repo.name,
                    "full_name": repo.full_name,
                    "size_mb": round(repo.size_mb, 2),
                    "stars": repo.stars,
                    "forks": repo.forks,
                    "issues": repo.open_issues,
                    "activity": round(repo.activity_score, 1),
                    "priority": round(repo.priority_score, 2),
                    "language": repo.language or "Unknown"
                }
                for i, repo in enumerate(self.selected_projects[:10])  # Top 10 for display
            ]
        }

# Global project selector instance
project_selector = MatrixMonitorProjectSelector()

async def select_top_projects(criteria: str = "priority", count: int = 3):
    """Select top projects using specified criteria"""
    criteria_enum = SelectionCriteria(criteria)
    return await project_selector.select_top_projects(count, criteria_enum)

async def get_project_selector_data():
    """Get project selector data for Matrix Monitor"""
    return await project_selector.get_matrix_monitor_data()

async def update_operations_centers_with_selection():
    """Update operations centers with current selection"""
    if not project_selector.selected_projects:
        await project_selector.select_top_projects()
    return await project_selector.update_operations_centers(project_selector.selected_projects)

if __name__ == "__main__":
    # Demo project selection
    async def demo():
        print("🔍 Matrix Monitor Project Selector Demo")
        print("=" * 50)

        # Load repository data
        print("📊 Loading repository data...")
        repos = await project_selector.load_repository_data()
        print(f"✅ Loaded {len(repos)} repositories")

        # Select top 3 projects
        print("🎯 Selecting top 3 projects...")
        selected = await project_selector.select_top_projects(3, SelectionCriteria.PRIORITY)
        print(f"✅ Selected {len(selected)} projects")

        # Display selection
        print("\n🏆 Top 3 Selected Projects:")
        for i, repo in enumerate(selected, 1):
            print(f"  {i}. {repo.full_name}")
            print(f"     Size: {repo.size_mb:.2f}MB, Stars: {repo.stars}, Priority: {repo.priority_score:.2f}")
            print(f"     Language: {repo.language or 'Unknown'}")
            print()

        # Get Matrix Monitor data
        print("📊 Getting Matrix Monitor data...")
        monitor_data = await project_selector.get_matrix_monitor_data()
        print(f"✅ Generated monitor data with {monitor_data['project_selector']['total_repositories']} repositories")

        print("\n🎉 Project selection completed successfully!")

    asyncio.run(demo())
