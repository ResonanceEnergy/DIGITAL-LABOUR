#!/usr/bin/env python3
"""
DIGITAL LABOUR Backlog Management System
Comprehensive task tracking and AI-powered prioritization
"""

import os
import json
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import uuid
import re

class BacklogItem:
    """Represents a single backlog item"""

    def __init__(
            self, title: str, description: str="", category: str="general",
            priority: str="medium", effort: str="medium",
            created_by: str="system", **kwargs):
        self.id = str(uuid.uuid4())
        self.title = title
        self.description = description
        # memory, doctrine, integration, advanced, monitoring, security
        self.category = category
        self.priority = priority  # high, medium, low
        self.effort = effort  # small, medium, large, epic
        self.status = "pending"  # pending, in_progress, completed, blocked
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.created_by = created_by
        self.assigned_to = None
        self.due_date = None
        self.dependencies = []  # List of other backlog item IDs
        self.tags = kwargs.get('tags', [])
        self.doctrine_alignment = {}  # How this aligns with doctrine principles
        self.ai_insights = {}  # AI-generated insights and suggestions
        self.progress_notes = []

    def to_dict(self) -> Dict:
        """Convert to dictionary for storage"""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "category": self.category,
            "priority": self.priority,
            "effort": self.effort,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "created_by": self.created_by,
            "assigned_to": self.assigned_to,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "dependencies": self.dependencies,
            "tags": self.tags,
            "doctrine_alignment": self.doctrine_alignment,
            "ai_insights": self.ai_insights,
            "progress_notes": self.progress_notes
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'BacklogItem':
        """Create from dictionary"""
        item = cls(
            title=data["title"],
            description=data.get("description", ""),
            category=data.get("category", "general"),
            priority=data.get("priority", "medium"),
            effort=data.get("effort", "medium"),
            created_by=data.get("created_by", "system")
        )

        # Override generated values with stored ones
        item.id = data["id"]
        item.status = data.get("status", "pending")
        item.created_at = datetime.fromisoformat(data["created_at"])
        item.updated_at = datetime.fromisoformat(data["updated_at"])
        item.assigned_to = data.get("assigned_to")
        item.due_date = datetime.fromisoformat(
            data["due_date"]) if data.get("due_date") else None
        item.dependencies = data.get("dependencies", [])
        item.tags = data.get("tags", [])
        item.doctrine_alignment = data.get("doctrine_alignment", {})
        item.ai_insights = data.get("ai_insights", {})
        item.progress_notes = data.get("progress_notes", [])

        return item

    def update_status(self, new_status: str, note: str = ""):
        """Update item status with progress note"""
        self.status = new_status
        self.updated_at = datetime.now()

        if note:
            self.progress_notes.append({
                "timestamp": datetime.now().isoformat(),
                "status_change": f"→ {new_status}",
                "note": note
            })

    def add_dependency(self, dependency_id: str):
        """Add a dependency"""
        if dependency_id not in self.dependencies:
            self.dependencies.append(dependency_id)
            self.updated_at = datetime.now()

    def calculate_priority_score(self) -> float:
        """Calculate AI-powered priority score"""
        base_score = {"high": 1.0, "medium": 0.6, "low": 0.3}[self.priority]

        # Age factor (older items get slight boost)
        age_days = (datetime.now() - self.created_at).days
        age_factor = min(1.0, age_days / 30) * 0.1  # Max 10% boost

        # Dependency factor (items blocking others get boost)
        dependency_factor = len(self.dependencies) * 0.05  # 5% per dependency

        # Doctrine alignment factor
        doctrine_factor = 0.0
        if self.doctrine_alignment:
            doctrine_factor = sum(
                self.doctrine_alignment.values()) / len(self.doctrine_alignment) * 0.1

        # AI insights factor
        ai_factor = self.ai_insights.get("priority_boost", 0.0)

        return min(2.0, base_score +age_factor +dependency_factor +
                   doctrine_factor +ai_factor)

class BacklogManager:
    """Manages the complete backlog system"""


    def __init__(self, storage_path: Path = None):
        """__init__ handler."""
        self.storage_path = storage_path or Path("./backlog/backlog.db")
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

        # Cache for performance
        self._item_cache = {}
        self._last_cache_update = None

    def _init_db(self):
        """Initialize SQLite database for backlog storage"""
        self.conn = sqlite3.connect(str(self.storage_path))
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS backlog_items (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                category TEXT DEFAULT 'general',
                priority TEXT DEFAULT 'medium',
                effort TEXT DEFAULT 'medium',
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by TEXT DEFAULT 'system',
                assigned_to TEXT,
                due_date TIMESTAMP,
                dependencies TEXT,  -- JSON array
                tags TEXT,  -- JSON array
                doctrine_alignment TEXT,  -- JSON object
                ai_insights TEXT,  -- JSON object
                progress_notes TEXT  -- JSON array
            )
        """)

        # Create indexes for performance
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_status ON backlog_items(status)")
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_priority ON backlog_items(priority)")
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_category ON backlog_items(category)")
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_due_date ON backlog_items(due_date)")

        self.conn.commit()

    def create_item(
            self, title: str, description: str="", **kwargs) ->BacklogItem:
        """Create a new backlog item"""
        item = BacklogItem(title, description, **kwargs)

        # Store in database
        self.conn.execute("""
            INSERT INTO backlog_items
            (id, title, description, category, priority, effort, status,
             created_at, updated_at, created_by, assigned_to, due_date,
             dependencies, tags, doctrine_alignment, ai_insights, progress_notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            item.id, item.title, item.description, item.category,
            item.priority, item.effort, item.status,
            item.created_at.isoformat(), item.updated_at.isoformat(),
            item.created_by, item.assigned_to,
            item.due_date.isoformat() if item.due_date else None,
            json.dumps(item.dependencies), json.dumps(item.tags),
            json.dumps(item.doctrine_alignment), json.dumps(item.ai_insights),
            json.dumps(item.progress_notes)
        ))

        self.conn.commit()

        # Update cache
        self._item_cache[item.id] = item

        return item

    def get_item(self, item_id: str) -> Optional[BacklogItem]:
        """Get a backlog item by ID"""
        # Check cache first
        if item_id in self._item_cache:
            return self._item_cache[item_id]

        cursor = self.conn.execute(
            "SELECT * FROM backlog_items WHERE id = ?", (item_id,))
        row = cursor.fetchone()

        if row:
            # Convert row to dict
            columns = [desc[0] for desc in cursor.description]
            data = dict(zip(columns, row))

            # Parse JSON fields
            for json_field in [
                'dependencies', 'tags', 'doctrine_alignment', 'ai_insights',
                'progress_notes']:
                if data[json_field]:
                    data[json_field] = json.loads(data[json_field])

            item = BacklogItem.from_dict(data)
            self._item_cache[item_id] = item
            return item

        return None

    def update_item(self, item_id: str, **updates) -> bool:
        """Update a backlog item"""
        item = self.get_item(item_id)
        if not item:
            return False

        # Update item attributes
        for key, value in updates.items():
            if hasattr(item, key):
                setattr(item, key, value)

        item.updated_at = datetime.now()

        # Update database
        self.conn.execute("""
            UPDATE backlog_items SET
                title = ?, description = ?, category = ?, priority = ?,
                effort = ?, status = ?, updated_at = ?, assigned_to = ?,
                due_date = ?, dependencies = ?, tags = ?,
                doctrine_alignment = ?, ai_insights = ?, progress_notes = ?
            WHERE id = ?
        """, (
            item.title, item.description, item.category, item.priority,
            item.effort, item.status, item.updated_at.isoformat(),
            item.assigned_to,
            item.due_date.isoformat() if item.due_date else None,
            json.dumps(item.dependencies), json.dumps(item.tags),
            json.dumps(item.doctrine_alignment), json.dumps(item.ai_insights),
            json.dumps(item.progress_notes),
            item.id
        ))

        self.conn.commit()

        # Update cache
        self._item_cache[item_id] = item

        return True

    def delete_item(self, item_id: str) -> bool:
        """Delete a backlog item"""
        result = self.conn.execute(
            "DELETE FROM backlog_items WHERE id = ?", (item_id,))
        self.conn.commit()

        if result.rowcount > 0:
            # Remove from cache
            self._item_cache.pop(item_id, None)
            return True

        return False

    def query_items(
            self, filters: Dict=None, sort_by: str="priority_score",
            limit: int=None) ->List[BacklogItem]:
        """Query backlog items with filters"""

        query = "SELECT * FROM backlog_items"
        params = []

        where_clauses = []

        if filters:
            if "status" in filters:
                where_clauses.append("status = ?")
                params.append(filters["status"])

            if "category" in filters:
                where_clauses.append("category = ?")
                params.append(filters["category"])

            if "priority" in filters:
                where_clauses.append("priority = ?")
                params.append(filters["priority"])

            if "assigned_to" in filters:
                where_clauses.append("assigned_to = ?")
                params.append(filters["assigned_to"])

            if "due_before" in filters:
                where_clauses.append("due_date < ?")
                params.append(filters["due_before"].isoformat())

        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)

        # Sorting
        if sort_by == "priority_score":
            # This would require calculating priority scores
            # For now, sort by priority then created_at
            query += " ORDER BY CASE priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 WHEN 'low' THEN 3 END, created_at DESC"
        elif sort_by == "created_at":
            query += " ORDER BY created_at DESC"
        elif sort_by == "due_date":
            query += " ORDER BY due_date ASC NULLS LAST"

        if limit:
            query += f" LIMIT {limit}"

        cursor = self.conn.execute(query, params)
        rows = cursor.fetchall()

        items = []
        for row in rows:
            columns = [desc[0] for desc in cursor.description]
            data = dict(zip(columns, row))

            # Parse JSON fields
            for json_field in [
                'dependencies', 'tags', 'doctrine_alignment', 'ai_insights',
                'progress_notes']:
                if data[json_field]:
                    data[json_field] = json.loads(data[json_field])

            items.append(BacklogItem.from_dict(data))

        return items

    def get_stats(self) -> Dict:
        """Get comprehensive backlog statistics"""
        stats = {
            "total_items": 0,
            "by_status": {},
            "by_priority": {},
            "by_category": {},
            "overdue_items": 0,
            "completion_rate": 0.0
        }

        # Get counts by status
        cursor = self.conn.execute(
            "SELECT status, COUNT(*) FROM backlog_items GROUP BY status")
        for row in cursor.fetchall():
            stats["by_status"][row[0]] = row[1]
            stats["total_items"] += row[1]

        # Get counts by priority
        cursor = self.conn.execute(
            "SELECT priority, COUNT(*) FROM backlog_items GROUP BY priority")
        for row in cursor.fetchall():
            stats["by_priority"][row[0]] = row[1]

        # Get counts by category
        cursor = self.conn.execute(
            "SELECT category, COUNT(*) FROM backlog_items GROUP BY category")
        for row in cursor.fetchall():
            stats["by_category"][row[0]] = row[1]

        # Count overdue items
        now = datetime.now().isoformat()
        cursor = self.conn.execute(
            "SELECT COUNT(*) FROM backlog_items WHERE due_date < ? AND status != 'completed'",
            (now,))
        stats["overdue_items"] = cursor.fetchone()[0]

        # Calculate completion rate
        completed = stats["by_status"].get("completed", 0)
        if stats["total_items"] > 0:
            stats["completion_rate"] = round(
                completed / stats["total_items"], 3)

        return stats

    def generate_ai_insights(self, item: BacklogItem) -> Dict:
        """Generate AI-powered insights for a backlog item"""
        insights = {
            "estimated_effort_days": self._estimate_effort_days(item),
            "priority_boost": self._calculate_priority_boost(item),
            "dependency_risk": self._assess_dependency_risk(item),
            "suggested_tags": self._suggest_tags(item),
            "similar_items": self._find_similar_items(item)
        }

        return insights

    def _estimate_effort_days(self, item: BacklogItem) -> float:
        """Estimate effort in days based on item characteristics"""
        base_effort = {"small": 1, "medium": 5,
            "large": 15, "epic": 45}[item.effort]

        # Adjust based on category complexity
        complexity_multipliers = {
            "memory": 1.2,  # Memory work is complex
            "doctrine": 1.5,  # Doctrine changes require care
            "security": 1.3,  # Security work needs thoroughness
            "integration": 1.4,  # Integration work has dependencies
        }

        multiplier = complexity_multipliers.get(item.category, 1.0)

        return round(base_effort * multiplier, 1)

    def _calculate_priority_boost(self, item: BacklogItem) -> float:
        """Calculate AI-suggested priority boost"""
        boost = 0.0

        # Boost for items blocking others
        if len(item.dependencies) > 2:
            boost += 0.2

        # Boost for overdue items
        if item.due_date and item.due_date < datetime.now():
            boost += 0.3

        # Boost for critical categories
        if item.category in ["security", "doctrine"]:
            boost += 0.1

        return min(0.5, boost)  # Max 50% boost

    def _assess_dependency_risk(self, item: BacklogItem) -> str:
        """Assess dependency risk level"""
        dep_count = len(item.dependencies)

        if dep_count == 0:
            return "low"
        elif dep_count <= 2:
            return "medium"
        else:
            return "high"

    def _suggest_tags(self, item: BacklogItem) -> List[str]:
        """Suggest relevant tags based on item content"""
        tags = []

        text = f"{item.title} {item.description}".lower()

        if "memory" in text:
            tags.append("memory-optimization")
        if "doctrine" in text:
            tags.append("doctrine-compliance")
        if "security" in text or "encrypt" in text:
            tags.append("security")
        if "api" in text or "integration" in text:
            tags.append("integration")
        if "test" in text or "validation" in text:
            tags.append("testing")

        return tags[:3]  # Max 3 suggestions

    def _find_similar_items(self, item: BacklogItem) -> List[str]:
        """Find similar backlog items"""
        # Simple keyword matching for now
        keywords = re.findall(r'\b\w+\b', f"{item.title} {item.description}")

        similar_ids = []
        for keyword in keywords[:5]:  # Check first 5 keywords
            cursor = self.conn.execute("""
                SELECT id FROM backlog_items
                WHERE (title LIKE ? OR description LIKE ?)
                AND id != ?
                LIMIT 2
            """, (f"%{keyword}%", f"%{keyword}%", item.id))

            for row in cursor.fetchall():
                if row[0] not in similar_ids:
                    similar_ids.append(row[0])

        return similar_ids[:3]  # Max 3 similar items

def initialize_backlog_system():
    """Initialize the backlog management system with core items"""
    print("📋 Initializing Backlog Management System...")

    manager = BacklogManager()

    # Create core backlog items from the implementation plan
    core_items = [
        {
            "title": "Implement Multi-Layer Memory Architecture",
            "description": "Create ephemeral, session, and persistent memory layers with automatic cleanup",
            "category": "memory",
            "priority": "high",
            "effort": "large",
            "tags": ["memory-optimization", "architecture"]
        },
        {
            "title": "Establish Doctrine Storage & Validation",
            "description": "Create immutable doctrine storage with compliance checking and evolution framework",
            "category": "doctrine",
            "priority": "high",
            "effort": "large",
            "tags": ["doctrine", "compliance"]
        },
        {
            "title": "Build AI-Powered Backlog Intelligence",
            "description": "Implement intelligent prioritization, dependency analysis, and progress tracking",
            "category": "integration",
            "priority": "medium",
            "effort": "large",
            "tags": ["ai", "prioritization"]
        },
        {
            "title": "Complete Financial Reporting System",
            "description": "Finish income statements, balance sheets, and automated reporting in AAC",
            "category": "integration",
            "priority": "high",
            "effort": "medium",
            "tags": ["aac", "reporting"]
        },
        {
            "title": "Implement NCL Core Cognitive Layer",
            "description": "Deploy the Neural Cognitive Layer as the central AI processing system",
            "category": "integration",
            "priority": "critical",
            "effort": "epic",
            "tags": ["ncl", "ai", "critical"]
        }
    ]

    created_items = []
    for item_data in core_items:
        item = manager.create_item(**item_data)

        # Generate AI insights
        insights = manager.generate_ai_insights(item)
        manager.update_item(item.id, ai_insights=insights)

        created_items.append(item)
        print(f"✅ Created backlog item: {item.title}")

    return manager

# Global instance
_backlog_manager = None

def get_backlog_manager():
    """Get or initialize backlog manager"""
    global _backlog_manager
    if _backlog_manager is None:
        _backlog_manager = initialize_backlog_system()
    return _backlog_manager

if __name__ == "__main__":
    # Test the backlog system
    print("📋 Testing Backlog Management System...")

    manager = get_backlog_manager()

    # Create a test item
    test_item = manager.create_item(
        title="Test Memory Optimization",
        description="Implement advanced memory compression algorithms",
        category="memory",
        priority="high",
        effort="medium"
    )

    print(f"✅ Created test item: {test_item.id}")

    # Generate AI insights
    insights = manager.generate_ai_insights(test_item)
    manager.update_item(test_item.id, ai_insights=insights)

    print(f"AI Insights: {insights}")

    # Get stats
    stats = manager.get_stats()
    print(f"Backlog Stats: {stats}")

    print("✅ Backlog Management System test complete!")
