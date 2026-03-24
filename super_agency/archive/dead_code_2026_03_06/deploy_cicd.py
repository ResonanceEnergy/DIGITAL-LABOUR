#!/usr/bin/env python3
"""
Super Agency CI/CD Deployment System
Activate workflow templates across all portfolio repositories
"""

import os
import json
import requests
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class CICDDeploymentSystem:
    """
    Deploy CI/CD workflows to all portfolio repositories
    """

    def __init__(self):
        """Initialize."""
        self.token = os.getenv('GITHUB_TOKEN')
        self.org = 'ResonanceEnergy'
        self.session = requests.Session()

        if self.token:
            self.session.headers.update({
                'Authorization': f'token {self.token}',
                'Accept': 'application/vnd.github.v3+json'
            })

        # Load portfolio
        with open('portfolio.json', 'r') as f:
            self.portfolio = json.load(f)

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

    def deploy_workflows_to_repository(self, repo_name):
        """Deploy CI/CD workflows to a specific repository"""
        print(f"🚀 Deploying CI/CD to {repo_name}...")

        for template_name, template_content in self.templates.items():
            # Create .github/workflows directory structure
            workflow_path = f".github/workflows/{template_name}.yml"

            # Create the workflow file via GitHub API
            url = f"https://api.github.com/repos/{self.org}/{repo_name}/contents/{workflow_path}"

            # Check if file already exists
            response = self.session.get(url)
            if response.status_code == 200:
                print(f"  ⚠️  {template_name}.yml already exists in {repo_name}")
                continue

            # Create the file
            data = {
                "message": f"Add {template_name} CI/CD workflow",
                "content": template_content.encode('utf-8').decode('latin-1')  # GitHub API encoding
            }

            response = self.session.put(url, json=data)

            if response.status_code in [200, 201]:
                print(f"  ✅ Created {template_name}.yml in {repo_name}")
            else:
                print(f"  ❌ Failed to create {template_name}.yml in {repo_name}: {response.text}")

    def deploy_all_workflows(self):
        """Deploy workflows to all repositories in portfolio"""
        print("🎯 Starting CI/CD Deployment Across Portfolio")
        print("=" * 50)

        successful = 0
        total = len(self.portfolio['repositories'])

        for repo in self.portfolio['repositories']:
            repo_name = repo['name']
            try:
                self.deploy_workflows_to_repository(repo_name)
                successful += 1
                print(f"✅ {repo_name} CI/CD deployment completed\n")
            except Exception as e:
                print(f"❌ Failed to deploy to {repo_name}: {e}\n")

        print("=" * 50)
        print(f"📊 CI/CD Deployment Summary: {successful}/{total} repositories")
        return successful == total

def main():
    """Main deployment execution"""
    system = CICDDeploymentSystem()
    success = system.deploy_all_workflows()

    if success:
        print("🎉 CI/CD Deployment completed successfully!")
        print("🔄 Workflows will trigger on next push or PR")
    else:
        print("⚠️  Some deployments failed - check logs above")

    return success

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)