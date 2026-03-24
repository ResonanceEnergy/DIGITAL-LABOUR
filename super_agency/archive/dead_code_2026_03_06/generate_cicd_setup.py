#!/usr/bin/env python3
"""
Super Agency CI/CD Setup Generator
Generate workflow files for manual deployment to repositories
"""

import os
import json
import shutil
from pathlib import Path

class CICDSetupGenerator:
    """
    Generate CI/CD workflow files for manual deployment
    """

    def __init__(self):
        """Initialize."""
        # Load portfolio
        with open('portfolio.json', 'r') as f:
            self.portfolio = json.load(f)

        # Setup output directory
        self.output_dir = Path('cicd_workflows')
        self.output_dir.mkdir(exist_ok=True)

        # Load templates
        self.templates_dir = Path('github_integration/templates')
        self.templates = self.load_templates()

    def load_templates(self):
        """Load CI/CD workflow templates"""
        templates = {}
        if self.templates_dir.exists():
            for template_file in self.templates_dir.glob('*.yml'):
                with open(template_file, 'r') as f:
                    templates[template_file.stem] = f.read()
        return templates

    def generate_repository_workflows(self, repo_name):
        """Generate workflow files for a specific repository"""
        repo_dir = self.output_dir / repo_name
        workflows_dir = repo_dir / '.github' / 'workflows'
        workflows_dir.mkdir(parents=True, exist_ok=True)

        print(f"📝 Generating workflows for {repo_name}...")

        for template_name, template_content in self.templates.items():
            workflow_file = workflows_dir / f"{template_name}.yml"
            with open(workflow_file, 'w') as f:
                f.write(template_content)
            print(f"  ✅ Created {template_name}.yml")

        # Create deployment script for this repository
        deploy_script = repo_dir / 'deploy_workflows.bat'
        with open(deploy_script, 'w') as f:
            f.write(f'''@echo off
REM Deploy CI/CD workflows to {repo_name}
echo Deploying CI/CD workflows to {repo_name}...

REM Copy workflow files to repository
xcopy ".github" "c:\\path\\to\\{repo_name}\\.github\\" /E /I /Y

echo Workflows deployed! Push to GitHub to activate.
pause
''')

        return repo_dir

    def generate_all_workflows(self):
        """Generate workflows for all repositories"""
        print("🎯 Generating CI/CD Workflows for Portfolio")
        print("=" * 50)

        deployment_instructions = []

        for repo in self.portfolio['repositories']:
            repo_name = repo['name']
            try:
                repo_dir = self.generate_repository_workflows(repo_name)
                deployment_instructions.append(f"- {repo_name}: Copy from {repo_dir}\\.github\\workflows\\")
                print(f"✅ {repo_name} workflows generated\n")
            except Exception as e:
                print(f"❌ Failed to generate for {repo_name}: {e}\n")

        # Create master deployment guide
        self.create_deployment_guide(deployment_instructions)

        print("=" * 50)
        print("📁 All workflows generated in: cicd_workflows\\")
        print("📋 Check cicd_workflows\\DEPLOYMENT_GUIDE.md for instructions")

        return True

    def create_deployment_guide(self, instructions):
        """Create a deployment guide"""
        guide_path = self.output_dir / 'DEPLOYMENT_GUIDE.md'

        with open(guide_path, 'w') as f:
            f.write('''# Super Agency CI/CD Deployment Guide

## Overview
This directory contains CI/CD workflow templates for all portfolio repositories.

## Available Workflows
- **python-ci.yml**: Python testing, linting, type checking, and coverage
- **security-scan.yml**: Security scanning with Trivy, Bandit, and CodeQL

## Deployment Instructions

### Option 1: Manual Copy (Recommended)
For each repository, copy the workflow files to your local repository:

''' + '\n'.join(instructions) + '''

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
''')

def main():
    """Main setup generation"""
    generator = CICDSetupGenerator()
    success = generator.generate_all_workflows()

    if success:
        print("🎉 CI/CD Setup generation completed!")
        print("📂 Check cicd_workflows/ directory for all workflow files")
    else:
        print("⚠️  Some generations failed - check logs above")

    return success

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)