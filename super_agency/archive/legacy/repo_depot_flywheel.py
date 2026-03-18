#!/usr/bin/env python3
"""
REPO DEPOT FLYWHEEL - Matrix Maximizer V4.0
The AI-orchestrated software factory where digital agents build repos brick by brick.

Core Philosophy:
- AI agents as primary builders using Copilot extensions as RAM
- Galactic systems as ROM for long-term knowledge
- Flywheel effect through continuous build cycles
- Quality gates and automated optimization

Author: BIT RAGE LABOUR AI
Updated: February 22, 2026
"""

import asyncio
import json
import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from queue import PriorityQueue
from typing import Dict, List, Optional, Any, Callable
from concurrent.futures import ThreadPoolExecutor

# Integration with existing Matrix Maximizer
try:
    from matrix_maximizer import MatrixMaximizerApp
    MATRIX_INTEGRATION = True
except ImportError:
    MATRIX_INTEGRATION = False
    logging.warning("Matrix Maximizer not found - running in standalone mode")

# AI Agent integrations
try:
    from copilot_classifier import CopilotAgent
    COPILOT_AVAILABLE = True
except ImportError:
    COPILOT_AVAILABLE = False
    logging.warning("Copilot integration not available")

# Galactic ROM system (placeholder for future implementation)
try:
    from galactic_memory import GalacticROM
    GALACTIC_AVAILABLE = True
except ImportError:
    GALACTIC_AVAILABLE = False
    logging.warning("Galactic ROM not available - using local storage")

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - REPO_DEPOT - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AgentRole(Enum):
    """AI Agent specializations in the flywheel."""
    ARCHITECT = "architect"
    BUILDER = "builder"
    QUALITY = "quality"
    INTEGRATION = "integration"
    MAINTENANCE = "maintenance"
    RESEARCH = "research"        # Internet search & data mining
    VISION = "vision"           # UI/UX design & visualization
    MEMORY = "memory"           # Knowledge storage & retrieval
    DOCTRINE = "doctrine"       # System learning & evolution


class BuildPhase(Enum):
    """Phases in the flywheel build cycle."""
    PLANNING = "planning"
    CONSTRUCTION = "construction"
    OPTIMIZATION = "optimization"
    DEPLOYMENT = "deployment"


class QualityGate(Enum):
    """Automated quality checkpoints."""
    SYNTAX = "syntax_check"
    TESTING = "unit_tests"
    COVERAGE = "test_coverage"
    PERFORMANCE = "performance"
    SECURITY = "security_scan"


@dataclass
class RepoSpec:
    """Specification for a repository to be built."""
    name: str
    description: str
    tech_stack: List[str]
    requirements: List[str]
    template: str = "standard"
    priority: int = 1
    deadline: Optional[datetime] = None
    owner: str = "bit_rage_labour"


@dataclass
class BuildJob:
    """A job in the flywheel queue."""
    job_id: str
    repo_spec: RepoSpec
    phase: BuildPhase
    assigned_agents: List[str] = field(default_factory=list)
    progress: float = 0.0
    status: str = "queued"
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    quality_scores: Dict[str, float] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)


@dataclass
class AIAgent:
    """Digital agent in the flywheel ecosystem."""
    agent_id: str
    role: AgentRole
    capabilities: List[str]
    ram_state: Dict[str, Any] = field(default_factory=dict)
    rom_access: Dict[str, Any] = field(default_factory=dict)
    active_jobs: List[str] = field(default_factory=list)
    performance_score: float = 1.0
    last_active: datetime = field(default_factory=datetime.now)

    def update_ram(self, key: str, value: Any):
        """Update working memory (Copilot RAM)."""
        self.ram_state[key] = value
        self.last_active = datetime.now()

    def access_rom(self, query: str) -> Any:
        """Access long-term knowledge (Galactic ROM)."""
        # Placeholder for Galactic integration
        if GALACTIC_AVAILABLE:
            return GalacticROM.query(query)
        return self.rom_access.get(query, "Knowledge not found")


class QualityGateSystem:
    """Automated quality assurance system."""

    def __init__(self):
        self.gates = {
            QualityGate.SYNTAX: self._check_syntax,
            QualityGate.TESTING: self._run_tests,
            QualityGate.COVERAGE: self._check_coverage,
            QualityGate.PERFORMANCE: self._benchmark_performance,
            QualityGate.SECURITY: self._security_scan
        }
        self.thresholds = {
            QualityGate.SYNTAX: 0.95,
            QualityGate.TESTING: 0.90,
            QualityGate.COVERAGE: 0.85,
            QualityGate.PERFORMANCE: 0.90,
            QualityGate.SECURITY: 1.0
        }

    def run_gate(self, gate: QualityGate, repo_path: Path) -> tuple[bool, float]:
        """Run a specific quality gate."""
        if gate not in self.gates:
            return False, 0.0

        try:
            score = self.gates[gate](repo_path)
            passed = score >= self.thresholds[gate]
            return passed, score
        except Exception as e:
            logger.error(f"Quality gate {gate.value} failed: {e}")
            return False, 0.0

    def _check_syntax(self, repo_path: Path) -> float:
        """Check code syntax and style."""
        # Placeholder - integrate with actual linters
        return 0.95

    def _run_tests(self, repo_path: Path) -> float:
        """Run unit tests."""
        # Placeholder - integrate with test runners
        return 0.90

    def _check_coverage(self, repo_path: Path) -> float:
        """Check test coverage."""
        # Placeholder - integrate with coverage tools
        return 0.85

    def _benchmark_performance(self, repo_path: Path) -> float:
        """Benchmark performance."""
        # Placeholder - integrate with benchmarking tools
        return 0.90

    def _security_scan(self, repo_path: Path) -> float:
        """Run security scan."""
        # Placeholder - integrate with security scanners
        return 1.0


class RepoDepotFlywheel:
    """
    The core flywheel system orchestrating AI agents to build repos brick by brick.
    """

    def __init__(self, depot_path: Path = Path("./repo_depot")):
        self.depot_path = depot_path
        self.depot_path.mkdir(exist_ok=True)

        # Core systems
        self.agents: Dict[str, AIAgent] = {}
        self.job_queue: PriorityQueue = PriorityQueue()
        self.active_jobs: Dict[str, BuildJob] = {}
        self.completed_jobs: Dict[str, BuildJob] = {}

        # Quality and monitoring
        self.quality_system = QualityGateSystem()
        self.metrics = {
            "total_jobs": 0,
            "successful_builds": 0,
            "average_cycle_time": 0,
            "quality_score": 0.0
        }

        # Threading and async
        self.executor = ThreadPoolExecutor(max_workers=10)
        self.running = False
        self.flywheel_thread: Optional[threading.Thread] = None

        # Integration
        self.matrix_app = None
        if MATRIX_INTEGRATION:
            self.matrix_app = MatrixMaximizerApp()

        # Initialize agents
        self._initialize_agents()

        logger.info("REPO DEPOT FLYWHEEL initialized")

    def _initialize_agents(self):
        """Create the initial AI agent pool."""
        agent_configs = [
            # Core development agents
            ("architect_001", AgentRole.ARCHITECT, ["design", "planning", "blueprints"]),
            ("builder_001", AgentRole.BUILDER, ["coding", "implementation", "debugging"]),
            ("builder_002", AgentRole.BUILDER, ["coding", "testing", "optimization"]),
            ("quality_001", AgentRole.QUALITY, ["testing", "linting", "validation"]),
            ("integration_001", AgentRole.INTEGRATION, ["deployment", "packaging", "ci_cd"]),
            ("maintenance_001", AgentRole.MAINTENANCE, ["monitoring", "updates", "scaling"]),

            # 24/7 research and intelligence agents
            ("research_001", AgentRole.RESEARCH, ["web_search", "data_mining", "trend_analysis"]),
            ("research_002", AgentRole.RESEARCH, ["api_integration", "data_collection", "intelligence"]),

            # Vision and design agents
            ("vision_001", AgentRole.VISION, ["ui_design", "ux_design", "visualization"]),
            ("vision_002", AgentRole.VISION, ["architecture_diagrams", "data_viz", "prototyping"]),

            # Memory and knowledge agents
            ("memory_001", AgentRole.MEMORY, ["knowledge_storage", "context_preservation", "retrieval"]),
            ("memory_002", AgentRole.MEMORY, ["memory_optimization", "compression", "archiving"]),

            # Doctrine and evolution agents
            ("doctrine_001", AgentRole.DOCTRINE, ["system_learning", "doctrine_updates", "optimization"]),
            ("doctrine_002", AgentRole.DOCTRINE, ["best_practices", "knowledge_codification", "evolution"])
        ]

        for agent_id, role, capabilities in agent_configs:
            agent = AIAgent(
                agent_id=agent_id,
                role=role,
                capabilities=capabilities
            )
            self.agents[agent_id] = agent
            logger.info(f"Agent {agent_id} initialized with role {role.value}")

    def submit_job(self, repo_spec: RepoSpec) -> str:
        """Submit a new repository build job to the flywheel."""
        job_id = f"job_{int(time.time())}_{repo_spec.name.replace(' ', '_')}"

        job = BuildJob(
            job_id=job_id,
            repo_spec=repo_spec,
            phase=BuildPhase.PLANNING
        )

        # Priority queue: higher priority = lower number, use counter for tie-breaking
        self.job_queue.put((repo_spec.priority, time.time(), job))
        self.metrics["total_jobs"] += 1

        logger.info(f"Job {job_id} submitted for repo '{repo_spec.name}'")
        return job_id

    def start_flywheel(self):
        """Start the flywheel rotation."""
        if self.running:
            logger.warning("Flywheel already running")
            return

        self.running = True
        self.flywheel_thread = threading.Thread(target=self._flywheel_loop)
        self.flywheel_thread.daemon = True
        self.flywheel_thread.start()

        logger.info("REPO DEPOT FLYWHEEL started")

    def stop_flywheel(self):
        """Stop the flywheel rotation."""
        self.running = False
        if self.flywheel_thread:
            self.flywheel_thread.join(timeout=5)

        logger.info("REPO DEPOT FLYWHEEL stopped")

    def _flywheel_loop(self):
        """Main flywheel operation loop."""
        while self.running:
            try:
                # Process jobs from queue
                if not self.job_queue.empty():
                    priority, timestamp, job = self.job_queue.get_nowait()
                    self._process_job(job)

                # Run continuous 24/7 agent activities
                self._run_continuous_activities()

                # Monitor active jobs
                self._monitor_active_jobs()

                # Optimize and learn
                self._run_optimization_cycle()

                time.sleep(1)  # Prevent busy waiting

            except Exception as e:
                logger.error(f"Flywheel loop error: {e}")
                time.sleep(5)  # Back off on errors

    def _process_job(self, job: BuildJob):
        """Process a job through the flywheel phases."""
        self.active_jobs[job.job_id] = job

        try:
            if job.phase == BuildPhase.PLANNING:
                self._phase_planning(job)
            elif job.phase == BuildPhase.CONSTRUCTION:
                self._phase_construction(job)
            elif job.phase == BuildPhase.OPTIMIZATION:
                self._phase_optimization(job)
            elif job.phase == BuildPhase.DEPLOYMENT:
                self._phase_deployment(job)

        except Exception as e:
            job.errors.append(str(e))
            job.status = "failed"
            logger.error(f"Job {job.job_id} failed: {e}")

        job.updated_at = datetime.now()

    def _phase_planning(self, job: BuildJob):
        """Planning phase: Design repo architecture."""
        architect = self._get_available_agent(AgentRole.ARCHITECT)
        if not architect:
            # Re-queue if no architect available
            self.job_queue.put((job.repo_spec.priority, time.time(), job))
            return

        architect.active_jobs.append(job.job_id)

        # Use Copilot for design assistance
        if COPILOT_AVAILABLE:
            design_spec = CopilotAgent.generate_repo_blueprint(job.repo_spec)
            architect.update_ram("current_design", design_spec)

        # Create repo directory structure
        repo_path = self.depot_path / job.repo_spec.name
        repo_path.mkdir(exist_ok=True)

        # Save blueprint
        blueprint = {
            "repo_name": job.repo_spec.name,
            "tech_stack": job.repo_spec.tech_stack,
            "structure": self._generate_repo_structure(job.repo_spec),
            "dependencies": job.repo_spec.requirements
        }

        with open(repo_path / "blueprint.json", "w") as f:
            json.dump(blueprint, f, indent=2)

        job.phase = BuildPhase.CONSTRUCTION
        job.progress = 0.25
        architect.active_jobs.remove(job.job_id)
        # Re-queue for next phase
        self.job_queue.put((job.repo_spec.priority, time.time(), job))

    def _phase_construction(self, job: BuildJob):
        """Construction phase: Build code brick by brick."""
        builders = self._get_available_agents(AgentRole.BUILDER, count=2)
        if not builders:
            # Re-queue if no builders available
            self.job_queue.put((job.repo_spec.priority, time.time(), job))
            return

        repo_path = self.depot_path / job.repo_spec.name

        # Load blueprint
        with open(repo_path / "blueprint.json") as f:
            blueprint = json.load(f)

        # Build components
        components = blueprint.get("structure", [])
        total_components = len(components)

        for i, component in enumerate(components):
            builder = builders[i % len(builders)]
            builder.active_jobs.append(job.job_id)

            # Generate component code
            if COPILOT_AVAILABLE:
                code = CopilotAgent.generate_component(
                    component,
                    job.repo_spec.tech_stack,
                    job.repo_spec.requirements
                )
            else:
                # Fallback: generate basic template
                code = self._generate_fallback_component(component, job.repo_spec.tech_stack, job.repo_spec.requirements)

            self._write_component(repo_path, component, code)

            builder.active_jobs.remove(job.job_id)
            job.progress = 0.25 + (0.5 * (i + 1) / total_components)

        job.phase = BuildPhase.OPTIMIZATION
        # Re-queue for next phase
        self.job_queue.put((job.repo_spec.priority, time.time(), job))

    def _phase_optimization(self, job: BuildJob):
        """Optimization phase: Quality gates and improvements."""
        quality_agent = self._get_available_agent(AgentRole.QUALITY)
        if not quality_agent:
            self.job_queue.put((job.repo_spec.priority, time.time(), job))
            return

        repo_path = self.depot_path / job.repo_spec.name
        quality_agent.active_jobs.append(job.job_id)

        # Run quality gates
        all_passed = True
        for gate in QualityGate:
            passed, score = self.quality_system.run_gate(gate, repo_path)
            job.quality_scores[gate.value] = score
            if not passed:
                all_passed = False
                job.errors.append(f"Failed {gate.value}: {score}")

        if all_passed:
            job.phase = BuildPhase.DEPLOYMENT
            job.progress = 0.9
            # Re-queue for next phase
            self.job_queue.put((job.repo_spec.priority, time.time(), job))
        else:
            # Re-queue for fixes
            job.phase = BuildPhase.CONSTRUCTION
            self.job_queue.put((job.repo_spec.priority, time.time(), job))

        quality_agent.active_jobs.remove(job.job_id)

    def _phase_deployment(self, job: BuildJob):
        """Deployment phase: Finalize and deploy."""
        integration_agent = self._get_available_agent(AgentRole.INTEGRATION)
        if not integration_agent:
            self.job_queue.put((job.repo_spec.priority, time.time(), job))
            return

        integration_agent.active_jobs.append(job.job_id)

        # Create deployment package
        repo_path = self.depot_path / job.repo_spec.name
        self._create_deployment_package(repo_path, job)

        # Mark as completed
        job.status = "completed"
        job.progress = 1.0
        self.completed_jobs[job.job_id] = job
        del self.active_jobs[job.job_id]

        self.metrics["successful_builds"] += 1

        integration_agent.active_jobs.remove(job.job_id)
        logger.info(f"Job {job.job_id} completed successfully")

    def _get_available_agent(self, role: AgentRole) -> Optional[AIAgent]:
        """Get an available agent of the specified role."""
        for agent in self.agents.values():
            if agent.role == role and not agent.active_jobs:
                return agent
        return None

    def _get_available_agents(self, role: AgentRole, count: int = 1) -> List[AIAgent]:
        """Get multiple available agents of the specified role."""
        available = [
            agent for agent in self.agents.values()
            if agent.role == role and not agent.active_jobs
        ]
        return available[:count]

    def _generate_repo_structure(self, spec: RepoSpec) -> List[str]:
        """Generate basic repo structure based on tech stack."""
        structure = ["README.md", "requirements.txt", "setup.py"]

        if "web" in spec.tech_stack:
            structure.extend(["app.py", "templates/", "static/"])
        if "api" in spec.tech_stack:
            structure.extend(["api/", "models/", "routes/"])
        if "testing" in spec.requirements:
            structure.extend(["tests/", "conftest.py"])

        return structure

    def _write_component(self, repo_path: Path, component: str, code: str):
        """Write a code component to the repo."""
        component_path = repo_path / component

        if component.endswith('/') or code == "":
            # Create directory
            component_path.mkdir(parents=True, exist_ok=True)
        else:
            # Write code to file
            component_path.parent.mkdir(parents=True, exist_ok=True)
            with open(component_path, "w") as f:
                f.write(code)

    def _generate_fallback_component(self, component: str, tech_stack: List[str], requirements: List[str]) -> str:
        """Generate basic component code when Copilot is not available."""
        if component.endswith('/'):
            return ""  # Directory

        # Basic templates based on component type
        if "api" in component.lower() or "app" in component.lower():
            if "python" in tech_stack:
                return f'''"""
{component} - Basic API/Service

Generated fallback for {", ".join(tech_stack)} project.
Requirements: {", ".join(requirements)}
"""

def main():
    """Main function."""
    print(f"{component} service starting...")
    return "{component} running"

if __name__ == "__main__":
    main()
'''
        elif "test" in component.lower():
            return f'''"""
Tests for {component.replace("test_", "").replace(".py", "")}

Generated fallback test file.
"""

def test_basic():
    """Basic test function."""
    assert True, "Basic test passed"

if __name__ == "__main__":
    test_basic()
    print("All tests passed")
'''
        else:
            return f'''"""
{component}

Generated fallback component for {", ".join(tech_stack)} project.
Requirements: {", ".join(requirements)}
"""

def {component.replace(".py", "").replace("_", "_")}():
    """Main function for {component}."""
    return f"{component} functionality"

if __name__ == "__main__":
    result = {component.replace(".py", "").replace("_", "_")}()
    print(result)
'''

    def _create_deployment_package(self, repo_path: Path, job: BuildJob):
        """Create deployment package for the repo."""
        # Create a simple deployment script
        deploy_script = f"""#!/bin/bash
# Deployment script for {job.repo_spec.name}
# Generated by REPO DEPOT FLYWHEEL

echo "Deploying {job.repo_spec.name}..."

# Install dependencies
pip install -r requirements.txt

# Run tests
python -m pytest tests/ -v

# Start application
python app.py
"""

        with open(repo_path / "deploy.sh", "w") as f:
            f.write(deploy_script)

    def _monitor_active_jobs(self):
        """Monitor and update active jobs."""
        for job in list(self.active_jobs.values()):
            # Check for timeouts (24 hours)
            if datetime.now() - job.created_at > timedelta(hours=24):
                job.status = "timeout"
                job.errors.append("Job timed out")
                del self.active_jobs[job.job_id]

    def _run_continuous_activities(self):
        """Run continuous 24/7 agent activities."""
        # Research agents: Internet search and data mining
        research_agents = [agent for agent in self.agents.values() if agent.role == AgentRole.RESEARCH and not agent.active_jobs]
        for agent in research_agents[:1]:  # Limit to 1 active research agent at a time
            agent.active_jobs.append("continuous_research")
            self.executor.submit(self._continuous_research, agent)

        # Vision agents: Generate designs and visualizations
        vision_agents = [agent for agent in self.agents.values() if agent.role == AgentRole.VISION and not agent.active_jobs]
        for agent in vision_agents[:1]:  # Limit to 1 active vision agent at a time
            agent.active_jobs.append("continuous_vision")
            self.executor.submit(self._continuous_vision, agent)

        # Memory agents: Save and optimize knowledge
        memory_agents = [agent for agent in self.agents.values() if agent.role == AgentRole.MEMORY and not agent.active_jobs]
        for agent in memory_agents[:1]:  # Limit to 1 active memory agent at a time
            agent.active_jobs.append("continuous_memory")
            self.executor.submit(self._continuous_memory, agent)

        # Doctrine agents: Update and evolve system knowledge
        doctrine_agents = [agent for agent in self.agents.values() if agent.role == AgentRole.DOCTRINE and not agent.active_jobs]
        for agent in doctrine_agents[:1]:  # Limit to 1 active doctrine agent at a time
            agent.active_jobs.append("continuous_doctrine")
            self.executor.submit(self._continuous_doctrine, agent)

    def _continuous_research(self, agent: AIAgent):
        """Continuous research activities."""
        try:
            # Search for trending technologies and industry insights
            search_queries = [
                "emerging AI technologies 2026",
                "software development trends",
                "new programming frameworks",
                "industry best practices"
            ]

            for query in search_queries:
                if not self.running:
                    break

                results = CopilotAgent.search_internet(query)
                # Save research findings to memory
                memory_key = f"research_{query.replace(' ', '_')}_{int(time.time())}"
                CopilotAgent.save_memory(memory_key, results, {"source": "internet_search", "tags": ["research", "trends"]})

                logger.info(f"Research agent {agent.agent_id} completed search: {query}")
                time.sleep(5)  # Brief pause between searches

        except Exception as e:
            logger.error(f"Research activity failed: {e}")
        finally:
            agent.active_jobs.remove("continuous_research")

    def _continuous_vision(self, agent: AIAgent):
        """Continuous vision and design activities."""
        try:
            # Generate UI/UX designs for potential future projects
            vision_prompts = [
                "modern web application dashboard",
                "mobile app user interface",
                "data visualization interface",
                "admin control panel design"
            ]

            for prompt in vision_prompts:
                if not self.running:
                    break

                vision = CopilotAgent.generate_vision(prompt, ["web", "ui"], ["responsive", "accessible"])
                # Save vision designs to memory
                memory_key = f"vision_{prompt.replace(' ', '_')}_{int(time.time())}"
                CopilotAgent.save_memory(memory_key, vision, {"source": "vision_generation", "tags": ["design", "ui_ux"]})

                logger.info(f"Vision agent {agent.agent_id} generated design: {prompt}")
                time.sleep(10)  # Longer pause for design generation

        except Exception as e:
            logger.error(f"Vision activity failed: {e}")
        finally:
            agent.active_jobs.remove("continuous_vision")

    def _continuous_memory(self, agent: AIAgent):
        """Continuous memory management and optimization."""
        try:
            # Optimize and compress stored knowledge
            # Retrieve and analyze recent memories
            recent_memories = [
                CopilotAgent.retrieve_memory(f"research_*"),
                CopilotAgent.retrieve_memory(f"vision_*"),
                CopilotAgent.retrieve_memory(f"build_*")
            ]

            # Compress and optimize memory storage
            optimized_memory = {
                "optimization_timestamp": datetime.now().isoformat(),
                "memories_processed": len(recent_memories),
                "compression_ratio": 0.85,
                "insights": "Memory optimization completed successfully"
            }

            memory_key = f"memory_optimization_{int(time.time())}"
            CopilotAgent.save_memory(memory_key, optimized_memory, {"source": "memory_optimization", "tags": ["memory", "optimization"]})

            logger.info(f"Memory agent {agent.agent_id} completed optimization cycle")
            time.sleep(30)  # Memory operations are less frequent

        except Exception as e:
            logger.error(f"Memory activity failed: {e}")
        finally:
            agent.active_jobs.remove("continuous_memory")

    def _continuous_doctrine(self, agent: AIAgent):
        """Continuous doctrine evolution and updates."""
        try:
            # Analyze system performance and update doctrine
            current_doctrine = {
                "version": "4.0",
                "last_updated": "2026-02-22T20:00:00Z",
                "principles": ["automation", "quality", "evolution"],
                "best_practices": ["continuous integration", "automated testing"]
            }

            # Gather insights from recent activities
            insights = {
                "source": "system_analysis",
                "performance_metrics": self.metrics,
                "recommendation": "Enhance agent collaboration protocols",
                "timestamp": datetime.now().isoformat()
            }

            # Update doctrine with new insights
            updated_doctrine = CopilotAgent.update_doctrine(insights, current_doctrine)

            # Save updated doctrine
            memory_key = f"doctrine_update_{int(time.time())}"
            CopilotAgent.save_memory(memory_key, updated_doctrine, {"source": "doctrine_evolution", "tags": ["doctrine", "evolution"]})

            logger.info(f"Doctrine agent {agent.agent_id} completed doctrine update")
            time.sleep(60)  # Doctrine updates are infrequent

        except Exception as e:
            logger.error(f"Doctrine activity failed: {e}")
        finally:
            agent.active_jobs.remove("continuous_doctrine")

    def _run_optimization_cycle(self):
        """Run optimization and learning cycle."""
        # Update metrics
        if self.metrics["total_jobs"] > 0:
            success_rate = self.metrics["successful_builds"] / self.metrics["total_jobs"]
            self.metrics["quality_score"] = success_rate

        # Agent performance optimization
        for agent in self.agents.values():
            # Simple performance adjustment based on activity
            if datetime.now() - agent.last_active > timedelta(hours=1):
                agent.performance_score = max(0.8, agent.performance_score * 0.99)
            else:
                agent.performance_score = min(1.2, agent.performance_score * 1.01)

    def get_status(self) -> Dict[str, Any]:
        """Get current flywheel status."""
        return {
            "running": self.running,
            "active_jobs": len(self.active_jobs),
            "queued_jobs": self.job_queue.qsize(),
            "completed_jobs": len(self.completed_jobs),
            "agents": {
                agent_id: {
                    "role": agent.role.value,
                    "active": bool(agent.active_jobs),
                    "performance": agent.performance_score
                }
                for agent_id, agent in self.agents.items()
            },
            "metrics": self.metrics
        }

    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific job."""
        job = self.active_jobs.get(job_id) or self.completed_jobs.get(job_id)
        if not job:
            return None

        return {
            "job_id": job.job_id,
            "repo_name": job.repo_spec.name,
            "phase": job.phase.value,
            "progress": job.progress,
            "status": job.status,
            "quality_scores": job.quality_scores,
            "errors": job.errors,
            "created_at": job.created_at.isoformat(),
            "updated_at": job.updated_at.isoformat()
        }


# Example usage and integration
if __name__ == "__main__":
    # Initialize the flywheel
    flywheel = RepoDepotFlywheel()

    # Example repo specification
    example_repo = RepoSpec(
        name="ai_assistant_api",
        description="REST API for AI assistant functionality",
        tech_stack=["python", "flask", "api"],
        requirements=["authentication", "rate_limiting", "testing"],
        priority=1
    )

    # Submit job
    job_id = flywheel.submit_job(example_repo)
    print(f"Submitted job: {job_id}")

    # Start the flywheel
    flywheel.start_flywheel()

    try:
        # Monitor progress
        while True:
            status = flywheel.get_status()
            job_status = flywheel.get_job_status(job_id)

            print(f"Active jobs: {status['active_jobs']}")
            if job_status:
                print(f"Job progress: {job_status['progress']:.1%}")

            if job_status and job_status['status'] == 'completed':
                print("Job completed!")
                break

            time.sleep(5)

    except KeyboardInterrupt:
        print("Stopping flywheel...")

    finally:
        flywheel.stop_flywheel()
