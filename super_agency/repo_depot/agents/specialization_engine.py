# REPO DEPOT AGENTS - Advanced Specialization Engine

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
import statistics
import json

from .agent_registry import AgentRegistry, AgentSpecialization, AgentCapability, RepoDepotAgent

logger = logging.getLogger(__name__)


class SpecializationLevel(Enum):
    NOVICE = "novice"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"
    MASTER = "master"


@dataclass
class SkillProfile:
    """Profile of an agent's skills and capabilities"""

    specialization: AgentSpecialization
    level: SpecializationLevel
    proficiency_score: float  # 0.0 to 1.0
    experience_points: int = 0
    tasks_completed: int = 0
    success_rate: float = 0.0
    specialties: Set[str] = field(default_factory=set)
    weaknesses: Set[str] = field(default_factory=set)
    last_updated: datetime = field(default_factory=datetime.now)

    def update_proficiency(self, task_success: bool, task_complexity: float = 1.0):
        """Update proficiency based on task performance"""
        self.tasks_completed += 1

        if task_success:
            # Increase proficiency with diminishing returns
            improvement = (1.0 - self.proficiency_score) * 0.1 * task_complexity
            self.proficiency_score = min(1.0, self.proficiency_score + improvement)
            self.experience_points += int(10 * task_complexity)
        else:
            # Small decrease on failure
            self.proficiency_score = max(0.0, self.proficiency_score - 0.05)

        # Update success rate
        if self.tasks_completed > 0:
            self.success_rate = (
                (self.success_rate * (self.tasks_completed - 1)) + (1.0 if task_success else 0.0)
            ) / self.tasks_completed

        # Update level based on proficiency and experience
        self._update_level()
        self.last_updated = datetime.now()

    def _update_level(self):
        """Update specialization level based on proficiency and experience"""
        score = (self.proficiency_score * 0.7) + (min(1.0, self.experience_points / 1000) * 0.3)

        if score >= 0.9:
            self.level = SpecializationLevel.MASTER
        elif score >= 0.75:
            self.level = SpecializationLevel.EXPERT
        elif score >= 0.6:
            self.level = SpecializationLevel.ADVANCED
        elif score >= 0.4:
            self.level = SpecializationLevel.INTERMEDIATE
        else:
            self.level = SpecializationLevel.NOVICE

    def add_specialty(self, specialty: str):
        """Add a specialty area"""
        self.specialties.add(specialty)

    def add_weakness(self, weakness: str):
        """Add a known weakness"""
        self.weaknesses.add(weakness)


@dataclass
class TaskPattern:
    """Pattern of task characteristics for specialization matching"""

    task_type: str
    complexity: float
    required_skills: Set[str]
    estimated_duration: float
    success_criteria: List[str]


class SpecializationEngine:
    """
    Advanced engine for dynamic agent specialization and skill development.
    Analyzes task patterns and agent performance to optimize specialization.
    """

    def __init__(self, agent_registry: AgentRegistry):
        self.registry = agent_registry
        self.skill_profiles: Dict[str, Dict[AgentSpecialization, SkillProfile]] = {}
        self.task_patterns: Dict[str, TaskPattern] = {}
        self.learning_rate = 0.1
        self.adaptation_threshold = 0.7

        # Initialize skill profiles for existing agents
        self._initialize_skill_profiles()

    def _initialize_skill_profiles(self):
        """Initialize skill profiles for all registered agents"""
        for agent_id, agent in self.registry.agents.items():
            self.skill_profiles[agent_id] = {}
            for spec in AgentSpecialization:
                # Start with basic proficiency based on agent's declared specialization
                base_proficiency = 0.5 if spec == agent.specialization else 0.1
                self.skill_profiles[agent_id][spec] = SkillProfile(
                    specialization=spec,
                    level=SpecializationLevel.NOVICE,
                    proficiency_score=base_proficiency,
                    specialties=set(),
                    weaknesses=set(),
                )

    async def analyze_task_performance(
        self,
        agent_id: str,
        task_type: str,
        success: bool,
        duration: float,
        complexity: float = 1.0,
    ):
        """Analyze task performance and update agent specialization"""
        if agent_id not in self.skill_profiles:
            logger.warning(f"No skill profile found for agent {agent_id}")
            return

        # Determine which specialization was used
        specialization = self._infer_specialization_from_task(task_type)

        if specialization not in self.skill_profiles[agent_id]:
            # Create new skill profile for this specialization
            self.skill_profiles[agent_id][specialization] = SkillProfile(
                specialization=specialization,
                level=SpecializationLevel.NOVICE,
                proficiency_score=0.1,
            )

        profile = self.skill_profiles[agent_id][specialization]
        profile.update_proficiency(success, complexity)

        # Analyze performance patterns
        await self._analyze_performance_patterns(agent_id, task_type, success, duration)

        # Check for specialization adaptation
        await self._check_specialization_adaptation(agent_id)

        logger.info(
            f"Updated skill profile for {agent_id}: {specialization.value} -> {profile.level.value} ({profile.proficiency_score:.2f})"
        )

    def _infer_specialization_from_task(self, task_type: str) -> AgentSpecialization:
        """Infer specialization from task type"""
        task_lower = task_type.lower()

        if any(
            keyword in task_lower for keyword in ["architecture", "design", "planning", "strategy"]
        ):
            return AgentSpecialization.STRATEGIC
        elif any(keyword in task_lower for keyword in ["implement", "code", "build", "develop"]):
            return AgentSpecialization.IMPLEMENTATION
        elif any(keyword in task_lower for keyword in ["analyze", "review", "assess", "audit"]):
            return AgentSpecialization.ANALYSIS
        elif any(keyword in task_lower for keyword in ["coordinate", "manage", "orchestrate"]):
            return AgentSpecialization.COORDINATION
        elif any(keyword in task_lower for keyword in ["optimize", "performance", "tune"]):
            return AgentSpecialization.OPTIMIZATION
        else:
            return AgentSpecialization.IMPLEMENTATION  # Default

    async def _analyze_performance_patterns(
        self, agent_id: str, task_type: str, success: bool, duration: float
    ):
        """Analyze performance patterns to identify strengths and weaknesses"""
        # This would analyze historical performance data
        # For now, just log patterns
        if success and duration < 300:  # Fast success
            profile = self.skill_profiles[agent_id].get(
                self._infer_specialization_from_task(task_type)
            )
            if profile:
                profile.add_specialty(f"fast_{task_type}")
        elif not success:
            profile = self.skill_profiles[agent_id].get(
                self._infer_specialization_from_task(task_type)
            )
            if profile:
                profile.add_weakness(f"slow_{task_type}")

    async def _check_specialization_adaptation(self, agent_id: str):
        """Check if agent should adapt specialization based on performance"""
        if agent_id not in self.skill_profiles:
            return

        profiles = self.skill_profiles[agent_id]
        current_spec = self.registry.agents[agent_id].specialization

        # Find best performing specialization
        best_spec = max(profiles.items(), key=lambda x: x[1].proficiency_score)

        if (
            best_spec[0] != current_spec
            and best_spec[1].proficiency_score > self.adaptation_threshold
        ):
            # Check if adaptation makes sense (significant performance difference)
            current_score = profiles[current_spec].proficiency_score
            if best_spec[1].proficiency_score > current_score + 0.2:
                logger.info(
                    f"Recommending specialization change for {agent_id}: {current_spec.value} -> {best_spec[0].value}"
                )
                # Could trigger adaptation process here

    def recommend_agent_for_task(
        self, task_type: str, required_skills: List[str] = None
    ) -> Optional[str]:
        """Recommend the best agent for a given task"""
        if not required_skills:
            required_skills = []

        specialization = self._infer_specialization_from_task(task_type)
        best_agent = None
        best_score = 0.0

        for agent_id, profiles in self.skill_profiles.items():
            agent = self.registry.agents.get(agent_id)
            if not agent or agent.status != self.registry.AgentStatus.ACTIVE:
                continue

            profile = profiles.get(specialization)
            if not profile:
                continue

            # Calculate match score
            score = profile.proficiency_score * 0.6

            # Bonus for specialties
            skill_matches = sum(1 for skill in required_skills if skill in profile.specialties)
            score += (skill_matches / len(required_skills)) * 0.4 if required_skills else 0

            # Penalty for weaknesses
            weakness_penalty = (
                sum(1 for skill in required_skills if skill in profile.weaknesses) * 0.1
            )
            score -= weakness_penalty

            if score > best_score:
                best_score = score
                best_agent = agent_id

        return best_agent

    def get_specialization_report(self, agent_id: str) -> Dict[str, Any]:
        """Get detailed specialization report for an agent"""
        if agent_id not in self.skill_profiles:
            return {"error": "Agent not found"}

        profiles = self.skill_profiles[agent_id]
        agent = self.registry.agents[agent_id]

        return {
            "agent_id": agent_id,
            "current_specialization": agent.specialization.value,
            "skill_profiles": {
                spec.value: {
                    "level": profile.level.value,
                    "proficiency": profile.proficiency_score,
                    "experience_points": profile.experience_points,
                    "tasks_completed": profile.tasks_completed,
                    "success_rate": profile.success_rate,
                    "specialties": list(profile.specialties),
                    "weaknesses": list(profile.weaknesses),
                }
                for spec, profile in profiles.items()
            },
            "recommendations": self._generate_recommendations(agent_id),
        }

    def _generate_recommendations(self, agent_id: str) -> List[str]:
        """Generate specialization recommendations for an agent"""
        recommendations = []
        profiles = self.skill_profiles[agent_id]

        # Find strongest and weakest specializations
        sorted_specs = sorted(profiles.items(), key=lambda x: x[1].proficiency_score, reverse=True)

        if sorted_specs:
            strongest = sorted_specs[0]
            if strongest[1].proficiency_score > 0.8:
                recommendations.append(f"Consider specializing further in {strongest[0].value}")

            weakest = sorted_specs[-1]
            if weakest[1].proficiency_score < 0.3:
                recommendations.append(f"Focus on improving {weakest[0].value} skills")

        return recommendations

    def get_system_specialization_stats(self) -> Dict[str, Any]:
        """Get system-wide specialization statistics"""
        total_agents = len(self.skill_profiles)
        specialization_counts = {}

        for agent_profiles in self.skill_profiles.values():
            for spec, profile in agent_profiles.items():
                if spec not in specialization_counts:
                    specialization_counts[spec] = {
                        "count": 0,
                        "avg_proficiency": 0.0,
                        "levels": {},
                    }

                specialization_counts[spec]["count"] += 1
                specialization_counts[spec]["avg_proficiency"] += profile.proficiency_score

                level = profile.level.value
                specialization_counts[spec]["levels"][level] = (
                    specialization_counts[spec]["levels"].get(level, 0) + 1
                )

        # Calculate averages
        for spec_data in specialization_counts.values():
            if spec_data["count"] > 0:
                spec_data["avg_proficiency"] /= spec_data["count"]

        return {
            "total_agents": total_agents,
            "specialization_distribution": {
                spec.value: data for spec, data in specialization_counts.items()
            },
        }


# Global specialization engine instance
specialization_engine = SpecializationEngine(AgentRegistry())
