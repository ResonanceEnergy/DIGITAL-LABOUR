#!/usr/bin/env python3
"""
QFORGE - Quantum Forge Execution Layer
High-performance task execution, tool integration, and result aggregation
"""

from .qforge_executor import (
    ExecutionTask,
    PerformanceMonitor,
    QFORGEExecutor,
    TaskExecutor,
)

__all__ = [
    'TaskExecutor',
    'ExecutionTask',
    'QFORGEExecutor',
    'PerformanceMonitor',
]

__version__ = '2.0.0'
__author__ = 'Bit Rage Systems'
