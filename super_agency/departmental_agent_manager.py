#!/usr/bin/env python3
"""
Departmental Agent Management System
Manages agents across the restructured departmental organization
"""

import os
import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DepartmentalAgentManager:
    """Manages agents across departmental structure"""

    def __init__(self, root_path: Path):
        self.root = root_path
        self.departments: Dict[str, Any] = {}
        self.agents: Dict[str, Any] = {}
        self.org_structure = {}
        self.load_organization_structure()

    def load_organization_structure(self):
        """Load the organizational structure and department configurations"""
        org_file = self.root / "organization_structure.json"
        if org_file.exists():
            try:
                with open(org_file, 'r') as f:
                    self.org_structure = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load organization structure: {e}")
                self.org_structure = {}
        else:
            logger.error(
                f"Organization structure file not found at: {org_file}")
            self.org_structure = {}

        # Load department configurations
        departments_dir = self.root / "departments"
        if departments_dir.exists():
            for dept_dir in departments_dir.iterdir():
                if dept_dir.is_dir():
                    config_file = dept_dir / "config.json"
                    if config_file.exists():
                        with open(config_file, 'r') as f:
                            dept_config = json.load(f)
                            self.departments[dept_config["department"]
                                ] = dept_config

        logger.info(f"Loaded {len(self.departments)} departments")

    def get_department_agents(self, department: str) -> List[Dict[str, Any]]:
        """Get all agents in a specific department"""
        if department not in self.departments:
            return []

        dept_config = self.departments[department]
        agents = []

        # Collect agents from subdepartments
        for subdept_key, subdept in dept_config.get(
            "subdepartments", {}).items():
            subdept_path = self.root / "departments" / department / subdept_key

            if subdept_path.exists():
                for agent_file in subdept.get("agents", []):
                    agent_path = subdept_path / agent_file
                    if agent_path.exists():
                        agents.append({
                            "name": agent_file.replace(".py", ""),
                            "file": str(agent_path),
                            "department": department,
                            "subdepartment": subdept_key,
                            "role": subdept.get("name", "Unknown")
                        })

        return agents

    def get_all_agents_by_department(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get all agents organized by department"""
        result = {}
        for dept in self.departments.keys():
            result[dept] = self.get_department_agents(dept)
        return result

    def get_agent_status_report(self) -> Dict[str, Any]:
        """Generate comprehensive agent status report"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "total_departments": len(self.departments),
            "department_breakdown": {},
            "total_agents": 0,
            "active_departments": []
        }

        for dept_name, dept_config in self.departments.items():
            agents = self.get_department_agents(dept_name)
            report["department_breakdown"][dept_name] = {
                "name": dept_config["name"],
                "head": dept_config["head"],
                "authority_level": dept_config["authority_level"],
                "agent_count": len(agents),
                "agents": [agent["name"] for agent in agents]
            }
            report["total_agents"] += len(agents)

            if len(agents) > 0:
                report["active_departments"].append(dept_name)

        return report

    def validate_departmental_structure(self) -> Dict[str, Any]:
        """Validate the departmental structure and agent placement"""
        validation = {
            "valid": True,
            "issues": [],
            "recommendations": []
        }

        # Check for missing agent files
        for dept_name, dept_config in self.departments.items():
            for subdept_key, subdept in dept_config.get(
                "subdepartments", {}).items():
                subdept_path = self.root / "departments" / dept_name / subdept_key

                for agent_file in subdept.get("agents", []):
                    agent_path = subdept_path / agent_file
                    if not agent_path.exists():
                        validation["issues"].append(
                            f"Missing agent file: {agent_path}")
                        validation["valid"] = False

        # Check for council separation
        if "executive_council" in self.departments:
            council_config = self.departments["executive_council"]
            if council_config.get("authority_level") != "AZ_FINAL":
                validation["issues"].append(
                    "Executive Council must have AZ_FINAL authority")
                validation["valid"] = False

        # Check authority hierarchy
        authority_levels = ["BASIC", "STANDARD", "HIGH", "AZ_FINAL"]
        for dept_name, dept_config in self.departments.items():
            if dept_config.get("authority_level") not in authority_levels:
                validation["issues"].append(
                    f"Invalid authority level for {dept_name}")
                validation["valid"] = False

        return validation

def main():
    """Main departmental management function"""
    print("🏢 Bit Rage Systems Departmental Agent Management System")
    print("=" * 60)

    root_path = Path(__file__).resolve().parent
    manager = DepartmentalAgentManager(root_path)

    # Generate status report
    report = manager.get_agent_status_report()

    print(f"📊 Organization Status Report")
    print(f"   Total Departments: {report['total_departments']}")
    print(f"   Total Agents: {report['total_agents']}")
    print(f"   Active Departments: {len(report['active_departments'])}")
    print()

    for dept_name, dept_info in report["department_breakdown"].items():
        print(f"🏛️  {dept_info['name']} ({dept_name})")
        print(f"   Head: {dept_info['head']}")
        print(f"   Authority: {dept_info['authority_level']}")
        print(f"   Agents: {dept_info['agent_count']}")
        if dept_info['agents']:
            for agent in dept_info['agents']:
                print(f"     • {agent}")
        print()

    # Validate structure
    validation = manager.validate_departmental_structure()
    if validation["valid"]:
        print("✅ Departmental structure validation: PASSED")
    else:
        print("❌ Departmental structure validation: FAILED")
        for issue in validation["issues"]:
            print(f"   • {issue}")

if __name__ == "__main__":
    main()