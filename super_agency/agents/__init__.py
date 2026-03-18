#!/usr/bin/env python3
"""
BIT RAGE LABOUR Agents Module
Core AI agents for system orchestration and management
OpenClaw Gateway integration via GASKET-OpenClaw Bridge + System-Wide Bridge
"""

from .agent_gasket import AgentGasket

# Core Agents
from .agent_optimus import AgentOptimus

# OpenClaw Bridges
try:
    from .gasket_openclaw_bridge import GasketOpenClawBridge
except ImportError:
    GasketOpenClawBridge = None

try:
    from .openclaw_system_bridge import OpenClawSystemBridge
except ImportError:
    OpenClawSystemBridge = None

# Executive Council Agents
from .ceo_agent import CEOAgent
from .cfo_agent import CFOAgent
from .cio_agent import CIOAgent
from .cmo_agent import CMOAgent

# Utilities
from .common import get_agent_status, initialize_agents
from .council import CouncilAgent
from .cto_agent import CTOAgent
from .executive_council_orchestrator import ExecutiveCouncilOrchestrator

__all__ = [
    # Core Agents
    'AgentOptimus',
    'AgentGasket',
    # OpenClaw Bridges
    'GasketOpenClawBridge',
    'OpenClawSystemBridge',
    # Executive Council
    'CEOAgent',
    'CFOAgent',
    'CTOAgent',
    'CIOAgent',
    'CMOAgent',
    # Orchestration
    'ExecutiveCouncilOrchestrator',
    'CouncilAgent',
    # Utilities
    'get_agent_status',
    'initialize_agents',
]

__version__ = '3.1.0'
__author__ = 'BIT RAGE LABOUR'
