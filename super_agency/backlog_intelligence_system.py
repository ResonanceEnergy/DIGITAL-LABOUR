#!/usr/bin/env python3
"""
DIGITAL LABOUR Backlog Intelligence System
AI-powered priority suggestions and dependency optimization
"""

import os
import json
import sqlite3
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Set
import re
from enum import Enum
from collections import defaultdict, deque

class PriorityLevel(Enum):
    """Priority levels for backlog items"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    BACKLOG = "backlog"

class IntelligenceEngine:
    """AI-powered backlog intelligence and optimization"""

    def __init__(self, storage_path: Path = None):
        """Initialize."""
        self.storage_path = storage_path or Path("./backlog/intelligence.db")
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

        # Load existing backlog manager
        from backlog_management_system import BacklogManager
        self.backlog_manager = BacklogManager()

    def _init_db(self):
        """Initialize intelligence database"""
        self.conn = sqlite3.connect(str(self.storage_path))
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS intelligence_patterns (
                id TEXT PRIMARY KEY,
                pattern_type TEXT NOT NULL,
                pattern_data TEXT NOT NULL,
                confidence REAL DEFAULT 0.0,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS priority_suggestions (
                item_id TEXT PRIMARY KEY,
                suggested_priority TEXT NOT NULL,
                confidence REAL NOT NULL,
                reasoning TEXT NOT NULL,
                factors TEXT NOT NULL,  -- JSON array of influencing factors
                generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS dependency_insights (
                id TEXT PRIMARY KEY,
                item_id TEXT NOT NULL,
                dependency_id TEXT NOT NULL,
                insight_type TEXT NOT NULL,
                strength REAL NOT NULL,
                reasoning TEXT NOT NULL,
                discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create indexes
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_pattern_type ON intelligence_patterns(pattern_type)")
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_item_priority ON priority_suggestions(item_id)")
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_dep_item ON dependency_insights(item_id)")

        self.conn.commit()

    def analyze_backlog_patterns(self) -> Dict[str, Any]:
        """Analyze patterns in the backlog for intelligence insights"""

        items = self.backlog_manager.get_all_items()
        if not items:
            return {"patterns": [], "insights": []}

        patterns = {
            "completion_rates": self._analyze_completion_rates(items),
            "category_patterns": self._analyze_category_patterns(items),
            "effort_patterns": self._analyze_effort_patterns(items),
            "dependency_patterns": self._analyze_dependency_patterns(items),
            "time_patterns": self._analyze_time_patterns(items)
        }

        # Store patterns for future learning
        self._store_patterns("completion_rates", patterns["completion_rates"])
        self._store_patterns("category_patterns",
                             patterns["category_patterns"])
        self._store_patterns("effort_patterns", patterns["effort_patterns"])
        self._store_patterns("dependency_patterns",
                             patterns["dependency_patterns"])
        self._store_patterns("time_patterns", patterns["time_patterns"])

        insights = self._generate_insights_from_patterns(patterns)

        return {
            "patterns": patterns,
            "insights": insights,
            "analyzed_items": len(items)
        }

    def _analyze_completion_rates(self, items: List) -> Dict[str, Any]:
        """Analyze completion rates by various factors"""

        completed = [item for item in items if item.status == "completed"]
        total = len(items)

        if total == 0:
            return {"completion_rate": 0.0}

        completion_rate = len(completed) / total

        # By priority
        priority_completion = defaultdict(lambda: {"completed": 0, "total": 0})
        for item in items:
            priority_completion[item.priority]["total"] += 1
            if item.status == "completed":
                priority_completion[item.priority]["completed"] += 1

        priority_rates = {}
        for priority, counts in priority_completion.items():
            if counts["total"] > 0:
                priority_rates[priority] = counts["completed"] / \
                    counts["total"]

        # By category
        category_completion = defaultdict(lambda: {"completed": 0, "total": 0})
        for item in items:
            category_completion[item.category]["total"] += 1
            if item.status == "completed":
                category_completion[item.category]["completed"] += 1

        category_rates = {}
        for category, counts in category_completion.items():
            if counts["total"] > 0:
                category_rates[category] = counts["completed"] / \
                    counts["total"]

        return {
            "overall_completion_rate": completion_rate,
            "priority_completion_rates": dict(priority_rates),
            "category_completion_rates": dict(category_rates)
        }

    def _analyze_category_patterns(self, items: List) -> Dict[str, Any]:
        """Analyze patterns within categories"""

        categories = defaultdict(list)
        for item in items:
            categories[item.category].append(item)

        patterns = {}
        for category, cat_items in categories.items():
            if len(cat_items) < 2:
                continue

            # Average effort by priority
            effort_by_priority = defaultdict(list)
            for item in cat_items:
                effort_by_priority[item.priority].append(
                    self._effort_to_days(item.effort))

            avg_effort = {}
            for priority, efforts in effort_by_priority.items():
                avg_effort[priority] = sum(efforts) / len(efforts)

            patterns[category] = {
                "item_count": len(cat_items),
                "average_effort_by_priority": dict(avg_effort),
                "completion_rate": len([i for i in cat_items if i.status == "completed"]) / len(cat_items)
            }

        return patterns

    def _analyze_effort_patterns(self, items: List) -> Dict[str, Any]:
        """Analyze effort estimation patterns"""

        effort_distribution = defaultdict(int)
        effort_completion = defaultdict(lambda: {"completed": 0, "total": 0})

        for item in items:
            effort_distribution[item.effort] += 1
            effort_completion[item.effort]["total"] += 1
            if item.status == "completed":
                effort_completion[item.effort]["completed"] += 1

        effort_rates = {}
        for effort, counts in effort_completion.items():
            if counts["total"] > 0:
                effort_rates[effort] = counts["completed"] / counts["total"]

        return {
            "effort_distribution": dict(effort_distribution),
            "effort_completion_rates": effort_rates
        }

    def _analyze_dependency_patterns(self, items: List) -> Dict[str, Any]:
        """Analyze dependency relationships and patterns"""

        # Build dependency graph
        item_map = {item.id: item for item in items}
        dependency_graph = defaultdict(list)

        for item in items:
            if hasattr(item, 'dependencies') and item.dependencies:
                for dep_id in item.dependencies:
                    dependency_graph[item.id].append(dep_id)

        # Analyze dependency depth and complexity
        dependency_depths = {}
        for item_id in item_map.keys():
            depth = self._calculate_dependency_depth(item_id, dependency_graph)
            dependency_depths[item_id] = depth

        # Find circular dependencies
        circular_deps = self._find_circular_dependencies(dependency_graph)

        # Calculate dependency complexity scores
        complexity_scores = {}
        for item_id, deps in dependency_graph.items():
            complexity_scores[item_id] = self._calculate_dependency_complexity(
                item_id, deps, dependency_graph)

        return {
            "dependency_depths": dependency_depths,
            "circular_dependencies": circular_deps,
            "complexity_scores": complexity_scores,
            "average_dependencies": sum(len(deps) for deps in dependency_graph.values()) / len(items) if items else 0
        }

    def _analyze_time_patterns(self, items: List) -> Dict[str, Any]:
        """Analyze time-based patterns"""

        now = datetime.now()

        # Age analysis
        age_distribution = defaultdict(int)
        for item in items:
            if hasattr(item, 'created_at') and item.created_at:
                try:
                    created = datetime.fromisoformat(
                        item.created_at.replace('Z', '+00:00'))
                    age_days = (now - created).days
                    if age_days < 7:
                        age_distribution["week"] += 1
                    elif age_days < 30:
                        age_distribution["month"] += 1
                    elif age_days < 90:
                        age_distribution["quarter"] += 1
                    else:
                        age_distribution["older"] += 1
                except:
                    age_distribution["unknown"] += 1

        # Completion time analysis
        completion_times = []
        for item in items:
            if (item.status == "completed" and
                hasattr(item, 'created_at') and item.created_at and
                hasattr(item, 'completed_at') and item.completed_at):
                try:
                    created = datetime.fromisoformat(
                        item.created_at.replace('Z', '+00:00'))
                    completed = datetime.fromisoformat(
                        item.completed_at.replace('Z', '+00:00'))
                    completion_days = (completed - created).days
                    completion_times.append(completion_days)
                except:
                    pass

        avg_completion_time = sum(
            completion_times) / len(completion_times) if completion_times else 0

        return {
            "age_distribution": dict(age_distribution),
            "average_completion_days": avg_completion_time,
            "completion_time_samples": len(completion_times)
        }

    def _calculate_dependency_depth(
            self, item_id: str, dependency_graph: Dict) ->int:
        """Calculate the maximum dependency depth for an item"""

        if item_id not in dependency_graph or not dependency_graph[item_id]:
            return 0

        max_depth = 0
        for dep_id in dependency_graph[item_id]:
            depth = 1 + \
                self._calculate_dependency_depth(dep_id, dependency_graph)
            max_depth = max(max_depth, depth)

        return max_depth

    def _find_circular_dependencies(self, dependency_graph: Dict) -> List[List[str]]:
        """Find circular dependencies in the graph"""

        circular_deps = []
        visited = set()
        rec_stack = set()


        def dfs(node, path):
            """dfs handler."""
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for dep in dependency_graph.get(node, []):
                if dep not in visited:
                    if dfs(dep, path):
                        return True
                elif dep in rec_stack:
                    # Found cycle
                    cycle_start = path.index(dep)
                    circular_deps.append(path[cycle_start:] + [dep])
                    return True

            path.pop()
            rec_stack.remove(node)
            return False

        for node in dependency_graph:
            if node not in visited:
                dfs(node, [])

        return circular_deps

    def _calculate_dependency_complexity(
            self, item_id: str, direct_deps: List[str],
            dependency_graph: Dict) ->float:
        """Calculate dependency complexity score"""

        if not direct_deps:
            return 0.0

        # Direct dependencies
        direct_count = len(direct_deps)

        # Indirect dependencies (recursive)
        indirect_deps = set()
        to_visit = list(direct_deps)

        while to_visit:
            current = to_visit.pop()
            if current not in indirect_deps:
                indirect_deps.add(current)
                to_visit.extend(dependency_graph.get(current, []))

        indirect_count = len(indirect_deps) - direct_count

        # Complexity score combines direct and indirect dependencies
        complexity = direct_count * 0.7 + indirect_count * 0.3

        return complexity

    def _effort_to_days(self, effort: str) -> float:
        """Convert effort string to estimated days"""
        effort_map = {
            "small": 1.0,
            "medium": 3.0,
            "large": 7.0,
            "epic": 14.0
        }
        return effort_map.get(effort, 3.0)

    def _store_patterns(self, pattern_type: str, pattern_data: Dict):
        """Store patterns for future learning"""

        pattern_id = hashlib.md5(
            f"{pattern_type}_{json.dumps(pattern_data, sort_keys=True)}".encode()).hexdigest()[:16]

        self.conn.execute("""
            INSERT OR REPLACE INTO intelligence_patterns
            (id, pattern_type, pattern_data, confidence, last_updated)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (
            pattern_id,
            pattern_type,
            json.dumps(pattern_data),
            0.8  # Base confidence
        ))

        self.conn.commit()

    def _generate_insights_from_patterns(self, patterns: Dict) -> List[Dict]:
        """Generate actionable insights from patterns"""

        insights = []

        # Completion rate insights
        completion_patterns = patterns.get("completion_rates", {})
        if completion_patterns.get("overall_completion_rate", 0) < 0.5:
            insights.append({
                "type": "completion_rate",
                "priority": "high",
                "message": f"Low overall completion rate ({completion_patterns['overall_completion_rate']:.1%}). Consider reviewing priorities.",
                "recommendation": "Focus on high-priority items and break down large tasks"
            })

        # Category pattern insights
        category_patterns = patterns.get("category_patterns", {})
        for category, data in category_patterns.items():
            if data.get(
                "completion_rate", 0) <0.3 and data.get(
                "item_count", 0) >3:
                insights.append({
                    "type": "category_blocker",
                    "priority": "medium",
                    "message": f"Low completion rate in {category} category ({data['completion_rate']:.1%})",
                    "recommendation": f"Investigate blockers in {category} items"
                })

        # Dependency insights
        dep_patterns = patterns.get("dependency_patterns", {})
        circular_deps = dep_patterns.get("circular_dependencies", [])
        if circular_deps:
            insights.append({
                "type": "circular_dependencies",
                "priority": "high",
                "message": f"Found {len(circular_deps)} circular dependency chains",
                "recommendation": "Review and break circular dependencies"
            })

        # Time-based insights
        time_patterns = patterns.get("time_patterns", {})
        old_items = time_patterns.get("age_distribution", {}).get("older", 0)
        if old_items > 5:
            insights.append({
                "type": "aging_backlog",
                "priority": "medium",
                "message": f"{old_items} items older than 3 months",
                "recommendation": "Review and reprioritize old backlog items"
            })

        return insights

    def generate_priority_suggestions(self) -> Dict[str, Any]:
        """Generate AI-powered priority suggestions for all backlog items"""

        items = self.backlog_manager.get_all_items()
        suggestions = {}

        # Get current patterns for context
        patterns = self.analyze_backlog_patterns()

        for item in items:
            if item.status in ["completed", "cancelled"]:
                continue

            suggestion = self._calculate_priority_suggestion(item, patterns)
            suggestions[item.id] = suggestion

            # Store suggestion
            self._store_priority_suggestion(item.id, suggestion)

        return {
            "suggestions": suggestions,
            "total_items": len(items),
            "suggested_changes": len([s for s in suggestions.values() if s["suggested_priority"] != s["current_priority"]])
        }

    def _calculate_priority_suggestion(self, item, patterns: Dict) -> Dict[str, Any]:
        """Calculate priority suggestion for a single item"""

        factors = []
        confidence = 0.5  # Base confidence
        reasoning_parts = []

        current_priority = item.priority

        # Factor 1: Age-based priority boost
        if hasattr(item, 'created_at') and item.created_at:
            try:
                created = datetime.fromisoformat(
                    item.created_at.replace('Z', '+00:00'))
                age_days = (datetime.now() - created).days

                if age_days > 90:  # 3 months
                    factors.append("aging_item")
                    confidence += 0.2
                    reasoning_parts.append("Item is significantly aged")
                elif age_days > 30:  # 1 month
                    factors.append("moderately_aged")
                    confidence += 0.1
                    reasoning_parts.append("Item has been waiting")
            except:
                pass

        # Factor 2: Dependency analysis
        dep_patterns = patterns.get("patterns", {}).get(
            "dependency_patterns", {})
        item_complexity = dep_patterns.get(
            "complexity_scores", {}).get(item.id, 0)

        if item_complexity > 2.0:
            factors.append("high_dependency_complexity")
            confidence += 0.15
            reasoning_parts.append(
                "High dependency complexity may cause delays")

        # Factor 3: Category performance
        category_rates = patterns.get("patterns", {}).get(
            "completion_rates", {}).get("category_completion_rates", {})
        category_rate = category_rates.get(item.category, 0.5)

        if category_rate < 0.3:
            factors.append("low_category_performance")
            confidence += 0.1
            reasoning_parts.append(
                f"{item.category} category has low completion rate")

        # Factor 4: Effort vs completion patterns
        effort_rates = patterns.get("patterns", {}).get(
            "effort_patterns", {}).get("effort_completion_rates", {})
        effort_rate = effort_rates.get(item.effort, 0.5)

        if effort_rate < 0.4 and item.effort == "large":
            factors.append("large_effort_blocked")
            confidence += 0.2
            reasoning_parts.append("Large effort items are getting stuck")

        # Factor 5: Doctrine alignment (if available)
        if hasattr(item, 'doctrine_alignment') and item.doctrine_alignment:
            max_alignment = max(item.doctrine_alignment.values())
            if max_alignment > 0.8:
                factors.append("high_doctrine_alignment")
                confidence += 0.1
                reasoning_parts.append("Strong doctrine alignment")

        # Determine suggested priority
        suggested_priority = current_priority

        # Priority boost logic
        boost_reasons = []
        if "aging_item" in factors and current_priority in ["low", "backlog"]:
            suggested_priority = "medium"
            boost_reasons.append("aging")
        elif "high_dependency_complexity" in factors and current_priority == "low":
            suggested_priority = "medium"
            boost_reasons.append("dependency complexity")
        elif "large_effort_blocked" in factors and current_priority != "high":
            suggested_priority = "high"
            boost_reasons.append("large effort blocking")
        elif "low_category_performance" in factors and len(factors) >= 2:
            # Boost if multiple negative factors
            if current_priority == "low":
                suggested_priority = "medium"
            elif current_priority == "medium":
                suggested_priority = "high"
            boost_reasons.append("multiple risk factors")

        # Cap confidence
        confidence = min(confidence, 0.95)

        reasoning = ". ".join(
            reasoning_parts) if reasoning_parts else "Based on current backlog patterns"

        return {
            "current_priority": current_priority,
            "suggested_priority": suggested_priority,
            "confidence": confidence,
            "factors": factors,
            "reasoning": reasoning,
            "boost_reasons": boost_reasons
        }

    def _store_priority_suggestion(self, item_id: str, suggestion: Dict):
        """Store priority suggestion in database"""

        self.conn.execute("""
            INSERT OR REPLACE INTO priority_suggestions
            (item_id, suggested_priority, confidence, reasoning, factors, generated_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (
            item_id,
            suggestion["suggested_priority"],
            suggestion["confidence"],
            suggestion["reasoning"],
            json.dumps(suggestion["factors"])
        ))

        self.conn.commit()

    def optimize_dependencies(self) -> Dict[str, Any]:
        """Optimize dependency relationships for better flow"""

        items = self.backlog_manager.get_all_items()
        item_map = {item.id: item for item in items}

        # Build current dependency graph
        dependency_graph = defaultdict(list)
        reverse_graph = defaultdict(list)

        for item in items:
            if hasattr(item, 'dependencies') and item.dependencies:
                for dep_id in item.dependencies:
                    dependency_graph[item.id].append(dep_id)
                    reverse_graph[dep_id].append(item.id)

        # Find optimization opportunities
        optimizations = []

        # 1. Identify missing dependencies
        missing_deps = self._find_missing_dependencies(
            dependency_graph, item_map)
        for item_id, suggested_deps in missing_deps.items():
            if suggested_deps:
                optimizations.append({
                    "type": "missing_dependencies",
                    "item_id": item_id,
                    "suggestions": suggested_deps,
                    "reasoning": "Based on category and content analysis"
                })

        # 2. Suggest parallel execution opportunities
        parallel_ops = self._find_parallel_opportunities(
            dependency_graph, item_map)
        for item_id, parallel_items in parallel_ops.items():
            if parallel_items:
                optimizations.append({
                    "type": "parallel_execution",
                    "item_id": item_id,
                    "parallel_items": parallel_items,
                    "reasoning": "Items can be worked on simultaneously"
                })

        # 3. Identify bottleneck items
        bottlenecks = self._identify_bottlenecks(reverse_graph, item_map)
        for item_id, impact in bottlenecks.items():
            if impact > 3:  # Blocking more than 3 items
                optimizations.append({
                    "type": "bottleneck",
                    "item_id": item_id,
                    "blocking_count": impact,
                    "reasoning": "High blocker - prioritize this item"
                })

        # Store dependency insights
        for opt in optimizations:
            if opt["type"] == "missing_dependencies":
                for dep_id in opt["suggestions"]:
                    self._store_dependency_insight(
                        opt["item_id"], dep_id, "suggested_missing",
                        0.7, f"Analysis suggests {dep_id} should be dependency of {opt['item_id']}"
                    )

        return {
            "optimizations": optimizations,
            "total_opportunities": len(optimizations),
            "bottlenecks_found": len([o for o in optimizations if o["type"] == "bottleneck"])
        }

    def _find_missing_dependencies(self, dependency_graph: Dict,
                                    item_map: Dict) ->Dict[str, List[str]]:
        """Find potentially missing dependencies based on content analysis"""

        missing_deps = defaultdict(list)

        # Simple heuristic: items in same category might depend on each other
        category_items = defaultdict(list)
        for item_id, item in item_map.items():
            category_items[item.category].append(item_id)

        for category, item_ids in category_items.items():
            if len(item_ids) <= 1:
                continue

            # For now, suggest dependencies based on creation order
            # More sophisticated analysis could use NLP on titles/descriptions
            sorted_items = sorted(
                [(item_id, item_map[item_id].created_at)
                  for item_id in item_ids],
                key=lambda x: x[1] or ""
            )

            for i, (item_id, _) in enumerate(sorted_items):
                # Suggest dependency on previous items in same category
                for j in range(
                    max(0, i -2),
                    i):  # Last 2 items as potential deps
                    prev_item_id = sorted_items[j][0]
                    if prev_item_id not in dependency_graph[item_id]:
                        missing_deps[item_id].append(prev_item_id)

        return dict(missing_deps)

    def _find_parallel_opportunities(self, dependency_graph: Dict,
                                     item_map: Dict) ->Dict[str, List[str]]:
        """Find items that could be worked on in parallel"""

        parallel_ops = defaultdict(list)

        # Find items with no dependencies that others depend on
        independent_items = []
        for item_id, deps in dependency_graph.items():
            if not deps:  # No dependencies
                independent_items.append(item_id)

        # Group by category
        category_groups = defaultdict(list)
        for item_id in independent_items:
            category_groups[item_map[item_id].category].append(item_id)

        # Within categories, suggest parallel execution for similar priority items
        for category, item_ids in category_groups.items():
            if len(item_ids) >= 2:
                priority_groups = defaultdict(list)
                for item_id in item_ids:
                    priority_groups[item_map[item_id].priority].append(item_id)

                for priority, items in priority_groups.items():
                    if len(items) >= 2:
                        # First item can suggest parallels with others
                        for i in range(1, len(items)):
                            parallel_ops[items[0]].append(items[i])

        return dict(parallel_ops)

    def _identify_bottlenecks(self, reverse_graph: Dict, item_map: Dict) -> Dict[str, int]:
        """Identify items that are blocking many others"""

        bottlenecks = {}
        for item_id, blocked_items in reverse_graph.items():
            bottlenecks[item_id] = len(blocked_items)

        return bottlenecks

    def _store_dependency_insight(
            self, item_id: str, dependency_id: str, insight_type: str,
            strength: float, reasoning: str):
        """Store dependency insight"""

        insight_id = hashlib.md5(
            f"{item_id}_{dependency_id}_{insight_type}".encode()).hexdigest()[:16]

        self.conn.execute("""
            INSERT OR REPLACE INTO dependency_insights
            (id, item_id, dependency_id, insight_type, strength, reasoning, discovered_at)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (
            insight_id,
            item_id,
            dependency_id,
            insight_type,
            strength,
            reasoning
        ))

        self.conn.commit()

    def get_intelligence_report(self) -> Dict[str, Any]:
        """Generate comprehensive intelligence report"""

        patterns = self.analyze_backlog_patterns()
        suggestions = self.generate_priority_suggestions()
        optimizations = self.optimize_dependencies()

        # Get stored insights
        cursor = self.conn.execute("""
            SELECT pattern_type, pattern_data, confidence
            FROM intelligence_patterns
            ORDER BY last_updated DESC
            LIMIT 10
        """)

        stored_patterns = []
        for row in cursor.fetchall():
            stored_patterns.append({
                "type": row[0],
                "data": json.loads(row[1]),
                "confidence": row[2]
            })

        return {
            "patterns_analysis": patterns,
            "priority_suggestions": suggestions,
            "dependency_optimizations": optimizations,
            "stored_patterns": stored_patterns,
            "generated_at": datetime.now().isoformat()
        }

# Global instance
_intelligence_engine = None

def get_intelligence_engine() -> IntelligenceEngine:
    """Get global intelligence engine instance"""
    global _intelligence_engine
    if _intelligence_engine is None:
        _intelligence_engine = IntelligenceEngine()
    return _intelligence_engine

# Convenience functions
def analyze_backlog_intelligence() -> Dict[str, Any]:
    """Analyze backlog patterns and generate insights"""
    return get_intelligence_engine().analyze_backlog_patterns()

def generate_priority_suggestions() -> Dict[str, Any]:
    """Generate AI-powered priority suggestions"""
    return get_intelligence_engine().generate_priority_suggestions()

def optimize_backlog_dependencies() -> Dict[str, Any]:
    """Optimize dependency relationships"""
    return get_intelligence_engine().optimize_dependencies()

def get_backlog_intelligence_report() -> Dict[str, Any]:
    """Get comprehensive intelligence report"""
    return get_intelligence_engine().get_intelligence_report()

if __name__ == "__main__":
    # Test the intelligence system
    print("🧠 Testing Backlog Intelligence System...")

    try:
        # Test pattern analysis
        patterns = analyze_backlog_intelligence()
        print(f"✅ Analyzed {patterns.get('analyzed_items', 0)} backlog items")

        # Test priority suggestions
        suggestions = generate_priority_suggestions()
        print(
            f"✅ Generated {suggestions.get('suggested_changes', 0)} priority suggestions")

        # Test dependency optimization
        optimizations = optimize_backlog_dependencies()
        print(
            f"✅ Found {optimizations.get('total_opportunities', 0)} optimization opportunities")

        # Test full report
        report = get_backlog_intelligence_report()
        print(
            f"✅ Generated intelligence report with {len(report.get('stored_patterns', []))} stored patterns")

    except Exception as e:
        print(f"❌ Intelligence system test failed: {e}")
        import traceback
        traceback.print_exc()

    print("✅ Backlog Intelligence System ready!")