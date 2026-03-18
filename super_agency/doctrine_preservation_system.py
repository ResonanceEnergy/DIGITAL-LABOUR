#!/usr/bin/env python3
"""
BIT RAGE LABOUR Doctrine Preservation System
Immutable doctrine storage and validation engine
"""

import hashlib
import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml


class DoctrineError(Exception):
    """Custom exception for doctrine operations"""
    pass

class DoctrineValidator:
    """Validates doctrine compliance and integrity"""

    def __init__(self):
        """Initialize."""
        self.doctrine_schema = {
            "required_fields": [
                "memory_principles",
                "operational_principles",
                "governance_principles"
            ],
            "principle_categories": [
                "memory_principles",
                "operational_principles",
                "governance_principles"
            ]
        }

    def validate_doctrine(self, doctrine: Dict) -> Tuple[bool, List[str]]:
        """Validate doctrine structure and content"""
        errors = []

        # Check required fields
        for field in self.doctrine_schema["required_fields"]:
            if field not in doctrine:
                errors.append(f"Missing required field: {field}")

        # Validate principle categories
        for category in self.doctrine_schema["principle_categories"]:
            if category in doctrine:
                if not isinstance(doctrine[category], list):
                    errors.append(f"{category} must be a list")
                elif len(doctrine[category]) == 0:
                    errors.append(f"{category} cannot be empty")

        # Validate principle content
        for category in self.doctrine_schema["principle_categories"]:
            if category in doctrine and isinstance(doctrine[category], list):
                for i, principle in enumerate(doctrine[category]):
                    if not isinstance(principle, (str, dict)):
                        errors.append(
                            f"{category}[{i}] must be string or dict")
                    if isinstance(principle, dict):
                        if "name" not in principle or "description" not in principle:
                            errors.append(
                                f"{category}[{i}] missing name or description")

        return len(errors) == 0, errors

    def validate_compliance(self, action: Dict, doctrine: Dict) -> Tuple[bool, List[str]]:
        """Check if an action complies with doctrine"""
        violations = []

        # Check memory principles
        if "memory_usage" in action:
            memory_mb = action["memory_usage"]
            if memory_mb > 256:  # Ultra-conservative limit
                violations.append(
                    f"Memory usage {memory_mb}MB exceeds doctrine limit of 256MB")

        # Check operational principles
        if "autonomous_action" in action:
            if action["autonomous_action"] and "human_approval" not in action:
                violations.append(
                    "Autonomous actions require human approval tracking")

        # Check governance principles
        if "data_handling" in action:
            if "consent_receipt" not in action.get("data_handling", {}):
                violations.append("Data handling requires consent receipt")

        return len(violations) == 0, violations

class DoctrineStorage:
    """Immutable doctrine storage with versioning"""


    def __init__(self, storage_path: Path = None):
        """__init__ handler."""
        self.storage_path = storage_path or Path(
            "./doctrine/doctrine_core.yaml")
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.db_path = self.storage_path.parent / "doctrine_history.db"
        self.validator = DoctrineValidator()
        self._init_db()

    def _init_db(self):
        """Initialize doctrine history database"""
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS doctrine_versions (
                version_id TEXT PRIMARY KEY,
                doctrine_hash TEXT UNIQUE NOT NULL,
                doctrine_content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by TEXT,
                change_reason TEXT,
                is_active BOOLEAN DEFAULT FALSE
            )
        """)
        self.conn.commit()

    def store_doctrine(self, doctrine: Dict, created_by: str = "system",
                      change_reason: str = "Initial doctrine") -> Tuple[bool, str]:
        """Store doctrine with immutability guarantees"""

        # Validate doctrine
        is_valid, errors = self.validator.validate_doctrine(doctrine)
        if not is_valid:
            return False, f"Doctrine validation failed: {', '.join(errors)}"

        # Create doctrine hash for integrity
        doctrine_str = json.dumps(doctrine, sort_keys=True)
        doctrine_hash = hashlib.sha256(doctrine_str.encode()).hexdigest()

        # Check if this version already exists
        cursor = self.conn.execute(
            "SELECT version_id FROM doctrine_versions WHERE doctrine_hash = ?",
            (doctrine_hash,)
        )
        if cursor.fetchone():
            return False, "Doctrine version already exists"

        # Generate version ID
        version_id = f"doctrine_v_{int(datetime.now().timestamp())}"

        try:
            # Store in database
            self.conn.execute("""
                INSERT INTO doctrine_versions
                (version_id, doctrine_hash, doctrine_content, created_by, change_reason)
                VALUES (?, ?, ?, ?, ?)
            """, (version_id, doctrine_hash, doctrine_str, created_by, change_reason))

            # Deactivate previous versions
            self.conn.execute(
                "UPDATE doctrine_versions SET is_active = FALSE WHERE is_active = TRUE"
            )

            # Activate new version
            self.conn.execute(
                "UPDATE doctrine_versions SET is_active = TRUE WHERE version_id = ?",
                (version_id,))

            # Save to file system as well
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                yaml.dump(doctrine, f, default_flow_style=False,
                          sort_keys=False)

            self.conn.commit()
            return True, version_id

        except Exception as e:
            self.conn.rollback()
            return False, f"Failed to store doctrine: {str(e)}"

    def load_doctrine(self, version_id: str = None) -> Optional[Dict]:
        """Load doctrine from storage"""
        try:
            if version_id:
                # Load specific version
                cursor = self.conn.execute(
                    "SELECT doctrine_content FROM doctrine_versions WHERE version_id = ?",
                    (version_id,))
            else:
                # Load active version
                cursor = self.conn.execute(
                    "SELECT doctrine_content FROM doctrine_versions WHERE is_active = TRUE"
                )

            row = cursor.fetchone()
            if row:
                return json.loads(row[0])

        except Exception as e:
            print(f"Error loading doctrine: {e}")

        return None

    def get_doctrine_history(self) -> List[Dict]:
        """Get doctrine version history"""
        try:
            cursor = self.conn.execute("""
                SELECT version_id, doctrine_hash, created_at, created_by, change_reason, is_active
                FROM doctrine_versions
                ORDER BY created_at DESC
            """)

            history = []
            for row in cursor.fetchall():
                history.append({
                    "version_id": row[0],
                    "hash": row[1],
                    "created_at": row[2],
                    "created_by": row[3],
                    "change_reason": row[4],
                    "is_active": bool(row[5])
                })

            return history

        except Exception as e:
            print(f"Error getting doctrine history: {e}")
            return []

    def validate_integrity(self) -> Tuple[bool, List[str]]:
        """Validate doctrine integrity across all versions"""
        issues = []

        try:
            cursor = self.conn.execute(
                "SELECT version_id, doctrine_hash, doctrine_content FROM doctrine_versions"
            )

            for row in cursor.fetchall():
                version_id, stored_hash, content = row

                # Recalculate hash
                calculated_hash = hashlib.sha256(content.encode()).hexdigest()

                if stored_hash != calculated_hash:
                    issues.append(f"Hash mismatch in version {version_id}")

        except Exception as e:
            issues.append(f"Integrity check failed: {str(e)}")

        return len(issues) == 0, issues


class DoctrineComplianceEngine:
    """__init__ handler."""
    """Real-time doctrine compliance monitoring"""

    def __init__(self, doctrine_storage: DoctrineStorage):
        self.doctrine_storage = doctrine_storage
        self.validator = DoctrineValidator()
        self.compliance_log = []
        self.audit_path = Path("./doctrine/compliance_audit.json")
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)

    def check_compliance(self, action: Dict, context: Dict = None) -> Dict:
        """Check action compliance with current doctrine"""
        doctrine = self.doctrine_storage.load_doctrine()

        if not doctrine:
            return {
                "compliant": False,
                "reason": "No doctrine loaded",
                "severity": "critical"
            }

        # Validate action against doctrine
        is_compliant, violations = self.validator.validate_compliance(
            action, doctrine)

        result = {
            "compliant": is_compliant, "violations": violations,
            "timestamp": datetime.now().isoformat(),
            "action_summary": action.get("summary", "Unknown action"),
            "severity": "high"
            if len(violations) >1 else "medium" if violations else "low"}

        # Log compliance check
        self.compliance_log.append(result)

        # Save audit trail
        self._save_audit()

        return result

    def _save_audit(self):
        """Save compliance audit trail"""
        try:
            # Keep only last 1000 entries
            audit_data = self.compliance_log[-1000:] if len(
                self.compliance_log) > 1000 else self.compliance_log

            with open(self.audit_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "audit_generated": datetime.now().isoformat(),
                    "total_checks": len(audit_data),
                    "compliance_rate": sum(1 for r in audit_data if r["compliant"]) / len(audit_data),
                    "entries": audit_data
                }, f, indent=2)

        except Exception as e:
            print(f"Failed to save compliance audit: {e}")

    def get_compliance_stats(self) -> Dict:
        """Get compliance statistics"""
        if not self.compliance_log:
            return {"total_checks": 0, "compliance_rate": 0.0}

        total_checks = len(self.compliance_log)
        compliant_checks = sum(
            1 for result in self.compliance_log if result["compliant"])
        compliance_rate = compliant_checks / total_checks

        # Severity breakdown
        severity_counts = {}
        for result in self.compliance_log:
            severity = result.get("severity", "unknown")
            severity_counts[severity] = severity_counts.get(severity, 0) + 1

        return {
            "total_checks": total_checks,
            "compliant_checks": compliant_checks,
            "compliance_rate": round(compliance_rate, 3),
            "severity_breakdown": severity_counts,
            "last_check": self.compliance_log[-1]["timestamp"] if self.compliance_log else None
        }

class DoctrineEvolutionEngine:
    """Structured doctrine evolution with governance"""

    def __init__(self, doctrine_storage: DoctrineStorage):
        self.doctrine_storage = doctrine_storage
        self.proposals_path = Path("./doctrine/proposals/")
        self.proposals_path.mkdir(parents=True, exist_ok=True)

    def propose_change(self, proposal: Dict) -> Tuple[bool, str]:
        """Submit doctrine change proposal"""

        required_fields = ["title", "description",
            "changes", "rationale", "proposed_by"]
        for field in required_fields:
            if field not in proposal:
                return False, f"Missing required field: {field}"

        # Generate proposal ID
        proposal_id = f"proposal_{int(datetime.now().timestamp())}"
        proposal_file = self.proposals_path / f"{proposal_id}.json"

        # Add metadata
        proposal.update({
            "proposal_id": proposal_id,
            "status": "pending",
            "submitted_at": datetime.now().isoformat(),
            "votes": {"approve": [], "reject": [], "abstain": []}
        })

        try:
            with open(proposal_file, 'w', encoding='utf-8') as f:
                json.dump(proposal, f, indent=2, default=str)

            return True, proposal_id

        except Exception as e:
            return False, f"Failed to save proposal: {str(e)}"

    def vote_on_proposal(self, proposal_id: str, voter: str, vote: str) -> Tuple[bool, str]:
        """Vote on a doctrine change proposal"""

        if vote not in ["approve", "reject", "abstain"]:
            return False, "Invalid vote type"

        proposal_file = self.proposals_path / f"{proposal_id}.json"

        if not proposal_file.exists():
            return False, "Proposal not found"

        try:
            with open(proposal_file, 'r', encoding='utf-8') as f:
                proposal = json.load(f)

            # Check if already voted
            for vote_type, voters in proposal["votes"].items():
                if voter in voters:
                    return False, f"Already voted: {vote_type}"

            # Add vote
            proposal["votes"][vote].append(voter)
            proposal["last_updated"] = datetime.now().isoformat()

            # Auto-resolve if consensus reached (simple majority)
            total_votes = sum(len(voters)
                              for voters in proposal["votes"].values())
            approve_votes = len(proposal["votes"]["approve"])

            if approve_votes > total_votes / 2:
                proposal["status"] = "approved"
                # Could trigger doctrine update here
            elif len(proposal["votes"]["reject"]) > total_votes / 2:
                proposal["status"] = "rejected"

            with open(proposal_file, 'w', encoding='utf-8') as f:
                json.dump(proposal, f, indent=2, default=str)

            return True, f"Vote recorded: {vote}"

        except Exception as e:
            return False, f"Failed to record vote: {str(e)}"

    def get_pending_proposals(self) -> List[Dict]:
        """Get all pending doctrine change proposals"""
        proposals = []

        for proposal_file in self.proposals_path.glob("*.json"):
            try:
                with open(proposal_file, 'r', encoding='utf-8') as f:
                    proposal = json.load(f)
                    if proposal.get("status") == "pending":
                        proposals.append(proposal)
            except Exception:
                continue

        return proposals

# Core doctrine content
CORE_DOCTRINE = {
    "memory_principles": [
        "ultra_conservative_allocation",
        "context_aware_loading",
        "persistent_state_management",
        "adaptive_resource_usage",
        "memory_efficiency_first"
    ],
    "operational_principles": [
        "autonomous_execution_with_bounds",
        "ethical_ai_governance",
        "continuous_learning_adaptation",
        "human_centric_design",
        "transparency_accountability"
    ],
    "governance_principles": [
        "doctrine_immutability",
        "consensus_driven_changes",
        "audit_trail_maintenance",
        "ethical_boundaries_enforcement",
        "human_oversight_preservation"
    ]
}

def initialize_doctrine_system():
    """Initialize the complete doctrine preservation system"""
    print("📜 Initializing Doctrine Preservation System...")

    # Create storage system
    storage = DoctrineStorage()

    # Store core doctrine
    success, version_id = storage.store_doctrine(
        CORE_DOCTRINE,
        created_by="system_initialization",
        change_reason="Core doctrine establishment"
    )

    if success:
        print(f"✅ Core doctrine stored as version: {version_id}")
    else:
        print(f"❌ Failed to store core doctrine: {version_id}")
        return None

    # Create compliance engine
    compliance = DoctrineComplianceEngine(storage)

    # Create evolution engine
    evolution = DoctrineEvolutionEngine(storage)

    return {
        "storage": storage,
        "compliance": compliance,
        "evolution": evolution
    }

# Global instances
_doctrine_system = None

def get_doctrine_system():
    """Get or initialize doctrine system"""
    global _doctrine_system
    if _doctrine_system is None:
        _doctrine_system = initialize_doctrine_system()
    return _doctrine_system


class DoctrinePreservationSystem:
    """
    Main facade class for the Doctrine Preservation System.
    Provides unified access to storage, compliance, and evolution capabilities.
    """

    def __init__(self):
        system = get_doctrine_system()
        if system is None:
            # Create standalone instances if system init fails
            self.storage = DoctrineStorage()
            self.compliance = DoctrineComplianceEngine(self.storage)
            self.evolution = DoctrineEvolutionEngine(self.storage)
        else:
            self.storage: DoctrineStorage = system["storage"]
            self.compliance: DoctrineComplianceEngine = system["compliance"]
            self.evolution: DoctrineEvolutionEngine = system["evolution"]
        self.validator = DoctrineValidator()

    def load_doctrine(self) -> Dict:
        """Load current doctrine"""
        return self.storage.load_doctrine()

    def save_doctrine(
            self, doctrine: Dict, version: str=None, comment: str="") ->bool:
        """Save doctrine with optional version"""
        return self.storage.save_doctrine(doctrine, version, comment)

    def check_compliance(self, action: Dict) -> Dict:
        """Check action compliance with doctrine"""
        return self.compliance.check_compliance(action)

    def get_doctrine_history(self) -> List[Dict]:
        """Get doctrine version history"""
        return self.storage.get_doctrine_history()

    def validate_doctrine(self, doctrine: Dict) -> Tuple[bool, List[str]]:
        """Validate doctrine structure"""
        return self.validator.validate_doctrine(doctrine)

    def get_system_status(self) -> Dict:
        """Get overall system status"""
        return {
            "storage_ok": self.storage is not None,
            "compliance_ok": self.compliance is not None,
            "evolution_ok": self.evolution is not None,
            "doctrine_loaded": self.load_doctrine() is not None,
            "versions": len(self.get_doctrine_history())
        }


if __name__ == "__main__":
    # Test the doctrine system
    print("📜 Testing Doctrine Preservation System...")

    system = get_doctrine_system()
    if not system:
        print("❌ Failed to initialize doctrine system")
        exit(1)

    storage = system["storage"]
    compliance = system["compliance"]

    # Test doctrine loading
    doctrine = storage.load_doctrine()
    print("Loaded doctrine:", doctrine is not None)

    # Test compliance checking
    test_action = {
        "summary": "Test memory allocation",
        "memory_usage": 100,  # Within limits
        "autonomous_action": False
    }

    compliance_result = compliance.check_compliance(test_action)
    print("Compliance check:", compliance_result["compliant"])

    # Test doctrine history
    history = storage.get_doctrine_history()
    print(f"Doctrine versions: {len(history)}")

    print("✅ Doctrine Preservation System test complete!")
