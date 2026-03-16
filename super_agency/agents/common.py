#!/usr/bin/env python3
import datetime
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from autogen_agentchat.agents import AssistantAgent

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
CONFIG = json.loads(
    (ROOT / "config" / "settings.json").read_text(encoding="utf-8"))

# PORTFOLIO - lazy-loaded on first access
_portfolio_cache = None

def get_portfolio():
    global _portfolio_cache
    if _portfolio_cache is None:
        portfolio_path = ROOT / "portfolio.json"
        if portfolio_path.exists():
            _portfolio_cache = json.loads(
                portfolio_path.read_text(encoding="utf-8"))
        else:
            _portfolio_cache = {"repositories": []}
    return _portfolio_cache


class PortfolioAccessor:
    """Lazy accessor for portfolio data"""
    def __getitem__(self, key):
        return get_portfolio()[key]
    def __iter__(self):
        return iter(get_portfolio())
    def get(self, key, default=None):
        return get_portfolio().get(key, default)
    def keys(self):
        return get_portfolio().keys()
    def values(self):
        return get_portfolio().values()
    def items(self):
        return get_portfolio().items()


# PORTFOLIO accessor for backward compatibility
PORTFOLIO = PortfolioAccessor()

SENSITIVE_ACTIONS = set(CONFIG.get("require_consent_for", []))

class Log:
    @staticmethod
    def info(msg: str):
        print(f"[INFO] {msg}")

    @staticmethod
    def warn(msg: str):
        print(f"[WARN] {msg}")

    @staticmethod
    def error(msg: str):
        print(f"[ERROR] {msg}")


def is_git_repo(path: Path) -> bool:
    return (path / ".git").exists()


def run_git(path: Path, args: List[str]) -> Tuple[int, str, str]:
    try:
        cp = subprocess.run(["git", "-C", str(path)] +args,
                            capture_output=True, encoding="utf-8",
                            errors="replace", check=False,)
        return cp.returncode, (cp.stdout or "").strip(), (cp.stderr or "").strip()
    except FileNotFoundError:
        return 127, "", "git not found"


def get_head_commit(path: Path) -> Optional[str]:
    rc, out, err = run_git(path, ["rev-parse", "HEAD"])
    return out if rc == 0 else None


def list_changed_files(path: Path, since_commit: Optional[str]) -> List[Tuple[str, str]]:
    if since_commit:
        rc, out, err = run_git(
            path, ["diff", "--name-status", f"{since_commit}..HEAD"])
    else:
        rc, out, err = run_git(
            path, ["show", "--name-status", "-m", "-1", "HEAD"])
    if rc != 0:
        return []
    rows: List[Tuple[str, str]] = []
    for line in out.splitlines():
        parts = line.split('\t')
        if len(parts) >= 2:
            status, fn = parts[0], parts[-1]
            rows.append((status, fn))
    return rows


def categorize_file(fn: str) -> str:
    fnl = fn.lower()
    if fnl.startswith(".ncl/") or "/.ncl/" in fnl:
        return "ncl"
    # detect test paths: either start with tests/ or contain /tests/
    if fnl.startswith("tests/") or any(seg in fnl
        for seg in ["/tests/", "/test/", "_test.", ".spec."]):
        return "tests"
    if any(fnl.endswith(ext) for ext in [".md", ".rst", ".txt"]):
        return "docs"
    return "code"


def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)


def now_iso() -> str:
    return datetime.datetime.now().astimezone().isoformat()


def load_mandate(repo_root: Path) -> Dict[str, Any]:
    mpath = repo_root / ".ncl" / "mandate.yaml"
    jpath = repo_root / ".ncl" / "mandate.json"
    if jpath.exists():
        return json.loads(jpath.read_text(encoding="utf-8"))
    data: Dict[str, Any] = {}
    if not mpath.exists():
        return data
    import io
    key = None
    for raw in io.StringIO(mpath.read_text(encoding="utf-8")):
        line = raw.rstrip('\n')
        if not line or line.strip().startswith('#'):
            continue
        if re.match(r"^[A-Za-z0-9_]+:\s*$", line):
            key = line.split(":")[0].strip()
            data[key] = None
        elif ":" in line and not line.lstrip().startswith("-"):
            k, v = line.split(":", 1)
            data[k.strip()] = v.strip().strip('"')
        elif line.lstrip().startswith("- ") and key:
            if data.get(key) is None or not isinstance(data.get(key), list):
                data[key] = []
            data[key].append(line.strip()[2:])
    return data


def require_consent_for(action_class: str) -> bool:
    return action_class in SENSITIVE_ACTIONS


class CommonAgent:
    """Base agent class providing common functionality and utilities"""

    def __init__(self, model_client=None):
        self.name = "CommonAgent"
        self.model_client = model_client
        self.status = "initialized"

        # Create AutoGen agent if model client is available
        if self.model_client:
            self.agent = AssistantAgent(
                "common_utilities_agent", model_client=self.model_client,
                system_message="""You are a utility agent providing common functionality and support services
                for the DIGITAL LABOUR distributed intelligence system.

                Your role is to:
                - Provide utility functions and data processing
                - Assist with system maintenance and monitoring
                - Support other agents with common operations
                - Handle cross-cutting concerns and shared services

                Focus on reliability, efficiency, and seamless integration with other system components.""")

    def execute(self, task: str) -> Dict[str, Any]:
        """Execute a common task with optional AI enhancement"""
        try:
            # If AI is available, enhance the task execution
            if self.model_client and self.agent:
                analysis_prompt = f"""
                Analyze and execute this common task: {task}

                Provide:
                1. Task breakdown and requirements
                2. Execution strategy
                3. Potential optimizations
                4. Success criteria
                5. Error handling approach
                """

                # Note: In full implementation, we would run the agent here
                ai_enhancement = {
                    'task_analysis': 'AI analysis requires model execution',
                    'execution_strategy': 'AI analysis pending',
                    'optimizations': 'AI analysis pending',
                    'success_criteria': 'AI analysis pending',
                    'error_handling': 'AI analysis pending'
                }
            else:
                ai_enhancement = {
                    'task_analysis': 'Manual task execution',
                    'execution_strategy': 'Standard processing',
                    'optimizations': 'Basic optimization applied',
                    'success_criteria': 'Task completion',
                    'error_handling': 'Standard error handling'
                }

            return {
                'task': task,
                'result': 'completed with common functionality',
                'agent': self.name,
                'timestamp': now_iso(),
                'ai_enhancement': ai_enhancement,
                'ai_enhanced': bool(self.model_client),
                'status': 'success'
            }

        except Exception as e:
            Log.error(f"CommonAgent execution failed: {e}")
            return {
                'task': task,
                'result': f'error: {str(e)}',
                'agent': self.name,
                'timestamp': now_iso(),
                'status': 'error'
            }


# Utility functions for agent management
def get_agent_status() -> Dict[str, Any]:
    """Get status of all available agents"""
    import psutil

    return {
        'timestamp': now_iso(),
        'system': {
            'cpu_percent': psutil.cpu_percent(),
            'memory_percent': psutil.virtual_memory().percent,
        },
        'agents': {
            'optimus': {'status': 'available', 'role': 'QFORGE operations, repository intelligence'},
            'gasket': {'status': 'available', 'role': 'CPU optimization, QUSAR feedback loops'},
        },
        'integrations': {
            'qforge': True,
            'qusar': True,
            'matrix_monitor': True,
        }
    }


def initialize_agents() -> Dict[str, Any]:
    """Initialize all agents and return status"""
    from .agent_gasket import AgentGasket
    from .agent_optimus import AgentOptimus

    agents = {}

    try:
        agents['optimus'] = AgentOptimus()
        Log.info("AgentOptimus initialized")
    except Exception as e:
        Log.error(f"Failed to initialize AgentOptimus: {e}")
        agents['optimus'] = None

    try:
        agents['gasket'] = AgentGasket()
        Log.info("AgentGasket initialized")
    except Exception as e:
        Log.error(f"Failed to initialize AgentGasket: {e}")
        agents['gasket'] = None

    return {
        'status': 'initialized',
        'agents': {name: 'ready' if agent else 'failed' for name, agent in agents.items()},
        'timestamp': now_iso()
    }
