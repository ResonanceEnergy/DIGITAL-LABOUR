"""
Phase 4: Optimization & Scaling - Executive Development Programs
Executive development tracking and leadership growth frameworks
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from enum import Enum
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DevelopmentStage(Enum):
    """Executive development stages"""
    EMERGING = "emerging"
    MID_LEVEL = "mid_level"
    SENIOR = "senior"
    EXECUTIVE = "executive"
    C_SUITE = "c_suite"

class DevelopmentFocus(Enum):
    """Development focus areas"""
    LEADERSHIP = "leadership"
    STRATEGIC_THINKING = "strategic_thinking"
    CRISIS_MANAGEMENT = "crisis_management"
    TEAM_BUILDING = "team_building"
    INNOVATION = "innovation"
    ETHICAL_DECISION_MAKING = "ethical_decision_making"
    FINANCIAL_ACUMEN = "financial_acumen"
    DIGITAL_TRANSFORMATION = "digital_transformation"

@dataclass
class DevelopmentProgram:
    """Executive development program"""
    program_id: str
    title: str
    description: str
    target_stage: DevelopmentStage
    focus_areas: List[DevelopmentFocus]
    duration_weeks: int
    prerequisites: List[str] = field(default_factory=list)
    learning_objectives: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    is_active: bool = True

@dataclass
class ExecutiveProfile:
    """Executive development profile"""
    executive_id: str
    name: str
    current_stage: DevelopmentStage
    target_stage: DevelopmentStage
    development_focus: List[DevelopmentFocus]
    enrolled_programs: List[str] = field(default_factory=list)
    completed_programs: List[str] = field(default_factory=list)
    skills_assessment: Dict[str, float] = field(default_factory=dict)
    performance_metrics: Dict[str, Any] = field(default_factory=dict)
    mentorship_assignments: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)

@dataclass
class MentorshipAssignment:
    """Executive mentorship relationship"""
    assignment_id: str
    mentor_id: str
    mentee_id: str
    focus_areas: List[DevelopmentFocus]
    start_date: datetime
    end_date: Optional[datetime] = None
    goals: List[str] = field(default_factory=list)
    progress_notes: List[str] = field(default_factory=list)
    is_active: bool = True

class ExecutiveDevelopmentFramework:
    """
    Executive Development Programs Framework
    Manages executive growth, development programs, and mentorship
    """

    def __init__(self):
        """Initialize."""
        self.programs: Dict[str, DevelopmentProgram] = {}
        self.executives: Dict[str, ExecutiveProfile] = {}
        self.mentorships: Dict[str, MentorshipAssignment] = {}
        self.program_templates = self._initialize_program_templates()

        logger.info("Executive Development Framework initialized")

    def _initialize_program_templates(self) -> Dict[str, DevelopmentProgram]:
        """Initialize standard development program templates"""
        templates = {}

        # Emerging Leader Program
        templates["emerging_leader_foundation"] = DevelopmentProgram(
            program_id="emerging_leader_foundation",
            title="Emerging Leader Foundation",
            description="Build core leadership skills for new executives",
            target_stage=DevelopmentStage.EMERGING,
            focus_areas=[DevelopmentFocus.LEADERSHIP,
                DevelopmentFocus.TEAM_BUILDING],
            duration_weeks=12,
            learning_objectives=[
                "Develop basic leadership presence",
                "Master team communication skills",
                "Learn conflict resolution techniques",
                "Build decision-making confidence"
            ]
        )

        # Strategic Leadership Program
        templates["strategic_leadership_mastery"] = DevelopmentProgram(
            program_id="strategic_leadership_mastery",
            title="Strategic Leadership Mastery",
            description="Advanced strategic thinking and execution",
            target_stage=DevelopmentStage.SENIOR,
            focus_areas=[DevelopmentFocus.STRATEGIC_THINKING,
                DevelopmentFocus.INNOVATION],
            duration_weeks=24,
            prerequisites=["emerging_leader_foundation"],
            learning_objectives=[
                "Master strategic planning frameworks",
                "Develop innovation leadership skills",
                "Learn complex decision analysis",
                "Build strategic execution capabilities"
            ]
        )

        # Crisis Leadership Program
        templates["crisis_leadership_excellence"] = DevelopmentProgram(
            program_id="crisis_leadership_excellence",
            title="Crisis Leadership Excellence",
            description="Navigate crises with confidence and competence",
            target_stage=DevelopmentStage.EXECUTIVE,
            focus_areas=[DevelopmentFocus.CRISIS_MANAGEMENT,
                DevelopmentFocus.ETHICAL_DECISION_MAKING],
            duration_weeks=16,
            prerequisites=["strategic_leadership_mastery"],
            learning_objectives=[
                "Master crisis assessment frameworks",
                "Develop rapid decision-making under pressure",
                "Learn stakeholder communication in crises",
                "Build crisis recovery strategies"
            ]
        )

        # C-Suite Executive Program
        templates["c_suite_executive_mastery"] = DevelopmentProgram(
            program_id="c_suite_executive_mastery",
            title="C-Suite Executive Mastery",
            description="Ultimate executive leadership development",
            target_stage=DevelopmentStage.C_SUITE,
            focus_areas=[
                DevelopmentFocus.STRATEGIC_THINKING,
                DevelopmentFocus.CRISIS_MANAGEMENT,
                DevelopmentFocus.FINANCIAL_ACUMEN,
                DevelopmentFocus.DIGITAL_TRANSFORMATION
            ],
            duration_weeks=52,
            prerequisites=["crisis_leadership_excellence"],
            learning_objectives=[
                "Master board-level strategic thinking",
                "Develop enterprise-wide transformation skills",
                "Learn advanced financial strategy",
                "Build digital transformation leadership"
            ]
        )

        return templates

    def create_executive_profile(
            self, executive_id: str, name: str,
             current_stage: DevelopmentStage, target_stage: DevelopmentStage,
            development_focus: List[DevelopmentFocus]) ->str:
        """
        Create executive development profile

        Args:
            executive_id: Unique executive identifier
            name: Executive name
            current_stage: Current development stage
            target_stage: Target development stage
            development_focus: Development focus areas

        Returns:
            Profile ID
        """
        profile = ExecutiveProfile(
            executive_id=executive_id,
            name=name,
            current_stage=current_stage,
            target_stage=target_stage,
            development_focus=development_focus
        )

        self.executives[executive_id] = profile

        logger.info(f"Created executive profile for {name} ({executive_id})")
        return executive_id

    def enroll_in_program(self, executive_id: str, program_id: str) -> bool:
        """
        Enroll executive in development program

        Args:
            executive_id: Executive identifier
            program_id: Program identifier

        Returns:
            Success status
        """
        if executive_id not in self.executives:
            logger.error(f"Executive {executive_id} not found")
            return False

        if program_id not in self.program_templates:
            logger.error(f"Program {program_id} not found")
            return False

        executive = self.executives[executive_id]
        program = self.program_templates[program_id]

        # Check prerequisites
        if not self._check_prerequisites(executive, program):
            logger.error(f"Prerequisites not met for {program_id}")
            return False

        if program_id not in executive.enrolled_programs:
            executive.enrolled_programs.append(program_id)
            executive.last_updated = datetime.now()

            logger.info(f"Enrolled {executive.name} in {program.title}")
            return True

        return False

    def _check_prerequisites(self, executive: ExecutiveProfile,
                           program: DevelopmentProgram) -> bool:
        """Check if executive meets program prerequisites"""
        for prereq in program.prerequisites:
            if prereq not in executive.completed_programs:
                return False
        return True

    def complete_program(self, executive_id: str, program_id: str) -> bool:
        """
        Mark program as completed for executive

        Args:
            executive_id: Executive identifier
            program_id: Program identifier

        Returns:
            Success status
        """
        if executive_id not in self.executives:
            return False

        executive = self.executives[executive_id]

        if program_id in executive.enrolled_programs:
            executive.enrolled_programs.remove(program_id)
            executive.completed_programs.append(program_id)
            executive.last_updated = datetime.now()

            # Update development stage if appropriate
            self._update_development_stage(executive)

            logger.info(f"{executive.name} completed {program_id}")
            return True

        return False

    def _update_development_stage(self, executive: ExecutiveProfile):
        """Update executive development stage based on completed programs"""
        completed_programs = set(executive.completed_programs)

        if "c_suite_executive_mastery" in completed_programs:
            executive.current_stage = DevelopmentStage.C_SUITE
        elif "crisis_leadership_excellence" in completed_programs:
            executive.current_stage = DevelopmentStage.EXECUTIVE
        elif "strategic_leadership_mastery" in completed_programs:
            executive.current_stage = DevelopmentStage.SENIOR
        elif "emerging_leader_foundation" in completed_programs:
            executive.current_stage = DevelopmentStage.MID_LEVEL

    def assign_mentor(
            self, mentor_id: str, mentee_id: str,
            focus_areas: List[DevelopmentFocus],
            duration_weeks: int=26) ->str:
        """
        Assign mentorship relationship

        Args:
            mentor_id: Mentor executive ID
            mentee_id: Mentee executive ID
            focus_areas: Mentorship focus areas
            duration_weeks: Mentorship duration

        Returns:
            Assignment ID
        """
        assignment_id = f"mentorship_{mentor_id} _{mentee_id} _{
            datetime.now().strftime('%Y%m%d')} "

        assignment = MentorshipAssignment(
            assignment_id=assignment_id,
            mentor_id=mentor_id,
            mentee_id=mentee_id,
            focus_areas=focus_areas,
            start_date=datetime.now(),
            end_date=datetime.now() + timedelta(weeks=duration_weeks),
            goals=self._generate_mentorship_goals(focus_areas)
        )

        self.mentorships[assignment_id] = assignment

        # Update executive profiles
        if mentee_id in self.executives:
            self.executives[mentee_id].mentorship_assignments.append(
                assignment_id)

        logger.info(f"Assigned mentorship: {mentor_id} -> {mentee_id}")
        return assignment_id

    def _generate_mentorship_goals(
            self, focus_areas: List[DevelopmentFocus]) ->List[str]:
        """Generate mentorship goals based on focus areas"""
        goals = []
        for focus in focus_areas:
            if focus == DevelopmentFocus.LEADERSHIP:
                goals.extend([
                    "Develop authentic leadership presence",
                    "Master executive communication skills",
                    "Learn strategic delegation techniques"
                ])
            elif focus == DevelopmentFocus.STRATEGIC_THINKING:
                goals.extend([
                    "Learn long-term strategic planning",
                    "Develop scenario planning skills",
                    "Master competitive analysis frameworks"
                ])
            elif focus == DevelopmentFocus.CRISIS_MANAGEMENT:
                goals.extend([
                    "Learn crisis assessment methodologies",
                    "Develop rapid decision-making skills",
                    "Master stakeholder communication in crises"
                ])
        return goals

    def get_development_status(self) -> Dict[str, Any]:
        """
        Get overall development program status

        Returns:
            Development status summary
        """
        return {
            "total_executives": len(self.executives),
            "active_programs": len(self.program_templates),
            "active_mentorships": len([m for m in self.mentorships.values() if m.is_active]),
            "program_completion_rate": self._calculate_completion_rate(),
            "stage_distribution": self._get_stage_distribution(),
            "focus_area_coverage": self._get_focus_coverage()
        }

    def _calculate_completion_rate(self) -> float:
        """Calculate program completion rate"""
        total_enrollments = sum(
            len(exec.enrolled_programs) +len(exec.completed_programs)
            for exec in self.executives.values())
        if total_enrollments == 0:
            return 0.0

        completed = sum(len(exec.completed_programs)
                        for exec in self.executives.values())
        return completed / total_enrollments

    def _get_stage_distribution(self) -> Dict[str, int]:
        """Get distribution of executives by development stage"""
        distribution = {}
        for stage in DevelopmentStage:
            count = sum(1 for exec in self.executives.values()
                       if exec.current_stage == stage)
            distribution[stage.value] = count
        return distribution

    def _get_focus_coverage(self) -> Dict[str, int]:
        """Get coverage of development focus areas"""
        coverage = {}
        for focus in DevelopmentFocus:
            count = sum(1 for exec in self.executives.values()
                       if focus in exec.development_focus)
            coverage[focus.value] = count
        return coverage

    def get_executive_progress(self, executive_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed progress for specific executive

        Args:
            executive_id: Executive identifier

        Returns:
            Executive progress details
        """
        if executive_id not in self.executives:
            return None

        executive = self.executives[executive_id]

        return {
            "executive_id": executive_id,
            "name": executive.name,
            "current_stage": executive.current_stage.value,
            "target_stage": executive.target_stage.value,
            "enrolled_programs": executive.enrolled_programs,
            "completed_programs": executive.completed_programs,
            "active_mentorships": [
                m for m in executive.mentorship_assignments
                if m in self.mentorships and self.mentorships[m].is_active
            ],
            "progress_percentage": self._calculate_progress_percentage(executive),
            "next_recommended_programs": self._recommend_next_programs(executive)
        }

    def _calculate_progress_percentage(
            self, executive: ExecutiveProfile) ->float:
        """Calculate overall progress percentage for executive"""
        total_programs = len(self.program_templates)
        completed_count = len(executive.completed_programs)
        enrolled_count = len(executive.enrolled_programs)

        return ((completed_count + enrolled_count * 0.5) / total_programs) * 100

    def _recommend_next_programs(
            self, executive: ExecutiveProfile) ->List[str]:
        """Recommend next programs for executive"""
        recommendations = []

        for program_id, program in self.program_templates.items():
            if (program_id not in executive.completed_programs and
                program_id not in executive.enrolled_programs and
                self._check_prerequisites(executive, program) and
                program.target_stage.value in [executive.current_stage.value,
                                             executive.target_stage.value]):
                recommendations.append(program_id)

        return recommendations[:3]  # Return top 3 recommendations