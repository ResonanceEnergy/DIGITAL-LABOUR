#!/usr/bin/env python3
"""
Simple validation script for doctrine evolution framework
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from doctrine_evolution_framework import DoctrineEvolutionEngine, DoctrineChangeType
    print("✅ Doctrine evolution framework imported successfully")

    # Test basic functionality
    engine = DoctrineEvolutionEngine()
    print("✅ Doctrine evolution engine initialized")

    # Test proposing a change
    change_data = {
        "name": "test_principle",
        "description": "Test principle for validation"
    }

    change_id = engine.propose_doctrine_change(
        DoctrineChangeType.ADD_PRINCIPLE,
        "memory_principles",
        change_data,
        "Test change proposal",
        "validator"
    )
    print(f"✅ Change proposed: {change_id}")

    # Test getting pending changes
    pending = engine.get_pending_changes()
    print(f"✅ Pending changes: {len(pending)}")

    # Test stats
    stats = engine.get_evolution_stats()
    print(f"✅ Evolution stats: {stats}")

    print("🎉 Doctrine evolution framework validation successful!")

except Exception as e:
    print(f"❌ Validation failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)