#!/usr/bin/env python3
"""
Agent Marketplace
Dynamic discovery and loading of council agents for runtime extensibility
"""

import importlib
import pkgutil
import logging
from pathlib import Path
from typing import Dict, Type

from inner_council.agents.base_agent import BaseCouncilAgent

logger = logging.getLogger(__name__)


class AgentMarketplace:
    """Marketplace that discovers and loads agent classes dynamically"""

    def __init__(self, agents_package: str = "inner_council.agents"):
        self.agents_package = agents_package
        self.registry: Dict[str, Type[BaseCouncilAgent]] = {}
        self.discover_agents()

    def discover_agents(self):
        """Scan the agents package for any agent classes and register them"""
        try:
            pkg = importlib.import_module(self.agents_package)
        except ImportError as e:
            logger.error(
                f"Unable to import agents package {self.agents_package}: {e}")
            return

        package_path = Path(pkg.__file__).parent
        for finder, name, ispkg in pkgutil.iter_modules([str(package_path)]):
            if name.endswith("_agent"):
                module_name = f"{self.agents_package}.{name}"
                try:
                    module = importlib.import_module(module_name)
                except Exception as exc:
                    logger.error(
                        f"Failed to import module {module_name}: {exc}")
                    continue

                for attr in dir(module):
                    obj = getattr(module, attr)
                    if isinstance(
                        obj, type) and issubclass(
                        obj, BaseCouncilAgent) and obj is not BaseCouncilAgent:
                        class_name = obj.__name__
                        logger.info(f"Discovered agent class: {class_name}")
                        self.registry[class_name] = obj

    def list_available_agents(self) -> list:
        """Return names of available agent classes"""
        return list(self.registry.keys())

    def create_agent(self, class_name: str, **kwargs) -> BaseCouncilAgent:
        """Instantiate an agent by class name"""
        cls = self.registry.get(class_name)
        if not cls:
            raise KeyError(
                f"Agent class {class_name} not found in marketplace")
        agent = cls(**kwargs)
        return agent


# single global marketplace instance for convenience
global_marketplace = AgentMarketplace()
