#!/usr/bin/env python3
"""
Unified Memory Doctrine System
BIT RAGE LABOUR Memory Management and Doctrine Preservation
MacBook M1 8GB Optimized
"""

import json
import os
from datetime import datetime
from typing import Dict, Any, List, Optional


class UnifiedMemoryDoctrineSystem:
    """Unified memory and doctrine management system"""

    def __init__(self, memory_file: str = "unified_memory_doctrine.json"):
        self.memory_file = memory_file
        self.memory_store: Dict[str, Any] = {}
        self.doctrine_store: Dict[str, Any] = {}
        self.load_memory()

    def load_memory(self) -> None:
        """Load memory and doctrine from persistent storage"""
        try:
            if os.path.exists(self.memory_file):
                with open(self.memory_file, 'r') as f:
                    data = json.load(f)
                    self.memory_store = data.get('memory', {})
                    self.doctrine_store = data.get('doctrine', {})
                print("[MEMORY] Unified Memory Doctrine loaded")
            else:
                print("[MEMORY] Unified Memory Doctrine initialized (new)")
                self._initialize_default_doctrine()
        except Exception as e:
            print(f"[WARN] Memory load error: {e}")
            self._initialize_default_doctrine()

    def _initialize_default_doctrine(self) -> None:
        """Initialize default doctrine and memory structure"""
        self.doctrine_store = {
            'version': '2.0',
            'platform': 'macOS M1 8GB',
            'architecture': 'three_device',
            'memory_limits': {
                'critical': 128,
                'agents': 256,
                'cache': 128,
                'temp': 64
            },
            'device_codes': {
                'quantum_quasar': 'Mac Workstation',
                'pocket_pulsar': 'iPhone Slave',
                'tablet_titan': 'iPad Slave'
            }
        }

        self.memory_store = {
            'system_init': {
                'timestamp': datetime.now().isoformat(),
                'status': 'initialized',
                'platform': 'macOS Sequoia 15.7.3',
                'memory_total': '8GB',
                'optimization': 'QUASMEM_ACTIVE'
            }
        }

    def remember_unified(self, key: str, value: Any,
                         memory_type: str = 'temporary') -> None:
        """Store information in unified memory system"""
        memory_entry = {
            'value': value,
            'timestamp': datetime.now().isoformat(),
            'type': memory_type,
            'platform': 'macOS_M1'
        }

        self.memory_store[key] = memory_entry

        # Auto-save for persistent memory
        if memory_type == 'persistent':
            self.save_memory()

        print(f"[MEMORY] Stored: {key} = {value}")

    def recall_unified(self, key: str) -> Optional[Any]:
        """Retrieve information from unified memory"""
        if key in self.memory_store:
            entry = self.memory_store[key]
            print(f"[MEMORY] Recalled: {key} = {entry['value']}")
            return entry['value']
        return None

    def get_doctrine(self, key: str) -> Optional[Any]:
        """Get doctrine value"""
        return self.doctrine_store.get(key)

    def update_doctrine(self, key: str, value: Any) -> None:
        """Update doctrine value"""
        self.doctrine_store[key] = value
        self.save_memory()
        print(f"[DOCTRINE] Updated: {key} = {value}")

    def save_memory(self) -> None:
        """Save memory and doctrine to persistent storage"""
        try:
            data = {
                'memory': self.memory_store,
                'doctrine': self.doctrine_store,
                'last_saved': datetime.now().isoformat(),
                'version': '2.0'
            }

            with open(self.memory_file, 'w') as f:
                json.dump(data, f, indent=2)

            print("[MEMORY] Unified Memory Doctrine saved")
        except Exception as e:
            print(f"[WARN] Memory save error: {e}")

    def get_status(self) -> Dict[str, Any]:
        """Get system status"""
        return {
            'memory_entries': len(self.memory_store),
            'doctrine_entries': len(self.doctrine_store),
            'platform': self.doctrine_store.get('platform', 'unknown'),
            'memory_limits': self.doctrine_store.get(
                'memory_limits', {}),
            'last_saved': self.memory_store.get(
                'system_init', {}).get('timestamp', 'never'),
            'status': 'ACTIVE'
        }

    def get_system_status(self) -> Dict[str, Any]:
        """Alias for get_status — used by continuous_memory_backup."""
        return self.get_status()

    @property
    def layers(self) -> Dict[str, Any]:
        """Compatibility bridge — expose memory/doctrine stores as layers."""
        return {
            'ephemeral': _SimpleLayer('ephemeral', {}),
            'session': _SimpleLayer(
                'session', dict(self.memory_store)),
            'persistent': _SimpleLayer(
                'persistent', dict(self.doctrine_store)),
        }

    def prevent_blanks(self) -> Dict[str, Any]:
        """Check for and consolidate blank/empty memory entries."""
        blanks_detected: List[str] = []
        for key, value in list(self.memory_store.items()):
            if value is None or value == '' or value == {}:
                blanks_detected.append(key)
        for key, value in list(self.doctrine_store.items()):
            if value is None or value == '' or value == {}:
                blanks_detected.append(key)
        return {
            'blanks_detected': blanks_detected,
            'consolidation': {
                'checked_memory': len(self.memory_store),
                'checked_doctrine': len(self.doctrine_store),
                'blanks_found': len(blanks_detected),
            },
        }


class _SimpleLayer:
    """Minimal layer shim for compatibility with continuous_memory_backup."""

    def __init__(self, name: str, data: Dict[str, Any]):
        self.name = name
        self.data = data
        self.cache = data  # ephemeral layer compat
        self.db_path = f"memory_{name}.db"

    def store(self, key: str, value: Any,
              metadata: Optional[Dict] = None) -> bool:
        self.data[key] = {'data': value, 'metadata': metadata or {}}
        return True

    def retrieve(self, key: str) -> Optional[Any]:
        entry = self.data.get(key)
        return entry.get('data') if entry else None

    def get_stats(self) -> Dict[str, Any]:
        return {'entries': len(self.data), 'name': self.name}


_instance: Optional[UnifiedMemoryDoctrineSystem] = None


def get_unified_memory_system() -> UnifiedMemoryDoctrineSystem:
    """Get or create the singleton UnifiedMemoryDoctrineSystem instance."""
    global _instance
    if _instance is None:
        _instance = UnifiedMemoryDoctrineSystem()
    return _instance


# Global instance
unified_memory = UnifiedMemoryDoctrineSystem()


def remember_unified(
    key: str, value: Any, memory_type: str = 'temporary'
) -> None:
    """Global function for unified memory storage"""
    unified_memory.remember_unified(key, value, memory_type)


def recall_unified(key: str) -> Optional[Any]:
    """Global function for unified memory retrieval"""
    return unified_memory.recall_unified(key)


def get_doctrine_status() -> Dict[str, Any]:
    """Get doctrine system status"""
    return unified_memory.get_status()


if __name__ == '__main__':
    print("[MEMORY] Unified Memory Doctrine System")
    print("Platform: MacBook M1 8GB")
    print("Status: ACTIVE")
    print("Memory entries:", len(unified_memory.memory_store))
    print("Doctrine entries:", len(unified_memory.doctrine_store))
