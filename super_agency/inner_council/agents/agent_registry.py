#!/usr/bin/env python3
"""
Inner Council Agent Registry
Central registry for all council member agents
"""

from typing import Dict, Type, Any
import importlib

# Agent registry
AGENT_REGISTRY = {}

def register_agent(agent_class: Type[Any]):
    """Register an agent class"""
    agent_name = agent_class.__name__.replace("Agent", "").lower()
    AGENT_REGISTRY[agent_name] = agent_class

def get_agent_class(agent_name: str) -> Type[Any]:
    """Get agent class by name"""
    return AGENT_REGISTRY.get(agent_name.lower())

def create_all_agents() -> Dict[str, Any]:
    """Create instances of all registered agents"""
    agents = {}
    for name, agent_class in AGENT_REGISTRY.items():
        try:
            agent = agent_class()
            agents[name] = agent
        except Exception as e:
            print(f"Error creating agent {name}: {e}")
    return agents

# Dynamic import of agent modules
import pkgutil, importlib
from pathlib import Path

from inner_council.agents.base_agent import BaseCouncilAgent


def discover_and_register_agents(package: str = "inner_council.agents"):
    """Discover agent classes in the given package and register them"""
    try:
        pkg = importlib.import_module(package)
    except ImportError:
        return
    package_path = Path(pkg.__file__).parent
    for finder, name, ispkg in pkgutil.iter_modules([str(package_path)]):
        if name.endswith("_agent"):
            module_name = f"{package}.{name}"
            try:
                module = importlib.import_module(module_name)
            except Exception:
                continue
            for attr in dir(module):
                obj = getattr(module, attr)
                if isinstance(
                    obj, type) and issubclass(
                    obj, BaseCouncilAgent) and obj is not BaseCouncilAgent:
                    register_agent(obj)


# run discovery at import time
discover_and_register_agents()

# ensure the meta coordinator is always available
try:
    from meta_coordinator import MetaCoordinator
    register_agent(MetaCoordinator)
except ImportError:
    pass
