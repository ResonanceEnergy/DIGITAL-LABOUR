#!/usr/bin/env python3
"""
Cognitive Architecture — Brain / Perception / Action framework for agents.

Implements structured reasoning patterns from agentic AI research:
- ReAct (Reasoning + Acting) — Thought-Action-Observation loops
- Reflexion — Self-critique and corrective learning from failures
- Goal Decomposition — Hierarchical Goal → Subgoal → Task → Action
- Episodic Memory — Event replay and experiential learning
- Uncertainty Tracking — Confidence propagation through reasoning chains

Based on:
- "The Rise and Potential of LLM Based Agents: A Survey" (Xi et al., 2023)
- "LLM Powered Autonomous Agents" (Lilian Weng, 2023)
- "Reflexion: Language Agents with Verbal Reinforcement Learning" (Shinn, 2023)
- "AutoGen: Enabling Next-Gen LLM Applications" (Wu et al., 2023)

Usage:
    from tools.cognitive_architecture import (
        CognitiveAgent, ReActLoop, ReflexionEngine,
        GoalDecomposer, CognitiveMemory
    )

    agent = CognitiveAgent("researcher", domains=["research", "analysis"])
    result = agent.reason_and_act(task="Analyze market trends for QFORGE")
"""

import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
MEMORY_DIR = ROOT / "data" / "cognitive_memory"
MEMORY_DIR.mkdir(parents=True, exist_ok=True)


# ═══════════════════════════════════════════════════════════════════════
#  ENUMS & CONSTANTS
# ═══════════════════════════════════════════════════════════════════════

class Confidence(Enum):
    VERY_LOW = 0.1
    LOW = 0.3
    MEDIUM = 0.5
    HIGH = 0.7
    VERY_HIGH = 0.9
    CERTAIN = 1.0


class GoalStatus(Enum):
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


class ReasoningStepType(Enum):
    THOUGHT = "thought"
    ACTION = "action"
    OBSERVATION = "observation"
    REFLECTION = "reflection"
    CRITIQUE = "critique"
    DECISION = "decision"


# ═══════════════════════════════════════════════════════════════════════
#  DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class ReasoningStep:
    """Single step in a ReAct reasoning chain."""
    step_type: ReasoningStepType
    content: str
    confidence: float = 0.5
    evidence: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    step_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])

    def to_dict(self) -> dict:
        return {
            "step_type": self.step_type.value,
            "content": self.content,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "timestamp": self.timestamp,
            "step_id": self.step_id,
        }


@dataclass
class ReasoningTrace:
    """Complete reasoning chain for a task."""
    task: str
    steps: List[ReasoningStep] = field(default_factory=list)
    outcome: Optional[str] = None
    success: bool = False
    trace_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    started: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    completed: Optional[str] = None

    def add_step(self, step_type: ReasoningStepType, content: str,
                 confidence: float = 0.5, evidence: Optional[str] = None) -> ReasoningStep:
        step = ReasoningStep(step_type=step_type, content=content,
                             confidence=confidence, evidence=evidence)
        self.steps.append(step)
        return step

    def finalize(self, outcome: str, success: bool):
        self.outcome = outcome
        self.success = success
        self.completed = datetime.now().isoformat(timespec="seconds")

    @property
    def avg_confidence(self) -> float:
        if not self.steps:
            return 0.0
        return sum(s.confidence for s in self.steps) / len(self.steps)

    def to_dict(self) -> dict:
        return {
            "trace_id": self.trace_id,
            "task": self.task,
            "steps": [s.to_dict() for s in self.steps],
            "outcome": self.outcome,
            "success": self.success,
            "avg_confidence": round(self.avg_confidence, 3),
            "started": self.started,
            "completed": self.completed,
        }


@dataclass
class Goal:
    """Hierarchical goal with decomposition support."""
    description: str
    goal_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    parent_id: Optional[str] = None
    status: GoalStatus = GoalStatus.PENDING
    priority: int = 5  # 1-10, 10 = highest
    preconditions: List[str] = field(default_factory=list)
    postconditions: List[str] = field(default_factory=list)
    subgoals: List[str] = field(default_factory=list)  # goal_ids
    assigned_agent: Optional[str] = None
    confidence: float = 0.5
    created: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    completed: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "goal_id": self.goal_id,
            "description": self.description,
            "parent_id": self.parent_id,
            "status": self.status.value,
            "priority": self.priority,
            "preconditions": self.preconditions,
            "postconditions": self.postconditions,
            "subgoals": self.subgoals,
            "assigned_agent": self.assigned_agent,
            "confidence": self.confidence,
            "created": self.created,
            "completed": self.completed,
        }


@dataclass
class Episode:
    """Episodic memory entry — records an experience for future learning."""
    event: str
    context: Dict[str, Any]
    outcome: str
    success: bool
    lesson: Optional[str] = None
    importance: float = 0.5  # 0.0-1.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    episode_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])

    def to_dict(self) -> dict:
        return {
            "episode_id": self.episode_id,
            "event": self.event,
            "context": self.context,
            "outcome": self.outcome,
            "success": self.success,
            "lesson": self.lesson,
            "importance": self.importance,
            "timestamp": self.timestamp,
        }


# ═══════════════════════════════════════════════════════════════════════
#  ReAct LOOP — Reasoning + Acting
# ═══════════════════════════════════════════════════════════════════════

class ReActLoop:
    """
    Implements the ReAct pattern: Thought → Action → Observation loops.

    Each iteration:
    1. THOUGHT: Agent reasons about current state
    2. ACTION: Agent selects and executes an action
    3. OBSERVATION: Agent observes the result

    Continues until task is complete or max_steps reached.
    """

    def __init__(self, max_steps: int = 10,
                 confidence_threshold: float = 0.7):
        self.max_steps = max_steps
        self.confidence_threshold = confidence_threshold

    def execute(self, task: str,
                think_fn: Callable[[str, List[ReasoningStep]], str],
                act_fn: Callable[[str], dict],
                observe_fn: Callable[[dict], str],
                should_stop_fn: Optional[Callable[[List[ReasoningStep]], bool]] = None
                ) -> ReasoningTrace:
        """
        Execute a ReAct reasoning loop.

        Parameters
        ----------
        task : str
            The task to reason about and act on.
        think_fn : callable
            (task, history) → thought string
        act_fn : callable
            (thought) → action result dict
        observe_fn : callable
            (action_result) → observation string
        should_stop_fn : callable, optional
            (history) → bool, custom termination check
        """
        trace = ReasoningTrace(task=task)

        for step_num in range(self.max_steps):
            # THOUGHT
            thought = think_fn(task, trace.steps)
            trace.add_step(ReasoningStepType.THOUGHT, thought,
                           confidence=0.5 + (step_num * 0.05))

            # ACTION
            try:
                action_result = act_fn(thought)
                trace.add_step(ReasoningStepType.ACTION,
                               json.dumps(action_result, default=str),
                               confidence=0.6)
            except Exception as e:
                trace.add_step(ReasoningStepType.ACTION,
                               f"ERROR: {e}", confidence=0.1)
                trace.add_step(ReasoningStepType.OBSERVATION,
                               f"Action failed: {e}", confidence=0.1)
                continue

            # OBSERVATION
            observation = observe_fn(action_result)
            obs_confidence = 0.7 if "success" in observation.lower() else 0.4
            trace.add_step(ReasoningStepType.OBSERVATION, observation,
                           confidence=obs_confidence)

            # Check termination
            if should_stop_fn and should_stop_fn(trace.steps):
                trace.finalize(observation, success=True)
                break

            if trace.avg_confidence >= self.confidence_threshold:
                trace.finalize(observation, success=True)
                break
        else:
            trace.finalize("Max steps reached", success=False)

        return trace


# ═══════════════════════════════════════════════════════════════════════
#  REFLEXION ENGINE — Self-critique and corrective learning
# ═══════════════════════════════════════════════════════════════════════

class ReflexionEngine:
    """
    Implements Reflexion: self-evaluation after task execution.

    After each task attempt, the agent:
    1. Evaluates whether the outcome met expectations
    2. Identifies what went wrong (if failure)
    3. Generates corrective insights
    4. Stores lessons in episodic memory for future retrieval
    """

    def __init__(self, memory: Optional["CognitiveMemory"] = None,
                 max_retries: int = 3):
        self.memory = memory or CognitiveMemory("reflexion")
        self.max_retries = max_retries

    def reflect(self, trace: ReasoningTrace,
                evaluate_fn: Callable[[ReasoningTrace], Dict[str, Any]]
                ) -> Dict[str, Any]:
        """
        Reflect on a completed reasoning trace.

        Parameters
        ----------
        trace : ReasoningTrace
            The completed task execution trace.
        evaluate_fn : callable
            (trace) → {"success": bool, "quality": float, "issues": [...]}

        Returns
        -------
        dict with reflection results including lessons learned.
        """
        evaluation = evaluate_fn(trace)
        success = evaluation.get("success", trace.success)
        quality = evaluation.get("quality", trace.avg_confidence)
        issues = evaluation.get("issues", [])

        # Generate reflection step
        if success and quality >= 0.7:
            reflection = f"Task completed successfully (quality={quality:.2f}). "
            if issues:
                reflection += f"Minor issues: {', '.join(issues)}"
            lesson = f"Approach worked well for '{trace.task}'"
        else:
            reflection = f"Task {'failed' if not success else 'low quality'} "
            reflection += f"(quality={quality:.2f}). Issues: {', '.join(issues)}"
            lesson = f"For '{trace.task}': avoid {', '.join(issues[:3])}"

        # Add reflection to trace
        trace.add_step(ReasoningStepType.REFLECTION, reflection,
                       confidence=quality)

        # Store as episodic memory
        episode = Episode(
            event=f"reflexion:{trace.task}",
            context={"trace_id": trace.trace_id, "step_count": len(trace.steps)},
            outcome=reflection,
            success=success,
            lesson=lesson,
            importance=0.8 if not success else 0.5,
        )
        self.memory.store_episode(episode)

        return {
            "reflection": reflection,
            "lesson": lesson,
            "quality": quality,
            "success": success,
            "episode_id": episode.episode_id,
        }

    def reflect_and_retry(self, task: str,
                          execute_fn: Callable[[str, List[Episode]], ReasoningTrace],
                          evaluate_fn: Callable[[ReasoningTrace], Dict[str, Any]]
                          ) -> ReasoningTrace:
        """
        Execute task with retry + reflection loop.

        On failure, reflects on the attempt and feeds lessons into next try.
        """
        past_lessons = self.memory.recall_relevant(task, limit=5)

        for attempt in range(self.max_retries):
            trace = execute_fn(task, past_lessons)
            evaluation = evaluate_fn(trace)

            if evaluation.get("success", False):
                self.reflect(trace, evaluate_fn)
                return trace

            # Reflect and gather new lessons
            result = self.reflect(trace, evaluate_fn)
            past_lessons = self.memory.recall_relevant(task, limit=5)
            logger.info("Reflexion attempt %d/%d for '%s': %s",
                        attempt + 1, self.max_retries, task, result["lesson"])

        return trace


# ═══════════════════════════════════════════════════════════════════════
#  GOAL DECOMPOSER — Hierarchical goal management
# ═══════════════════════════════════════════════════════════════════════

class GoalDecomposer:
    """
    Manages hierarchical goal decomposition.

    Goal → Subgoals → Tasks → Actions

    Each goal has preconditions (what must be true before starting) and
    postconditions (what must be true after completion).
    """

    def __init__(self):
        self._goals: Dict[str, Goal] = {}

    def add_goal(self, description: str, parent_id: Optional[str] = None,
                 priority: int = 5,
                 preconditions: Optional[List[str]] = None,
                 postconditions: Optional[List[str]] = None) -> Goal:
        """Create and register a new goal."""
        goal = Goal(
            description=description,
            parent_id=parent_id,
            priority=priority,
            preconditions=preconditions or [],
            postconditions=postconditions or [],
        )
        self._goals[goal.goal_id] = goal

        if parent_id and parent_id in self._goals:
            self._goals[parent_id].subgoals.append(goal.goal_id)

        return goal

    def decompose(self, goal_id: str,
                  decompose_fn: Callable[[str], List[Dict[str, Any]]]
                  ) -> List[Goal]:
        """
        Decompose a goal into subgoals using a decomposition function.

        Parameters
        ----------
        goal_id : str
            The goal to decompose.
        decompose_fn : callable
            (goal_description) → [{"description": ..., "priority": ..., ...}]
        """
        goal = self._goals.get(goal_id)
        if not goal:
            return []

        sub_defs = decompose_fn(goal.description)
        subgoals = []
        for sub_def in sub_defs:
            sg = self.add_goal(
                description=sub_def.get("description", ""),
                parent_id=goal_id,
                priority=sub_def.get("priority", goal.priority),
                preconditions=sub_def.get("preconditions", []),
                postconditions=sub_def.get("postconditions", []),
            )
            subgoals.append(sg)

        return subgoals

    def get_actionable(self) -> List[Goal]:
        """Get goals that are ready to execute (preconditions met, no pending subgoals)."""
        actionable = []
        for goal in self._goals.values():
            if goal.status != GoalStatus.PENDING:
                continue
            # Check if all subgoals are completed
            if goal.subgoals:
                all_done = all(
                    self._goals[sg].status == GoalStatus.COMPLETED
                    for sg in goal.subgoals if sg in self._goals
                )
                if not all_done:
                    continue
            actionable.append(goal)

        actionable.sort(key=lambda g: g.priority, reverse=True)
        return actionable

    def complete_goal(self, goal_id: str, success: bool = True):
        """Mark a goal as completed or failed."""
        goal = self._goals.get(goal_id)
        if goal:
            goal.status = GoalStatus.COMPLETED if success else GoalStatus.FAILED
            goal.completed = datetime.now().isoformat(timespec="seconds")
            # Propagate: check if parent is now completable
            if goal.parent_id:
                self._check_parent_completion(goal.parent_id)

    def _check_parent_completion(self, parent_id: str):
        parent = self._goals.get(parent_id)
        if not parent or not parent.subgoals:
            return
        statuses = [
            self._goals[sg].status
            for sg in parent.subgoals if sg in self._goals
        ]
        if all(s == GoalStatus.COMPLETED for s in statuses):
            parent.status = GoalStatus.COMPLETED
            parent.completed = datetime.now().isoformat(timespec="seconds")

    def get_goal_tree(self, goal_id: Optional[str] = None) -> dict:
        """Get hierarchical view of goals."""
        if goal_id:
            return self._build_tree(goal_id)
        # Return all root goals
        roots = [g for g in self._goals.values() if g.parent_id is None]
        return {"roots": [self._build_tree(r.goal_id) for r in roots]}

    def _build_tree(self, goal_id: str) -> dict:
        goal = self._goals.get(goal_id)
        if not goal:
            return {}
        tree = goal.to_dict()
        tree["children"] = [self._build_tree(sg) for sg in goal.subgoals]
        return tree

    def to_dict(self) -> dict:
        return {gid: g.to_dict() for gid, g in self._goals.items()}


# ═══════════════════════════════════════════════════════════════════════
#  COGNITIVE MEMORY — Episodic + Semantic + Procedural
# ═══════════════════════════════════════════════════════════════════════

class CognitiveMemory:
    """
    Three-tier memory system inspired by human cognition:

    - Episodic: Specific events/experiences (what happened)
    - Semantic: Facts and concepts (what is known)
    - Procedural: Learned workflows (how to do things)

    Supports retrieval by relevance (keyword matching) and recency.
    """

    def __init__(self, agent_name: str, max_episodes: int = 1000):
        self.agent_name = agent_name
        self.max_episodes = max_episodes
        self._episodes: List[Episode] = []
        self._semantic: Dict[str, Any] = {}  # concept → value
        self._procedural: Dict[str, List[str]] = {}  # task_type → step list
        self._memory_file = MEMORY_DIR / f"{agent_name}_memory.json"
        self._load()

    def _load(self):
        if self._memory_file.exists():
            try:
                data = json.loads(self._memory_file.read_text(encoding="utf-8"))
                self._episodes = [
                    Episode(**ep) for ep in data.get("episodes", [])
                ]
                self._semantic = data.get("semantic", {})
                self._procedural = data.get("procedural", {})
            except (json.JSONDecodeError, TypeError):
                logger.warning("Could not load memory for %s", self.agent_name)

    def _save(self):
        data = {
            "agent": self.agent_name,
            "updated": datetime.now().isoformat(timespec="seconds"),
            "episodes": [ep.to_dict() for ep in self._episodes[-self.max_episodes:]],
            "semantic": self._semantic,
            "procedural": self._procedural,
        }
        self._memory_file.write_text(
            json.dumps(data, indent=2, default=str), encoding="utf-8"
        )

    # ── Episodic Memory ──────────────────────────────────────────────

    def store_episode(self, episode: Episode):
        """Store an episodic memory entry."""
        self._episodes.append(episode)
        if len(self._episodes) > self.max_episodes:
            self._episodes = self._episodes[-self.max_episodes:]
        self._save()

    def recall_recent(self, limit: int = 10) -> List[Episode]:
        """Recall most recent episodes."""
        return list(reversed(self._episodes[-limit:]))

    def recall_relevant(self, query: str, limit: int = 5) -> List[Episode]:
        """Recall episodes most relevant to a query (keyword matching)."""
        query_words = set(query.lower().split())
        scored = []
        for ep in self._episodes:
            ep_text = f"{ep.event} {ep.outcome} {ep.lesson or ''}".lower()
            ep_words = set(ep_text.split())
            overlap = len(query_words & ep_words)
            recency = 1.0 / (1 + (len(self._episodes) - self._episodes.index(ep)))
            score = (overlap * 2.0 + ep.importance + recency)
            if overlap > 0:
                scored.append((score, ep))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [ep for _, ep in scored[:limit]]

    def recall_failures(self, limit: int = 10) -> List[Episode]:
        """Recall failed episodes for learning."""
        failures = [ep for ep in self._episodes if not ep.success]
        return list(reversed(failures[-limit:]))

    # ── Semantic Memory ──────────────────────────────────────────────

    def store_fact(self, concept: str, value: Any):
        """Store a semantic fact (concept → value)."""
        self._semantic[concept] = {
            "value": value,
            "updated": datetime.now().isoformat(timespec="seconds"),
        }
        self._save()

    def recall_fact(self, concept: str) -> Optional[Any]:
        """Recall a semantic fact."""
        entry = self._semantic.get(concept)
        return entry["value"] if entry else None

    def search_facts(self, pattern: str) -> Dict[str, Any]:
        """Search semantic memory by key pattern."""
        return {
            k: v["value"] for k, v in self._semantic.items()
            if pattern.lower() in k.lower()
        }

    # ── Procedural Memory ────────────────────────────────────────────

    def store_procedure(self, task_type: str, steps: List[str]):
        """Store a learned procedure for a task type."""
        self._procedural[task_type] = steps
        self._save()

    def recall_procedure(self, task_type: str) -> Optional[List[str]]:
        """Recall a learned procedure."""
        return self._procedural.get(task_type)

    def list_procedures(self) -> List[str]:
        """List all known procedure types."""
        return list(self._procedural.keys())

    # ── Stats ────────────────────────────────────────────────────────

    def stats(self) -> dict:
        return {
            "agent": self.agent_name,
            "episodes": len(self._episodes),
            "facts": len(self._semantic),
            "procedures": len(self._procedural),
            "success_rate": (
                sum(1 for e in self._episodes if e.success) / len(self._episodes)
                if self._episodes else 0.0
            ),
        }


# ═══════════════════════════════════════════════════════════════════════
#  COGNITIVE AGENT — Full Brain/Perception/Action agent
# ═══════════════════════════════════════════════════════════════════════

class CognitiveAgent:
    """
    A fully cognitive agent implementing the Brain/Perception/Action
    architecture from modern agentic AI research.

    Brain: ReAct reasoning, Reflexion self-critique, goal decomposition
    Perception: State observation, environment sensing
    Action: Tool execution, inter-agent communication
    """

    def __init__(self, name: str, domains: Optional[List[str]] = None,
                 max_react_steps: int = 10,
                 confidence_threshold: float = 0.7):
        self.name = name
        self.domains = domains or []
        self.memory = CognitiveMemory(name)
        self.react = ReActLoop(max_steps=max_react_steps,
                               confidence_threshold=confidence_threshold)
        self.reflexion = ReflexionEngine(memory=self.memory)
        self.goals = GoalDecomposer()
        self._tools: Dict[str, Callable] = {}
        self._perceivers: Dict[str, Callable] = {}

    # ── Tool Registration ────────────────────────────────────────────

    def register_tool(self, name: str, fn: Callable,
                      description: str = ""):
        """Register an action tool for this agent."""
        self._tools[name] = fn

    def register_perceiver(self, name: str, fn: Callable):
        """Register a perception function for state observation."""
        self._perceivers[name] = fn

    # ── Core Reasoning ───────────────────────────────────────────────

    def reason_and_act(self, task: str,
                       think_fn: Optional[Callable] = None,
                       act_fn: Optional[Callable] = None,
                       observe_fn: Optional[Callable] = None) -> ReasoningTrace:
        """
        Execute a task using ReAct reasoning.

        Falls back to default implementations if custom functions not provided.
        """
        # Default think: use past episodes for context
        def default_think(task_desc: str, history: List[ReasoningStep]) -> str:
            past = self.memory.recall_relevant(task_desc, limit=3)
            lessons = [ep.lesson for ep in past if ep.lesson]
            context = f"Task: {task_desc}. "
            if lessons:
                context += f"Past lessons: {'; '.join(lessons)}. "
            if history:
                last = history[-1]
                context += f"Last step ({last.step_type.value}): {last.content[:100]}"
            return context

        # Default act: try matching tool
        def default_act(thought: str) -> dict:
            for tool_name, tool_fn in self._tools.items():
                if tool_name.lower() in thought.lower():
                    return {"tool": tool_name, "result": tool_fn(thought)}
            return {"tool": "none", "result": "No matching tool found"}

        # Default observe: summarize action result
        def default_observe(action_result: dict) -> str:
            return f"Tool '{action_result.get('tool', 'unknown')}' returned: {str(action_result.get('result', ''))[:200]}"

        trace = self.react.execute(
            task=task,
            think_fn=think_fn or default_think,
            act_fn=act_fn or default_act,
            observe_fn=observe_fn or default_observe,
        )

        return trace

    def reason_with_reflexion(self, task: str,
                              evaluate_fn: Optional[Callable] = None
                              ) -> ReasoningTrace:
        """Execute task with Reflexion — retries with self-critique on failure."""

        def default_evaluate(trace: ReasoningTrace) -> Dict[str, Any]:
            return {
                "success": trace.success,
                "quality": trace.avg_confidence,
                "issues": [] if trace.success else ["task_incomplete"],
            }

        def execute_with_lessons(task_desc: str,
                                 lessons: List[Episode]) -> ReasoningTrace:
            return self.reason_and_act(task_desc)

        return self.reflexion.reflect_and_retry(
            task=task,
            execute_fn=execute_with_lessons,
            evaluate_fn=evaluate_fn or default_evaluate,
        )

    # ── Perception ───────────────────────────────────────────────────

    def perceive(self) -> Dict[str, Any]:
        """Observe current state from all registered perceivers."""
        state = {}
        for name, perceiver in self._perceivers.items():
            try:
                state[name] = perceiver()
            except Exception as e:
                state[name] = {"error": str(e)}
        return state

    # ── Knowledge ────────────────────────────────────────────────────

    def learn(self, concept: str, value: Any):
        """Store a fact in semantic memory."""
        self.memory.store_fact(concept, value)

    def recall(self, concept: str) -> Optional[Any]:
        """Recall a fact from semantic memory."""
        return self.memory.recall_fact(concept)

    def learn_procedure(self, task_type: str, steps: List[str]):
        """Store a learned procedure."""
        self.memory.store_procedure(task_type, steps)

    # ── Status ───────────────────────────────────────────────────────

    def status(self) -> dict:
        """Get agent cognitive status."""
        return {
            "name": self.name,
            "domains": self.domains,
            "tools": list(self._tools.keys()),
            "perceivers": list(self._perceivers.keys()),
            "memory": self.memory.stats(),
            "goals": self.goals.to_dict(),
        }
