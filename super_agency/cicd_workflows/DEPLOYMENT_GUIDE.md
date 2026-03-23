# DIGITAL LABOUR CI/CD Deployment Guide

## Overview
This directory contains CI/CD workflow templates for all portfolio repositories.

## Available Workflows
- **python-ci.yml**: Python testing, linting, type checking, and coverage
- **security-scan.yml**: Security scanning with Trivy, Bandit, and CodeQL

## Deployment Instructions

### Option 1: Manual Copy (Recommended)
For each repository, copy the workflow files to your local repository:

- NATEBJONES: Copy from cicd_workflows\NATEBJONES\.github\workflows\
- NCL: Copy from cicd_workflows\NCL\.github\workflows\
- TESLACALLS2026: Copy from cicd_workflows\TESLACALLS2026\.github\workflows\
- future-predictor-council: Copy from cicd_workflows\future-predictor-council\.github\workflows\
- AAC: Copy from cicd_workflows\AAC\.github\workflows\
- ADVENTUREHEROAUTO: Copy from cicd_workflows\ADVENTUREHEROAUTO\.github\workflows\
- Crimson-Compass: Copy from cicd_workflows\Crimson-Compass\.github\workflows\
- YOUTUBEDROP: Copy from cicd_workflows\YOUTUBEDROP\.github\workflows\
- CIVIL-FORGE-TECHNOLOGIES-: Copy from cicd_workflows\CIVIL-FORGE-TECHNOLOGIES-\.github\workflows\
- GEET-PLASMA-PROJECT: Copy from cicd_workflows\GEET-PLASMA-PROJECT\.github\workflows\
- TESLA-TECH: Copy from cicd_workflows\TESLA-TECH\.github\workflows\
- ELECTRIC-UNIVERSE: Copy from cicd_workflows\ELECTRIC-UNIVERSE\.github\workflows\
- VORTEX-HUNTER: Copy from cicd_workflows\VORTEX-HUNTER\.github\workflows\
- MircoHydro: Copy from cicd_workflows\MircoHydro\.github\workflows\
- electric-ice: Copy from cicd_workflows\electric-ice\.github\workflows\
- SUPERSTONK-TRADER: Copy from cicd_workflows\SUPERSTONK-TRADER\.github\workflows\
- HUMAN-HEALTH: Copy from cicd_workflows\HUMAN-HEALTH\.github\workflows\
- Adventure-Hero-Chronicles-Of-Glory: Copy from cicd_workflows\Adventure-Hero-Chronicles-Of-Glory\.github\workflows\
- QDFG1: Copy from cicd_workflows\QDFG1\.github\workflows\
- NCC-Doctrine: Copy from cicd_workflows\NCC-Doctrine\.github\workflows\
- NCC: Copy from cicd_workflows\NCC\.github\workflows\
- resonance-uy-py: Copy from cicd_workflows\resonance-uy-py\.github\workflows\
- perpetual-flow-cube: Copy from cicd_workflows\perpetual-flow-cube\.github\workflows\
- demo: Copy from cicd_workflows\demo\.github\workflows\

Then commit and push to activate the workflows.

### Option 2: Automated Deployment
Run the deploy script in each repository directory:
```
deploy_workflows.bat
```

## Workflow Features

### Python CI (python-ci.yml)
- Multi-Python version testing (3.8, 3.9, 3.10, 3.11)
- Code linting with flake8
- Type checking with mypy
- Code formatting with black
- Test coverage reporting
- Automated dependency updates

### Security Scan (security-scan.yml)
- Vulnerability scanning with Trivy
- Python security linting with Bandit
- Dependency review for PRs
- CodeQL security analysis
- Weekly automated scans

## Activation
Workflows activate automatically on:
- Push to main/develop branches
- Pull requests to main branch
- Weekly schedule (security scans)

## Monitoring
Check the Actions tab in each repository to monitor workflow execution.
