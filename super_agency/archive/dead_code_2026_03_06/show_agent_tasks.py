#!/usr/bin/env python3
"""Show last 50 tasks for each agent"""

import json
from pathlib import Path

WORKSPACE = Path(__file__).parent

# Load portfolio
with open(WORKSPACE / 'portfolio.json') as f:
    portfolio = json.load(f)

repos = portfolio.get('repositories', [])

# Generate task assignments like the production system does
optimus_tasks = []
gasket_tasks = []

for repo in repos:
    name = repo['name']
    tier = repo.get('tier', 'M')

    # OPTIMUS gets planning/architecture tasks
    if tier in ['L', 'M']:
        optimus_tasks.append(f'Architecture Review: {name}')
    optimus_tasks.append(f'Progress Planning: {name}')

    # GASKET gets implementation tasks
    gasket_tasks.append(f'Implementation: {name}')
    gasket_tasks.append(f'Testing & QA: {name}')
    gasket_tasks.append(f'Integration & Deployment: {name}')

    # Security for high risk
    if repo.get('risk_tier') == 'HIGH':
        optimus_tasks.insert(0, f'[CRITICAL] Security Audit: {name}')

print('\n🔧 GASKET TASKS (Implementation Agent) - 50 tasks:')
print('=' * 60)
for i, task in enumerate(gasket_tasks[:50], 1):
    print(f'  {i:2}. {task}')

print('\n⚡ OPTIMUS TASKS (Strategy Agent) - 50 tasks:')
print('=' * 60)
for i, task in enumerate(optimus_tasks[:50], 1):
    print(f'  {i:2}. {task}')

# Load current state
with open(WORKSPACE / 'production_state.json') as f:
    state = json.load(f)

print('\n📊 EXECUTION STATS:')
print('=' * 60)
print(f'  GASKET completed:  {state["agent_status"]["gasket"]["tasks_completed"]:,}')
print(f'  OPTIMUS completed: {state["agent_status"]["optimus"]["tasks_completed"]:,}')
print(f'  Total completed:   {state["completed_tasks"]:,}')
print(f'  Pending:           {state["pending_tasks"]:,}')
