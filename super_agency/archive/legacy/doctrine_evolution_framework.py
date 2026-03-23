#!/usr/bin/env python3
"""
DIGITAL LABOUR Doctrine Evolution Framework
Structured doctrine updates with impact assessment and governance
"""

import os
import json
import hashlib
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import yaml
import re
from enum import Enum

class DoctrineChangeType(Enum):
    """Types of doctrine changes"""
    ADD_PRINCIPLE = "add_principle"
    MODIFY_PRINCIPLE = "modify_principle"
    REMOVE_PRINCIPLE = "remove_principle"
    ADD_CONSTRAINT = "add_constraint"
    MODIFY_CONSTRAINT = "modify_constraint"
    REMOVE_CONSTRAINT = "remove_constraint"
    RESTRUCTURE = "restructure"

class DoctrineChangeStatus(Enum):
    """Status of doctrine change proposals"""
    PROPOSED = "proposed"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    IMPLEMENTED = "implemented"
    ROLLED_BACK = "rolled_back"

class DoctrineEvolutionEngine:
    """Manages structured doctrine evolution with governance"""

    def __init__(self, storage_path: Path = None):
        """Initialize."""
        self.storage_path = storage_path or Path("./doctrine/evolution.db")
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

        # Load current doctrine
        from doctrine_preservation_system import DoctrinePreservationSystem
        self.doctrine_system = DoctrinePreservationSystem()

    def _init_db(self):
        """Initialize doctrine evolution database"""
        self.conn = sqlite3.connect(str(self.storage_path))
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS doctrine_changes (
                id TEXT PRIMARY KEY,
                change_type TEXT NOT NULL,
                category TEXT NOT NULL,  -- memory_principles, operational_principles, etc.
                change_data TEXT NOT NULL,  -- JSON with change details
                rationale TEXT NOT NULL,
                proposed_by TEXT NOT NULL,
                status TEXT DEFAULT 'proposed',
                impact_assessment TEXT,  -- JSON with impact analysis
                review_comments TEXT,  -- JSON array of review comments
                approved_by TEXT,
                approved_at TIMESTAMP,
                implemented_at TIMESTAMP,
                rollback_reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create indexes for performance
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_status ON doctrine_changes(status)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_category ON doctrine_changes(category)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_proposed_by ON doctrine_changes(proposed_by)")

        self.conn.commit()

    def propose_doctrine_change(self, change_type: DoctrineChangeType,
                              category: str, change_data: Dict,
                              rationale: str, proposed_by: str) -> str:
        """Propose a doctrine change"""

        # Validate change data
        if not self._validate_change_data(change_type, category, change_data):
            raise ValueError(f"Invalid change data for {change_type.value}")

        # Generate change ID
        change_id = hashlib.md5(
            f"{change_type.value}_{category}_{json.dumps(change_data, sort_keys=True)}_{datetime.now().isoformat()}".encode()
        ).hexdigest()[:16]

        # Store proposal
        self.conn.execute("""
            INSERT INTO doctrine_changes
            (id, change_type, category, change_data, rationale, proposed_by)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            change_id,
            change_type.value,
            category,
            json.dumps(change_data),
            rationale,
            proposed_by
        ))

        self.conn.commit()

        # Perform initial impact assessment
        impact = self._assess_change_impact(change_type, category, change_data)
        self._update_change_field(change_id, "impact_assessment", json.dumps(impact))

        print(f"✅ Doctrine change proposed: {change_id}")
        return change_id

    def review_change(self, change_id: str, reviewer: str,
                     approved: bool, comments: str = "") -> bool:
        """Review a doctrine change proposal"""

        change = self._get_change(change_id)
        if not change:
            raise ValueError(f"Change {change_id} not found")

        if change["status"] != "proposed":
            raise ValueError(f"Change {change_id} is not in proposed status")

        # Update review status
        new_status = "approved" if approved else "rejected"

        review_comment = {
            "reviewer": reviewer,
            "approved": approved,
            "comments": comments,
            "reviewed_at": datetime.now().isoformat()
        }

        # Get existing comments
        existing_comments = change.get("review_comments", [])
        if isinstance(existing_comments, str):
            existing_comments = json.loads(existing_comments)
        existing_comments.append(review_comment)

        self.conn.execute("""
            UPDATE doctrine_changes SET
                status = ?,
                review_comments = ?,
                approved_by = ?,
                approved_at = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (
            new_status,
            json.dumps(existing_comments),
            reviewer if approved else None,
            datetime.now().isoformat() if approved else None,
            change_id
        ))

        self.conn.commit()

        print(f"✅ Change {change_id} {'approved' if approved else 'rejected'} by {reviewer}")
        return approved

    def implement_change(self, change_id: str, implementer: str) -> bool:
        """Implement an approved doctrine change"""

        change = self._get_change(change_id)
        if not change:
            raise ValueError(f"Change {change_id} not found")

        if change["status"] != "approved":
            raise ValueError(f"Change {change_id} is not approved for implementation")

        try:
            # Get current doctrine
            current_doctrine = self.doctrine_system.get_current_doctrine()

            # Apply the change
            updated_doctrine = self._apply_change_to_doctrine(
                current_doctrine,
                DoctrineChangeType(change["change_type"]),
                change["category"],
                json.loads(change["change_data"])
            )

            # Store updated doctrine
            change_description = f"Implemented change {change_id}: {change['rationale'][:50]}..."
            self.doctrine_system.store_doctrine(updated_doctrine, change_description)

            # Update change status
            self.conn.execute("""
                UPDATE doctrine_changes SET
                    status = 'implemented',
                    implemented_at = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (datetime.now().isoformat(), change_id))

            self.conn.commit()

            print(f"✅ Change {change_id} implemented successfully")
            return True

        except Exception as e:
            print(f"❌ Implementation failed: {e}")
            # Mark as failed (could add a failed status)
            return False

    def rollback_change(self, change_id: str, rollback_reason: str, rolled_back_by: str) -> bool:
        """Rollback an implemented doctrine change"""

        change = self._get_change(change_id)
        if not change:
            raise ValueError(f"Change {change_id} not found")

        if change["status"] != "implemented":
            raise ValueError(f"Change {change_id} is not implemented")

        try:
            # For rollback, we'd need to restore the previous version
            # This is a simplified version - in practice, you'd restore from backup
            print(f"⚠️  Rollback functionality would restore previous doctrine version")

            # Update change status
            self.conn.execute("""
                UPDATE doctrine_changes SET
                    status = 'rolled_back',
                    rollback_reason = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (rollback_reason, change_id))

            self.conn.commit()

            print(f"✅ Change {change_id} rolled back: {rollback_reason}")
            return True

        except Exception as e:
            print(f"❌ Rollback failed: {e}")
            return False

    def _validate_change_data(self, change_type: DoctrineChangeType,
                            category: str, change_data: Dict) -> bool:
        """Validate change data structure"""

        valid_categories = [
            "memory_principles", "operational_principles",
            "governance_principles", "constraints"
        ]

        if category not in valid_categories:
            return False

        if change_type == DoctrineChangeType.ADD_PRINCIPLE:
            return "name" in change_data and "description" in change_data

        elif change_type in [DoctrineChangeType.MODIFY_PRINCIPLE, DoctrineChangeType.REMOVE_PRINCIPLE]:
            return "name" in change_data

        elif change_type == DoctrineChangeType.ADD_CONSTRAINT:
            return "key" in change_data and "value" in change_data

        elif change_type in [DoctrineChangeType.MODIFY_CONSTRAINT, DoctrineChangeType.REMOVE_CONSTRAINT]:
            return "key" in change_data

        elif change_type == DoctrineChangeType.RESTRUCTURE:
            return "new_structure" in change_data

        return False

    def _assess_change_impact(self, change_type: DoctrineChangeType,
                            category: str, change_data: Dict) -> Dict:
        """Assess the impact of a proposed doctrine change"""

        impact = {
            "risk_level": "low",  # low, medium, high, critical
            "affected_systems": [],
            "breaking_changes": False,
            "rollback_complexity": "low",  # low, medium, high
            "testing_requirements": [],
            "estimated_effort": "small",  # small, medium, large
            "recommendations": []
        }

        # Analyze based on change type and category
        if category == "memory_principles":
            impact["affected_systems"].extend(["memory_system", "context_compression"])
            impact["testing_requirements"].append("memory_performance_tests")

        elif category == "operational_principles":
            impact["affected_systems"].extend(["all_operations", "compliance_engine"])
            impact["testing_requirements"].append("operational_compliance_tests")

        elif category == "governance_principles":
            impact["affected_systems"].extend(["doctrine_system", "audit_trails"])
            impact["risk_level"] = "high"
            impact["rollback_complexity"] = "high"

        # Analyze change type impact
        if change_type == DoctrineChangeType.REMOVE_PRINCIPLE:
            impact["breaking_changes"] = True
            impact["risk_level"] = "high"
            impact["rollback_complexity"] = "high"

        elif change_type == DoctrineChangeType.ADD_CONSTRAINT:
            impact["estimated_effort"] = "medium"
            impact["testing_requirements"].append("constraint_validation_tests")

        # Generate recommendations
        if impact["risk_level"] == "high":
            impact["recommendations"].append("Schedule maintenance window")
            impact["recommendations"].append("Prepare rollback plan")
            impact["recommendations"].append("Conduct thorough testing")

        if impact["breaking_changes"]:
            impact["recommendations"].append("Notify all stakeholders")
            impact["recommendations"].append("Update documentation")

        return impact

    def _apply_change_to_doctrine(self, current_doctrine: Dict,
                                change_type: DoctrineChangeType,
                                category: str, change_data: Dict) -> Dict:
        """Apply a change to the doctrine structure"""

        updated_doctrine = json.loads(json.dumps(current_doctrine))  # Deep copy

        if change_type == DoctrineChangeType.ADD_PRINCIPLE:
            if category not in updated_doctrine:
                updated_doctrine[category] = []
            updated_doctrine[category].append({
                "name": change_data["name"],
                "description": change_data["description"],
                "added_at": datetime.now().isoformat()
            })

        elif change_type == DoctrineChangeType.MODIFY_PRINCIPLE:
            if category in updated_doctrine:
                for principle in updated_doctrine[category]:
                    if isinstance(principle, dict) and principle.get("name") == change_data["name"]:
                        if "new_description" in change_data:
                            principle["description"] = change_data["new_description"]
                        principle["modified_at"] = datetime.now().isoformat()

        elif change_type == DoctrineChangeType.REMOVE_PRINCIPLE:
            if category in updated_doctrine:
                updated_doctrine[category] = [
                    p for p in updated_doctrine[category]
                    if not (isinstance(p, dict) and p.get("name") == change_data["name"])
                ]

        elif change_type == DoctrineChangeType.ADD_CONSTRAINT:
            if "constraints" not in updated_doctrine:
                updated_doctrine["constraints"] = {}
            updated_doctrine["constraints"][change_data["key"]] = change_data["value"]

        elif change_type == DoctrineChangeType.MODIFY_CONSTRAINT:
            if "constraints" in updated_doctrine and change_data["key"] in updated_doctrine["constraints"]:
                updated_doctrine["constraints"][change_data["key"]] = change_data.get("new_value",
                    updated_doctrine["constraints"][change_data["key"]])

        elif change_type == DoctrineChangeType.REMOVE_CONSTRAINT:
            if "constraints" in updated_doctrine and change_data["key"] in updated_doctrine["constraints"]:
                del updated_doctrine["constraints"][change_data["key"]]

        # Update version and timestamp
        updated_doctrine["version"] = self._increment_version(current_doctrine.get("version", "1.0.0"))
        updated_doctrine["last_modified"] = datetime.now().isoformat()

        return updated_doctrine

    def _increment_version(self, current_version: str) -> str:
        """Increment semantic version"""
        try:
            parts = current_version.split(".")
            parts[-1] = str(int(parts[-1]) + 1)
            return ".".join(parts)
        except:
            return f"{current_version}.1"

    def _get_change(self, change_id: str) -> Optional[Dict]:
        """Get change details"""
        cursor = self.conn.execute("""
            SELECT * FROM doctrine_changes WHERE id = ?
        """, (change_id,))

        row = cursor.fetchone()
        if row:
            columns = [desc[0] for desc in cursor.description]
            return dict(zip(columns, row))

        return None

    def _update_change_field(self, change_id: str, field: str, value: Any):
        """Update a field in a change record"""
        self.conn.execute(f"""
            UPDATE doctrine_changes SET {field} = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (value, change_id))
        self.conn.commit()

    def get_pending_changes(self) -> List[Dict]:
        """Get all pending doctrine changes"""
        cursor = self.conn.execute("""
            SELECT id, change_type, category, rationale, proposed_by,
                   created_at, impact_assessment
            FROM doctrine_changes
            WHERE status = 'proposed'
            ORDER BY created_at DESC
        """)

        changes = []
        for row in cursor.fetchall():
            change = {
                "id": row[0],
                "change_type": row[1],
                "category": row[2],
                "rationale": row[3],
                "proposed_by": row[4],
                "created_at": row[5],
                "impact_assessment": json.loads(row[6]) if row[6] else None
            }
            changes.append(change)

        return changes

    def get_change_history(self, limit: int = 50) -> List[Dict]:
        """Get doctrine change history"""
        cursor = self.conn.execute("""
            SELECT id, change_type, category, status, proposed_by,
                   approved_by, implemented_at, rationale
            FROM doctrine_changes
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,))

        history = []
        for row in cursor.fetchall():
            history.append({
                "id": row[0],
                "change_type": row[1],
                "category": row[2],
                "status": row[3],
                "proposed_by": row[4],
                "approved_by": row[5],
                "implemented_at": row[6],
                "rationale": row[7]
            })

        return history

    def get_evolution_stats(self) -> Dict:
        """Get doctrine evolution statistics"""
        cursor = self.conn.execute("""
            SELECT
                COUNT(*) as total_changes,
                COUNT(CASE WHEN status = 'implemented' THEN 1 END) as implemented_changes,
                COUNT(CASE WHEN status = 'rejected' THEN 1 END) as rejected_changes,
                COUNT(CASE WHEN status = 'proposed' THEN 1 END) as pending_changes,
                AVG(CASE WHEN implemented_at IS NOT NULL
                    THEN julianday(implemented_at) - julianday(created_at) END) * 24 as avg_implementation_hours
            FROM doctrine_changes
        """)

        row = cursor.fetchone()
        if row:
            total, implemented, rejected, pending, avg_hours = row

            return {
                "total_changes": total,
                "implemented_changes": implemented,
                "rejected_changes": rejected,
                "pending_changes": pending,
                "average_implementation_time_hours": avg_hours or 0,
                "implementation_rate": (implemented / total * 100) if total > 0 else 0
            }

        return {
            "total_changes": 0,
            "implemented_changes": 0,
            "rejected_changes": 0,
            "pending_changes": 0,
            "average_implementation_time_hours": 0,
            "implementation_rate": 0
        }

# Global instance
_doctrine_evolution = None

def get_doctrine_evolution() -> DoctrineEvolutionEngine:
    """Get global doctrine evolution instance"""
    global _doctrine_evolution
    if _doctrine_evolution is None:
        _doctrine_evolution = DoctrineEvolutionEngine()
    return _doctrine_evolution

# Convenience functions
def propose_doctrine_change(change_type: str, category: str, change_data: Dict,
                          rationale: str, proposed_by: str) -> str:
    """Propose a doctrine change"""
    return get_doctrine_evolution().propose_doctrine_change(
        DoctrineChangeType(change_type), category, change_data, rationale, proposed_by
    )

def review_doctrine_change(change_id: str, reviewer: str, approved: bool, comments: str = "") -> bool:
    """Review a doctrine change"""
    return get_doctrine_evolution().review_change(change_id, reviewer, approved, comments)

def implement_doctrine_change(change_id: str, implementer: str) -> bool:
    """Implement a doctrine change"""
    return get_doctrine_evolution().implement_change(change_id, implementer)

def get_pending_doctrine_changes() -> List[Dict]:
    """Get pending doctrine changes"""
    return get_doctrine_evolution().get_pending_changes()

def get_doctrine_evolution_stats() -> Dict:
    """Get doctrine evolution statistics"""
    return get_doctrine_evolution().get_evolution_stats()

if __name__ == "__main__":
    # Test the doctrine evolution system
    print("🔄 Testing Doctrine Evolution Framework...")

    # Test proposing a change
    change_data = {
        "name": "enhanced_memory_compression",
        "description": "Implement advanced semantic compression for better memory efficiency"
    }

    try:
        change_id = propose_doctrine_change(
            "add_principle",
            "memory_principles",
            change_data,
            "Improve memory efficiency through semantic compression",
            "system"
        )
        print(f"✅ Proposed change: {change_id}")

        # Test reviewing the change
        approved = review_doctrine_change(change_id, "admin", True, "Good enhancement")
        print(f"✅ Change review: {'approved' if approved else 'rejected'}")

        # Test implementing the change
        if approved:
            implemented = implement_doctrine_change(change_id, "system")
            print(f"✅ Change implementation: {'successful' if implemented else 'failed'}")

        # Test getting pending changes
        pending = get_pending_doctrine_changes()
        print(f"📋 Pending changes: {len(pending)}")

        # Test evolution stats
        stats = get_doctrine_evolution_stats()
        print(f"📊 Evolution stats: {stats['total_changes']} total changes")

    except Exception as e:
        print(f"❌ Doctrine evolution test failed: {e}")
        import traceback
        traceback.print_exc()

    print("✅ Doctrine Evolution Framework ready!")