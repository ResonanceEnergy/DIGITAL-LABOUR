#!/usr/bin/env python3
"""
QUSAR - Quantum QUSAR Orchestration Layer
Feedback loops, goal formulation, and high-level coordination
"""

from .qusar_orchestrator import FeedbackLoopManager, GoalFormulator, QUSAROrchestrator

__all__ = [
    'FeedbackLoopManager',
    'GoalFormulator',
    'QUSAROrchestrator',
]

__version__ = '2.0.0'
__author__ = 'DIGITAL LABOUR'
