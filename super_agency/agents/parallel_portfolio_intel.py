#!/usr/bin/env python3
"""
Parallel Portfolio Intelligence
High-performance portfolio analysis with maximum CPU utilization
"""

import multiprocessing as mp
import concurrent.futures
import json
import os
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Tuple
import logging

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ParallelPortfolioIntel:
    """Parallel portfolio intelligence analysis for maximum throughput"""

    def __init__(self):
        self.root = Path(__file__).resolve(
        ).parents[1] / "ResonanceEnergy_DigitalLabour"
        self.config = json.loads(
            (self.root / "config" / "settings.json").read_text())
        self.repos_base = Path(self.config.get(
            "repos_base", "./repos")).resolve()
        self.reports_dir = Path(self.config.get(
            "reports_dir", "./reports")).resolve()
        self.reports_dir.mkdir(parents=True, exist_ok=True)

        # Get CPU count for parallel processing
        self.max_workers = mp.cpu_count()
        logger.info(
            f"Parallel Portfolio Intel initialized with {self.max_workers} workers")

    def get_all_repos(self) -> List[str]:
        """Get all repository names"""
        repos = []
        if self.repos_base.exists():
            repos = [d.name for d in self.repos_base.iterdir() if d.is_dir()]
        return repos

    def analyze_repo_parallel(self, repo_name: str) -> Dict[str, Any]:
        """Analyze a single repository"""
        repo_path = self.repos_base / repo_name
        if not repo_path.exists():
            return {"repo": repo_name, "error": "Repository not found"}

        analysis = {
            "repo": repo_name, "timestamp": datetime.now().isoformat(),
            "readme": self.parse_readme(repo_path / "README.md"),
            "package_json": self.analyze_package_json(
                repo_path / "package.json"),
            "requirements": self.analyze_requirements(
                repo_path / "requirements.txt"),
            "portfolio_yaml": self.read_simple_yaml(
                repo_path / "portfolio.yaml"),
            "repo_index": self.read_json(repo_path / "REPO_INDEX.json"),
            "file_count": self.count_files(repo_path),
            "code_metrics": self.calculate_code_metrics(repo_path)}

        return analysis

    def parse_readme(self, readme_path: Path) -> Dict[str, Any]:
        """Parse README file"""
        info = {"exists": readme_path.exists(), "size": 0, "headings": []}
        if not readme_path.exists():
            return info

        try:
            txt = readme_path.read_text(encoding='utf-8', errors='ignore')
            info["size"] = len(txt)
            heads = []
            for line in txt.splitlines():
                if line.startswith('#'):
                    heads.append(line.strip().lstrip('#').strip())
            info["headings"] = heads[:15]
        except Exception as e:
            info["error"] = str(e)

        return info

    def analyze_package_json(self, package_path: Path) -> Dict[str, Any]:
        """Analyze package.json file"""
        info = {"exists": package_path.exists()}
        if not info["exists"]:
            return info

        try:
            data = json.loads(package_path.read_text(encoding='utf-8'))
            info.update({
                "name": data.get("name"),
                "version": data.get("version"),
                "dependencies": len(data.get("dependencies", {})),
                "dev_dependencies": len(data.get("devDependencies", {})),
                "scripts": list(data.get("scripts", {}).keys())
            })
        except Exception as e:
            info["error"] = str(e)

        return info

    def analyze_requirements(self, req_path: Path) -> Dict[str, Any]:
        """Analyze requirements.txt file"""
        info = {"exists": req_path.exists(), "packages": []}
        if not info["exists"]:
            return info

        try:
            with open(req_path, 'r', encoding='utf-8') as f:
                packages = []
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        packages.append(line)
                info["packages"] = packages
                info["count"] = len(packages)
        except Exception as e:
            info["error"] = str(e)

        return info

    def read_simple_yaml(self, yaml_path: Path) -> Dict[str, Any]:
        """Read simple YAML file"""
        data = {}
        if not yaml_path.exists():
            return data

        try:
            key = None
            for line in yaml_path.read_text(
                encoding='utf-8', errors='ignore').splitlines():
                s = line.rstrip('\n')
                if not s or s.strip().startswith('#'):
                    continue
                if re.match(r'^[A-Za-z0-9_]+:\s*$', s):
                    key = s.split(':')[0].strip()
                    data[key] = None
                elif ':' in s and not s.lstrip().startswith('- '):
                    k, v = s.split(':', 1)
                    data[k.strip()] = v.strip().strip('"')
                    key = k.strip()
                elif s.lstrip().startswith('- ') and key:
                    if data.get(key) is None or not isinstance(
                        data.get(key),
                        list):
                        data[key] = []
                    data[key].append(s.strip()[2:])
        except Exception:
            pass

        return data

    def read_json(self, json_path: Path) -> Any:
        """Read JSON file"""
        if not json_path.exists():
            return None
        try:
            return json.loads(json_path.read_text(encoding='utf-8'))
        except Exception:
            return None

    def count_files(self, repo_path: Path) -> Dict[str, int]:
        """Count files by type"""
        counts = {"total": 0, "code": 0, "docs": 0, "tests": 0, "config": 0}

        if not repo_path.exists():
            return counts

        try:
            for root, dirs, files in os.walk(repo_path):
                # Skip certain directories
                dirs[:] = [d for d in dirs if not d.startswith(
                    '.') and d not in ['node_modules', '__pycache__', '.git']]

                for file in files:
                    counts["total"] += 1
                    if file.endswith(
                        ('.py', '.js', '.ts', '.java', '.cpp', '.c', '.go',
                         '.rs')):
                        counts["code"] += 1
                    elif file.endswith(('.md', '.txt', '.rst')):
                        counts["docs"] += 1
                    elif 'test' in file.lower() or file.startswith('test_'):
                        counts["tests"] += 1
                    elif file.endswith(('.json', '.yaml', '.yml', '.toml', '.ini', '.cfg')):
                        counts["config"] += 1
        except Exception:
            pass

        return counts

    def calculate_code_metrics(self, repo_path: Path) -> Dict[str, Any]:
        """Calculate basic code metrics"""
        metrics = {"lines_of_code": 0, "files_analyzed": 0}

        if not repo_path.exists():
            return metrics

        try:
            for root, dirs, files in os.walk(repo_path):
                dirs[:] = [d for d in dirs if not d.startswith(
                    '.') and d not in ['node_modules', '__pycache__', '.git']]

                for file in files:
                    if file.endswith(
                        ('.py', '.js', '.ts', '.java', '.cpp', '.c')):
                        file_path = Path(root) / file
                        try:
                            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                lines = f.readlines()
                                metrics["lines_of_code"] += len(lines)
                                metrics["files_analyzed"] += 1
                        except Exception:
                            continue
        except Exception:
            pass

        return metrics

    def run_parallel_analysis(self) -> Dict[str, Any]:
        """Run parallel analysis on all repositories"""
        logger.info("🚀 Starting parallel portfolio analysis...")

        repos = self.get_all_repos()
        if not repos:
            logger.warning("No repositories found to analyze")
            return {}

        logger.info(
            f"Analyzing {len(repos)} repositories with {self.max_workers} workers")

        results = {}

        def analyze_single_repo(repo_name: str) -> Tuple[str, Dict[str, Any]]:
            logger.info(f"Analyzing {repo_name}...")
            start_time = datetime.now()
            result = self.analyze_repo_parallel(repo_name)
            end_time = datetime.now()
            result["analysis_duration"] = (
                end_time - start_time).total_seconds()
            return repo_name, result

        # Use ProcessPoolExecutor for CPU-intensive analysis
        with concurrent.futures.ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(
                analyze_single_repo, repo): repo for repo in repos}

            for future in concurrent.futures.as_completed(futures):
                repo_name, result = future.result()
                results[repo_name] = result
                duration = result.get("analysis_duration", 0)
                logger.info(f"✅ {repo_name}: {duration:.2f}s")

        return results

    def generate_consolidated_report(self, analysis_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate consolidated portfolio report"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "total_repos": len(analysis_results),
            "summary": {
                "total_files": 0,
                "total_lines_of_code": 0,
                "repos_with_readme": 0,
                "repos_with_package_json": 0,
                "repos_with_requirements": 0
            },
            "repo_details": analysis_results
        }

        for repo_data in analysis_results.values():
            if "file_count" in repo_data:
                report["summary"]["total_files"] += repo_data["file_count"]["total"]

            if "code_metrics" in repo_data:
                report["summary"]["total_lines_of_code"] += repo_data["code_metrics"]["lines_of_code"]

            if repo_data.get("readme", {}).get("exists"):
                report["summary"]["repos_with_readme"] += 1

            if repo_data.get("package_json", {}).get("exists"):
                report["summary"]["repos_with_package_json"] += 1

            if repo_data.get("requirements", {}).get("exists"):
                report["summary"]["repos_with_requirements"] += 1

        return report

    def save_report(self, report: Dict[str, Any]) -> Path:
        """Save analysis report to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = self.reports_dir / \
            f"parallel_portfolio_analysis_{timestamp}.json"

        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        logger.info(f"Report saved to {report_file}")
        return report_file

def main():
    """Main parallel portfolio intelligence function"""
    print("🧠 Parallel Portfolio Intelligence")
    print("=" * 50)

    analyzer = ParallelPortfolioIntel()

    try:
        # Run parallel analysis
        results = analyzer.run_parallel_analysis()

        # Generate consolidated report
        report = analyzer.generate_consolidated_report(results)

        # Save report
        report_file = analyzer.save_report(report)

        # Print summary
        print("\n📊 Analysis Summary:")
        print(f"   Repositories Analyzed: {report['summary']['total_repos']}")
        print(f"   Total Files: {report['summary']['total_files']}")
        print(
            f"   Total Lines of Code: {report['summary']['total_lines_of_code']}")
        print(
            f"   Repos with README: {report['summary']['repos_with_readme']}")
        print(
            f"   Repos with package.json: {report['summary']['repos_with_package_json']}")
        print(
            f"   Repos with requirements.txt: {report['summary']['repos_with_requirements']}")
        print(f"   Report Saved: {report_file}")

    except KeyboardInterrupt:
        print("\n⚠️  Analysis interrupted by user")
    except Exception as e:
        print(f"\n💥 Analysis failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()