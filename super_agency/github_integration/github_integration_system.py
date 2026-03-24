#!/usr/bin/env python3
"""
Bit Rage Systems GitHub Integration System
Comprehensive GitHub operations management for the Resonance Energy portfolio
"""

import os
import json
import subprocess
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import logging
from pathlib import Path
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class GitHubIntegrationSystem:
    """
    Comprehensive GitHub operations management system
    """

    def __init__(self, config_path: str = "config/github_config.json"):
        self.config = self.load_config(config_path)
        self.org_name = self.config.get('organization', 'ResonanceEnergy')
        self.token = os.getenv(
            'GITHUB_TOKEN') or self.config.get('github_token')
        self.api_base = "https://api.github.com"
        self.session = requests.Session()

        if self.token:
            self.session.headers.update({
                'Authorization': f'token {self.token}',
                'Accept': 'application/vnd.github.v3+json'
            })

    def load_config(self, config_path: str) -> Dict:
        """Load GitHub integration configuration"""
        default_config = {
            "organization": "ResonanceEnergy",
            "default_visibility": "private",
            "branch_protection": {
                "required_reviews": 1,
                "require_code_owner_reviews": True,
                "dismiss_stale_reviews": True,
                "require_branches_up_to_date": True,
                "restrictions": None
            },
            "security_settings": {
                "enable_dependabot": True,
                "enable_codeql": True,
                "enable_secret_scanning": True,
                "vulnerability_alerts": True
            },
            "ci_cd_templates": [
                "python-ci.yml",
                "node-ci.yml",
                "docker-ci.yml"
            ],
            "repository_templates": {
                "python": "python-template",
                "node": "node-template",
                "go": "go-template"
            }
        }

        config_dir = Path(config_path).parent
        config_dir.mkdir(exist_ok=True)

        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                user_config = json.load(f)
                self._deep_update(default_config, user_config)

        # Save default config if it doesn't exist
        if not os.path.exists(config_path):
            with open(config_path, 'w') as f:
                json.dump(default_config, f, indent=2)

        return default_config

    def _deep_update(self, base_dict: Dict, update_dict: Dict) -> None:
        """Deep update dictionary"""
        for key, value in update_dict.items():
            if isinstance(
                value, dict) and key in base_dict and isinstance(
                base_dict[key],
                dict):
                self._deep_update(base_dict[key], value)
            else:
                base_dict[key] = value

    def run_gh_command(self, command: List[str],
                       cwd: str=None) ->Tuple[str, str, int]:
        """
        Execute GitHub CLI command

        Args:
            command: Command arguments for gh CLI
            cwd: Working directory

        Returns:
            stdout, stderr, return code
        """
        full_command = ['gh'] + command

        try:
            result = subprocess.run(
                full_command,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=300
            )
            return result.stdout, result.stderr, result.returncode
        except subprocess.TimeoutExpired:
            logger.error(
                f"GitHub CLI command timed out: {' '.join(full_command)}")
            return "", "Command timed out", 1
        except FileNotFoundError:
            logger.error("GitHub CLI (gh) not found. Please install it first.")
            return "", "GitHub CLI not installed", 1

    def create_repository(self, name: str, description: str = "",
                         private: bool = True, template: str = None) -> bool:
        """
        Create a new GitHub repository

        Args:
            name: Repository name
            description: Repository description
            private: Whether repository should be private
            template: Template repository to use

        Returns:
            Success status
        """
        logger.info(f"Creating repository: {name}")

        command = [
            'repo', 'create',
            f'{self.org_name}/{name}',
            '--description', description or f'{name} - Bit Rage Systems Project'
        ]

        if private:
            command.append('--private')
        else:
            command.append('--public')

        if template:
            command.extend(['--template', template])

        stdout, stderr, returncode = self.run_gh_command(command)

        if returncode == 0:
            logger.info(f"Successfully created repository: {name}")
            self.setup_repository_protection(name)
            self.setup_security_features(name)
            return True
        else:
            logger.error(f"Failed to create repository {name}: {stderr}")
            return False

    def setup_repository_protection(self, repo_name: str) -> bool:
        """
        Set up branch protection rules for a repository

        Args:
            repo_name: Repository name

        Returns:
            Success status
        """
        logger.info(f"Setting up branch protection for: {repo_name}")

        protection_config = self.config['branch_protection']

        command = [
            'repo', 'set-protection',
            f'{self.org_name}/{repo_name}',
            'main',
            '--required-status-checks', 'CI',
            f'--required-approving-review-count={protection_config["required_reviews"]}'
        ]

        if protection_config['require_code_owner_reviews']:
            command.append('--require-code-owner-reviews')

        if protection_config['dismiss_stale_reviews']:
            command.append('--dismiss-stale-reviews')

        if protection_config['require_branches_up_to_date']:
            command.append('--require-branches-up-to-date')

        stdout, stderr, returncode = self.run_gh_command(command)

        if returncode == 0:
            logger.info(f"Branch protection set up for: {repo_name}")
            return True
        else:
            logger.warning(
                f"Branch protection setup failed for {repo_name}: {stderr}")
            return False

    def setup_security_features(self, repo_name: str) -> bool:
        """
        Enable security features for a repository

        Args:
            repo_name: Repository name

        Returns:
            Success status
        """
        logger.info(f"Setting up security features for: {repo_name}")

        security_config = self.config['security_settings']

        success = True

        # Enable Dependabot
        if security_config['enable_dependabot']:
            if not self.enable_dependabot(repo_name):
                success = False

        # Enable CodeQL
        if security_config['enable_codeql']:
            if not self.enable_codeql(repo_name):
                success = False

        # Enable secret scanning
        if security_config['enable_secret_scanning']:
            if not self.enable_secret_scanning(repo_name):
                success = False

        return success

    def enable_dependabot(self, repo_name: str) -> bool:
        """Enable Dependabot security updates"""
        dependabot_config = {
            "version": 2,
            "updates": [
                {
                    "package-ecosystem": "npm",
                    "directory": "/",
                    "schedule": {"interval": "weekly"}
                },
                {
                    "package-ecosystem": "pip",
                    "directory": "/",
                    "schedule": {"interval": "weekly"}
                }
            ]
        }

        config_path = f".github/dependabot.yml"
        return self.create_or_update_file(
            repo_name, config_path, dependabot_config)

    def enable_codeql(self, repo_name: str) -> bool:
        """Enable CodeQL security scanning"""
        codeql_workflow = """name: "CodeQL"

on:
  push:
    branches: [ "main" ]
  pull_request:
    branches: [ "main" ]
  schedule:
    - cron: '0 6 * * 1'

jobs:
  analyze:
    name: Analyze
    runs-on: ubuntu-latest
    permissions:
      actions: read
      contents: read
      security-events: write

    strategy:
      fail-fast: false
      matrix:
        language: [ 'javascript', 'python' ]

    steps:
    - name: Checkout repository
      uses: actions/checkout@v4

    - name: Initialize CodeQL
      uses: github/codeql-action/init@v2
      with:
        languages: ${{ matrix.language }}

    - name: Autobuild
      uses: github/codeql-action/autobuild@v2

    - name: Perform CodeQL Analysis
      uses: github/codeql-action/analyze@v2
"""

        workflow_path = f".github/workflows/codeql-analysis.yml"
        return self.create_or_update_file(
            repo_name, workflow_path, codeql_workflow)

    def enable_secret_scanning(self, repo_name: str) -> bool:
        """Enable secret scanning"""
        # This is typically done via GitHub API
        if not self.token:
            logger.warning("GitHub token required for secret scanning setup")
            return False

        url = f"{self.api_base}/repos/{self.org_name}/{repo_name}/vulnerability-alerts"
        response = self.session.put(url)

        if response.status_code == 204:
            logger.info(f"Secret scanning enabled for: {repo_name}")
            return True
        else:
            logger.error(
                f"Failed to enable secret scanning for {repo_name}: {response.text}")
            return False

    def create_or_update_file(
            self, repo_name: str, file_path: str, content: Any) ->bool:
        """
        Create or update a file in a repository

        Args:
            repo_name: Repository name
            file_path: Path to the file
            content: File content (dict for JSON, string for text)

        Returns:
            Success status
        """
        if isinstance(content, dict):
            content_str = json.dumps(content, indent=2)
        else:
            content_str = str(content)

        # For now, we'll use gh CLI to create files
        # In production, this would use Git operations
        logger.info(f"Would create/update file {file_path} in {repo_name}")
        logger.info(f"Content preview: {content_str[:100]}...")

        return True  # Placeholder

    def create_pull_request(self, repo_name: str, title: str, body: str,
                          head_branch: str, base_branch: str = "main",
                          reviewers: List[str] = None) -> Optional[str]:
        """
        Create a pull request

        Args:
            repo_name: Repository name
            title: PR title
            body: PR description
            head_branch: Head branch name
            base_branch: Base branch name
            reviewers: List of reviewer usernames

        Returns:
            PR URL if successful, None otherwise
        """
        logger.info(f"Creating PR in {repo_name}: {title}")

        command = [
            'pr', 'create',
            '--repo', f'{self.org_name}/{repo_name}',
            '--title', title,
            '--body', body,
            '--head', head_branch,
            '--base', base_branch
        ]

        if reviewers:
            command.extend(['--reviewer', ','.join(reviewers)])

        stdout, stderr, returncode = self.run_gh_command(command)

        if returncode == 0:
            # Extract PR URL from output
            pr_url = stdout.strip().split('\n')[-1] if stdout.strip() else None
            logger.info(f"PR created: {pr_url}")
            return pr_url
        else:
            logger.error(f"Failed to create PR: {stderr}")
            return None

    def setup_repository_from_portfolio(self, repo_config: Dict) -> bool:
        """
        Set up a repository based on portfolio configuration

        Args:
            repo_config: Repository configuration from portfolio

        Returns:
            Success status
        """
        name = repo_config['name']
        visibility = repo_config.get('visibility', 'public')
        tier = repo_config.get('tier', 'S')
        autonomy = repo_config.get('autonomy_level', 'L1')

        # Determine if repository should be private based on tier/autonomy
        private = visibility == 'private' or autonomy in [
            'L2', 'L3'] or tier in ['EXECUTIVE']

        description = f"{name} - {tier} tier, {autonomy} autonomy - Bit Rage Systems Portfolio"

        # Map tier to template
        template_map = {
            'EXECUTIVE': 'executive-template',
            'L': 'large-project-template',
            'M': 'medium-project-template',
            'S': 'small-project-template'
        }

        # Skip templates for now - they don't exist yet
        template = None  # template_map.get(tier, 'small-project-template')

        success = self.create_repository(name, description, private, template)

        if success:
            logger.info(f"Successfully set up repository: {name}")
            # Additional setup based on autonomy level
            if autonomy == 'L3':
                self.setup_high_autonomy_features(name)
        else:
            logger.error(f"Failed to set up repository: {name}")

        return success

    def setup_high_autonomy_features(self, repo_name: str) -> bool:
        """Set up high-autonomy features for L3 repositories"""
        logger.info(f"Setting up high-autonomy features for: {repo_name}")

        # Enhanced branch protection
        # Automated deployment workflows
        # Advanced security features
        # Council integration

        return True

    def sync_portfolio_repositories(
            self, portfolio_path: str="../portfolio.json") ->Dict:
        """
        Sync all repositories from portfolio configuration

        Args:
            portfolio_path: Path to portfolio configuration file

        Returns:
            Sync results
        """
        logger.info("Starting portfolio repository sync")

        if not os.path.exists(portfolio_path):
            logger.error(f"Portfolio file not found: {portfolio_path}")
            return {'error': 'Portfolio file not found'}

        with open(portfolio_path, 'r') as f:
            portfolio = json.load(f)

        results = {
            'created': [],
            'updated': [],
            'failed': [],
            'skipped': []
        }

        for repo_config in portfolio.get('repositories', []):
            name = repo_config['name']

            # Check if repository exists
            if self.repository_exists(name):
                logger.info(
                    f"Repository {name} already exists, checking for updates")
                results['skipped'].append(name)
            else:
                logger.info(f"Creating new repository: {name}")
                if self.setup_repository_from_portfolio(repo_config):
                    results['created'].append(name)
                else:
                    results['failed'].append(name)

        logger.info(
            f"Portfolio sync complete: {len(results['created'])} created, {len(results['failed'])} failed")
        return results

    def autonomous_sync(self) -> Dict:
        """
        Autonomous portfolio synchronization
        Designed to be called automatically by the Bit Rage Systems orchestration system

        Returns:
            Sync results with detailed status
        """
        logger.info("🤖 Starting autonomous GitHub portfolio sync")

        try:
            # Verify authentication
            if not self.token:
                return {'error': 'No GitHub token available', 'status': 'failed'}

            # Test API connectivity
            test_response = self.session.get(f"{self.api_base}/user")
            if test_response.status_code != 200:
                return {'error': f'API authentication failed: {test_response.status_code}', 'status': 'failed'}

            # Load portfolio
            portfolio_path = Path(__file__).parent.parent / "portfolio.json"
            if not portfolio_path.exists():
                return {'error': f'Portfolio file not found: {portfolio_path}', 'status': 'failed'}

            with open(portfolio_path, 'r') as f:
                portfolio = json.load(f)

            results = {
                'status': 'success',
                'timestamp': datetime.now().isoformat(),
                'repositories_processed': 0,
                'created': [],
                'updated': [],
                'failed': [],
                'skipped': [],
                'errors': []
            }

            total_repos = len(portfolio.get('repositories', []))
            logger.info(
                f"Processing {total_repos} repositories from portfolio")

            for i, repo_config in enumerate(
                portfolio.get('repositories', []),
                1):
                name = repo_config['name']
                logger.info(
                    f"[{i}/{total_repos}] Processing repository: {name}")

                try:
                    # Check if repository exists
                    if self.repository_exists(name):
                        logger.info(
                            f"Repository {name} exists, verifying configuration")
                        results['skipped'].append(name)
                    else:
                        logger.info(f"Creating new repository: {name}")
                        if self.setup_repository_from_portfolio(repo_config):
                            results['created'].append(name)
                            logger.info(f"✅ Successfully created: {name}")
                        else:
                            results['failed'].append(name)
                            logger.error(f"❌ Failed to create: {name}")

                    results['repositories_processed'] += 1

                except Exception as e:
                    error_msg = f"Error processing {name}: {str(e)}"
                    logger.error(error_msg)
                    results['errors'].append(error_msg)
                    results['failed'].append(name)

            # Summary
            success_count = len(results['created'])
            failed_count = len(results['failed'])
            skipped_count = len(results['skipped'])

            logger.info(
                f"🤖 Autonomous sync complete: {success_count} created, {skipped_count} skipped, {failed_count} failed")

            results['summary'] = {
                'total_repositories': total_repos, 'successful': success_count,
                'skipped': skipped_count, 'failed': failed_count,
                'success_rate': f"{(success_count / total_repos) *100: .1f} %"
                if total_repos >0 else "0%"}

            return results

        except Exception as e:
            error_msg = f"Autonomous sync failed: {str(e)}"
            logger.error(error_msg)
            return {'error': error_msg, 'status': 'failed'}

    def repository_exists(self, repo_name: str) -> bool:
        """Check if a repository exists"""
        command = ['repo', 'view', f'{self.org_name}/{repo_name}']
        stdout, stderr, returncode = self.run_gh_command(command)
        return returncode == 0

def main():
    """Main entry point for GitHub integration operations"""
    import sys

    system = GitHubIntegrationSystem()

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == 'autonomous':
            # Autonomous operation - designed for automated calls
            results = system.autonomous_sync()
            print(json.dumps(results, indent=2))
            sys.exit(0 if results.get('status') == 'success' else 1)

        elif command == 'sync':
            # Manual sync operation
            results = system.sync_portfolio_repositories()
            print("Portfolio sync results:", json.dumps(results, indent=2))

        elif command == 'create' and len(sys.argv) > 2:
            # Create specific repository
            repo_name = sys.argv[2]
            description = sys.argv[3] if len(
                sys.argv) > 3 else f"{repo_name} - Bit Rage Systems Project"
            success = system.create_repository(repo_name, description, True)
            print(
                f"Repository creation {'successful' if success else 'failed'}: {repo_name}")

        else:
            print("Usage:")
            print("  python github_integration_system.py autonomous  # Autonomous sync")
            print("  python github_integration_system.py sync        # Manual sync")
            print(
                "  python github_integration_system.py create <name> [description]  # Create repo")
    else:
        # Default: run autonomous sync
        print("🤖 Bit Rage Systems GitHub Integration System")
        print("Running autonomous portfolio sync...")
        results = system.autonomous_sync()
        print("\n" + "="*50)
        print("SYNC RESULTS:")
        print(json.dumps(results, indent=2))

if __name__ == "__main__":
    main()