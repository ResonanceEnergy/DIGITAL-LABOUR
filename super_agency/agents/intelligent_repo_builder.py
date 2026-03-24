#!/usr/bin/env python3
"""
Intelligent Repo Builder Agent
Core function for analyzing files and autonomously updating repositories
"""

import ast
import json
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .common import CONFIG, PORTFOLIO, Log, ensure_dir, now_iso
from .repo_sentry import analyze_file_content, generate_file_updates


class IntelligentRepoBuilder:
    """
    Core Repo Builder - Analyzes files and autonomously updates repositories
    This is the "bread and butter" of SuperAgency repo operations
    """

    def __init__(self):
        self.repos_base = Path(CONFIG["repos_base"])
        self.builder_logs = Path(CONFIG["reports_dir"]) / "builder_logs"
        ensure_dir(self.builder_logs)
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    def analyze_and_update_repo(self, repo_name: str) -> Dict[str, Any]:
        """
        Core function: Analyze repository files and apply intelligent updates
        """
        repo_path = self.repos_base / repo_name
        if not repo_path.exists():
            return {"error": f"Repository {repo_name} not found locally"}

        Log.info(f"🔍 Analyzing repository: {repo_name}")

        results = {
            "repo": repo_name,
            "timestamp": now_iso(),
            "files_analyzed": 0,
            "updates_applied": 0,
            "recommendations": [],
            "auto_updates": [],
            "manual_actions": []
        }

        # Find all relevant files to analyze
        target_files = self._find_analysis_targets(repo_path)

        for file_path in target_files:
            analysis = self._analyze_and_update_file(repo_path, file_path)
            results["files_analyzed"] += 1

            if analysis.get("updates_applied"):
                results["updates_applied"] += len(analysis["updates_applied"])
                results["auto_updates"].extend(analysis["updates_applied"])

            if analysis.get("recommendations"):
                results["recommendations"].extend(analysis["recommendations"])

            if analysis.get("manual_actions"):
                results["manual_actions"].extend(analysis["manual_actions"])

        # Save builder log
        self._save_builder_log(repo_name, results)

        return results

    def _find_analysis_targets(self, repo_path: Path) -> List[str]:
        """Find files that should be analyzed and potentially updated"""
        targets = []

        # Python files
        for py_file in repo_path.rglob("*.py"):
            if not any(
                skip in str(py_file)
                for skip in ["__pycache__", ".git", "node_modules"]):
                targets.append(str(py_file.relative_to(repo_path)))

        # Configuration files
        for config_file in repo_path.rglob("*.json"):
            if not any(skip in str(config_file)
                       for skip in [".git", "node_modules"]):
                targets.append(str(config_file.relative_to(repo_path)))

        # Documentation files
        for doc_file in repo_path.rglob("README.md"):
            targets.append(str(doc_file.relative_to(repo_path)))

        return targets[:50]  # Limit to prevent excessive processing

    def _analyze_and_update_file(self, repo_path: Path, file_path: str) -> Dict[str, Any]:
        """Analyze a single file and apply intelligent updates"""
        full_path = repo_path / file_path

        try:
            # Get current content
            original_content = full_path.read_text(encoding='utf-8')
            analysis = analyze_file_content(repo_path, file_path)

            updates_applied = []
            recommendations = analysis.get("recommendations", [])
            manual_actions = []

            # Apply automatic updates for Python files
            if file_path.endswith('.py'):
                updated_content, auto_updates = self._apply_python_updates(
                    original_content, analysis)
                if updated_content != original_content:
                    # Create backup
                    backup_path = full_path.with_suffix('.py.backup')
                    backup_path.write_text(original_content, encoding='utf-8')

                    # Apply updates
                    full_path.write_text(updated_content, encoding='utf-8')
                    updates_applied.extend(auto_updates)
                    Log.info(
                        f"✅ Applied {len(auto_updates)} automatic updates to {file_path}")

            # Apply automatic updates for documentation
            elif file_path.endswith('.md'):
                updated_content, auto_updates = self._apply_markdown_updates(
                    original_content, analysis)
                if updated_content != original_content:
                    backup_path = full_path.with_suffix('.md.backup')
                    backup_path.write_text(original_content, encoding='utf-8')
                    full_path.write_text(updated_content, encoding='utf-8')
                    updates_applied.extend(auto_updates)

            return {
                "file": file_path,
                "updates_applied": updates_applied,
                "recommendations": recommendations,
                "manual_actions": manual_actions
            }

        except Exception as e:
            Log.error(f"Error analyzing {file_path}: {e}")
            return {
                "file": file_path,
                "error": str(e),
                "updates_applied": [],
                "recommendations": [],
                "manual_actions": []
            }

    def _apply_python_updates(self, content: str, analysis: Dict[str, Any]) -> tuple[str, List[str]]:
        """Apply automatic updates to Python files"""
        original_content = content
        updates_applied = []

        # Auto-add basic docstrings to functions without them
        try:
            tree = ast.parse(content)
            new_content = content

            # NOTE: Auto-docstring insertion disabled — the previous implementation
            # had bugs with indentation and line-number drift that corrupted files.
            # If re-enabled, must: (1) process nodes in reverse line order to avoid
            # line shifts, (2) use col_offset+4 for body indent, (3) account for
            # multi-line def signatures and decorators.

            # Fix common security issues
            if 'os.system' in new_content and 'subprocess' not in new_content:
                # Add subprocess import and suggest replacement
                if 'import subprocess' not in new_content:
                    lines = new_content.split('\n')
                    # Find a good place to add the import
                    for i, line in enumerate(lines):
                        if line.startswith('import ') or line.startswith(
                            'from '):
                            lines.insert(i, 'import subprocess')
                            break
                    else:
                        lines.insert(0, 'import subprocess')
                    new_content = '\n'.join(lines)
                    updates_applied.append(
                        "Added subprocess import for security")

        except SyntaxError:
            # Don't modify files with syntax errors
            pass

        return new_content, updates_applied

    def _apply_markdown_updates(self, content: str, analysis: Dict[str, Any]) -> tuple[str, List[str]]:
        """Apply automatic updates to Markdown files"""
        original_content = content
        updates_applied = []

        lines = content.split('\n')

        # Auto-add table of contents for long documents
        if len(lines) >50 and not any('Table of Contents' in line
            for line in lines):
            # Find the first heading
            toc_insert_index = -1
            for i, line in enumerate(lines):
                if line.startswith('# '):
                    toc_insert_index = i + 1
                    break

            if toc_insert_index > 0:
                toc = ["## Table of Contents", ""]
                for line in lines:
                    if line.startswith('## '):
                        toc.append(
                            f"- [{line[3:]}](#{line[3:].lower().replace(' ', '-')})")
                    elif line.startswith('### '):
                        toc.append(
                            f"  - [{line[4:]}](#{line[4:].lower().replace(' ', '-')})")

                if len(toc) > 2:  # Only add if there are actual sections
                    lines.insert(toc_insert_index, '\n'.join(toc))
                    updates_applied.append("Added table of contents")

        return '\n'.join(lines), updates_applied

    def _save_builder_log(self, repo_name: str, results: Dict[str, Any]):
        """Save detailed builder log for auditing"""
        log_file = self.builder_logs / \
            f"builder_{repo_name}_{self.session_id}.json"
        log_data = {
            "session_id": self.session_id,
            "repo": repo_name,
            "timestamp": now_iso(),
            "results": results
        }
        log_file.write_text(json.dumps(log_data, indent=2), encoding='utf-8')

    def run_full_portfolio_analysis(self) -> Dict[str, Any]:
        """Run intelligent analysis and updates across entire portfolio"""
        portfolio_results = {
            "session_id": self.session_id,
            "timestamp": now_iso(),
            "repos_processed": 0,
            "total_files_analyzed": 0,
            "total_updates_applied": 0,
            "repo_results": []
        }

        for repo in PORTFOLIO.get("repositories", []):
            try:
                repo_result = self.analyze_and_update_repo(repo["name"])
                portfolio_results["repo_results"].append(repo_result)
                portfolio_results["repos_processed"] += 1
                portfolio_results["total_files_analyzed"] += repo_result.get(
                    "files_analyzed", 0)
                portfolio_results["total_updates_applied"] += repo_result.get(
                    "updates_applied", 0)

                Log.info(
                    f"📊 {repo['name']}: {repo_result.get('files_analyzed', 0)} files analyzed, {repo_result.get('updates_applied', 0)} updates applied")

            except Exception as e:
                Log.error(f"Failed to process repo {repo['name']}: {e}")
                portfolio_results["repo_results"].append({
                    "repo": repo["name"],
                    "error": str(e)
                })

        # Save portfolio summary
        summary_file = self.builder_logs / \
            f"portfolio_builder_{self.session_id}.json"
        summary_file.write_text(json.dumps(
            portfolio_results, indent=2), encoding='utf-8')

        Log.info(
            f"🎯 Portfolio Builder Complete: {portfolio_results['repos_processed']} repos processed, {portfolio_results['total_updates_applied']} total updates applied")

        return portfolio_results

def main():
    """Command-line interface for Intelligent Repo Builder"""
    builder = IntelligentRepoBuilder()

    import sys
    if len(sys.argv) > 1:
        repo_name = sys.argv[1]
        result = builder.analyze_and_update_repo(repo_name)
        print(json.dumps(result, indent=2))
    else:
        # Run full portfolio analysis
        result = builder.run_full_portfolio_analysis()
        print(
            f"Portfolio analysis complete. Processed {result['repos_processed']} repositories.")

if __name__ == "__main__":
    main()
