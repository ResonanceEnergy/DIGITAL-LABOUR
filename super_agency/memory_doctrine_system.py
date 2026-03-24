#!/usr/bin/env python3
"""
Bit Rage Systems Memory Doctrine System
Multi-layer memory architecture for context management and persistence
"""

import os
import json
import time
import hashlib
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import threading
import atexit

class MemoryLayer:
    """Base class for memory layers"""

    def __init__(self, name: str, max_size: int, retention_policy: str):
        """Initialize."""
        self.name = name
        self.max_size = max_size
        self.retention_policy = retention_policy
        self.created_at = datetime.now()
        self.last_accessed = datetime.now()
        self.access_count = 0

    def store(self, key: str, data: Any, metadata: Dict = None) -> bool:
        """Store data in this layer"""
        raise NotImplementedError

    def retrieve(self, key: str) -> Optional[Any]:
        """Retrieve data from this layer"""
        raise NotImplementedError

    def cleanup(self) -> int:
        """Clean up expired or low-priority data"""
        raise NotImplementedError

    def get_stats(self) -> Dict:
        """Get layer statistics"""
        return {
            "name": self.name,
            "max_size": self.max_size,
            "retention_policy": self.retention_policy,
            "created_at": self.created_at.isoformat(),
            "last_accessed": self.last_accessed.isoformat(),
            "access_count": self.access_count
        }

class EphemeralMemory(MemoryLayer):
    """Fast, temporary memory for current session"""


    def __init__(self, max_size: int = 4096):  # 4K tokens equivalent
        """__init__ handler."""
        super().__init__("ephemeral", max_size, "session")
        self.cache = {}
        self.access_order = []

    def store(self, key: str, data: Any, metadata: Dict = None) -> bool:
        """Store data with LRU eviction"""
        if len(self.cache) >= self.max_size and key not in self.cache:
            # Evict least recently used
            oldest_key = self.access_order.pop(0)
            del self.cache[oldest_key]

        self.cache[key] = {
            "data": data,
            "metadata": metadata or {},
            "stored_at": datetime.now(),
            "access_count": 0
        }

        if key in self.access_order:
            self.access_order.remove(key)
        self.access_order.append(key)

        self.last_accessed = datetime.now()
        return True

    def retrieve(self, key: str) -> Optional[Any]:
        """Retrieve data and update access patterns"""
        if key not in self.cache:
            return None

        # Update access order
        if key in self.access_order:
            self.access_order.remove(key)
        self.access_order.append(key)

        self.cache[key]["access_count"] += 1
        self.last_accessed = datetime.now()
        self.access_count += 1

        return self.cache[key]["data"]

    def cleanup(self) -> int:
        """Clean up expired session data (no-op for ephemeral)"""
        return 0


class SessionMemory(MemoryLayer):
    """Medium-term memory for multi-turn conversations — backed by SQLite."""

    def __init__(self, max_size: int = 65536, retention_hours: int = 24):  # 64K tokens
        super().__init__("session", max_size, f"{retention_hours}_hours")
        self.retention_hours = retention_hours
        self.db_path = Path("./memory/session_memory.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        # Migrate legacy JSON if it exists
        self._migrate_from_json()

    def _init_db(self):
        """Initialize SQLite database for session storage."""
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS session (
                key TEXT PRIMARY KEY,
                data TEXT NOT NULL,
                metadata TEXT,
                stored_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                access_count INTEGER DEFAULT 0,
                last_accessed TIMESTAMP
            )
        """)
        self.conn.commit()
        SchemaMigrator.migrate(self.conn, "session_memory")

    def _migrate_from_json(self):
        """One-time migration from legacy session_memory.json."""
        json_path = self.db_path.parent / "session_memory.json"
        if not json_path.exists():
            return
        try:
            legacy = json.loads(json_path.read_text(encoding="utf-8"))
            for key, val in legacy.items():
                self.store(key, val.get("data"), val.get("metadata"))
            json_path.rename(json_path.with_suffix(".json.migrated"))
        except Exception:
            pass  # migration is best-effort

    def store(self, key: str, data: Any, metadata: Dict = None) -> bool:
        """Store session data with timestamp."""
        try:
            self.conn.execute("""
                INSERT OR REPLACE INTO session (key, data, metadata, stored_at, access_count)
                VALUES (?, ?, ?, ?, COALESCE(
                    (SELECT access_count FROM session WHERE key = ?), 0))
            """, (
                key,
                json.dumps(data, default=str),
                json.dumps(metadata or {}, default=str),
                datetime.now().isoformat(),
                key,
            ))
            self.conn.commit()
            self.last_accessed = datetime.now()
            return True
        except Exception as e:
            print(f"Error storing session memory: {e}")
            return False

    def retrieve(self, key: str) -> Optional[Any]:
        """Retrieve session data."""
        try:
            cur = self.conn.execute(
                "SELECT data, access_count FROM session WHERE key = ?", (key,))
            row = cur.fetchone()
            if not row:
                return None
            data = json.loads(row[0])
            self.conn.execute(
                "UPDATE session SET access_count = ?, last_accessed = ? WHERE key = ?",
                (row[1] + 1, datetime.now().isoformat(), key),
            )
            self.conn.commit()
            self.last_accessed = datetime.now()
            self.access_count += 1
            return data
        except Exception as e:
            print(f"Error retrieving session memory: {e}")
            return None

    def cleanup(self) -> int:
        """Clean up expired session data."""
        try:
            cutoff = (datetime.now() - \
                      timedelta(hours=self.retention_hours)).isoformat()
            cur = self.conn.execute(
                "DELETE FROM session WHERE stored_at < ?", (cutoff,))
            deleted = cur.rowcount
            self.conn.commit()
            return deleted
        except Exception as e:
            print(f"Error during session cleanup: {e}")
            return 0

class SchemaMigrator:
    """Simple schema migration framework for memory SQLite databases."""

    MIGRATIONS = {
        # version -> (description, list_of_sql_statements)
        1: ("initial schema", []),  # v1 = the CREATE TABLEs in _init_db
        2: ("add last_accessed to session table", [
            "ALTER TABLE session ADD COLUMN last_accessed TIMESTAMP",
        ]),
    }

    @classmethod
    def migrate(cls, conn: sqlite3.Connection, db_label: str = "memory"):
        """Run pending migrations on the given connection."""
        conn.execute("""
            CREATE TABLE IF NOT EXISTS _schema_meta (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        cur = conn.execute(
            "SELECT value FROM _schema_meta WHERE key = 'version'")
        row = cur.fetchone()
        current = int(row[0]) if row else 0

        latest = max(cls.MIGRATIONS.keys()) if cls.MIGRATIONS else 0
        if current >= latest:
            return

        for ver in sorted(cls.MIGRATIONS.keys()):
            if ver <= current:
                continue
            desc, stmts = cls.MIGRATIONS[ver]
            for sql in stmts:
                try:
                    conn.execute(sql)
                except sqlite3.OperationalError:
                    pass  # e.g. column already exists on fresh DB
            conn.execute(
                "INSERT OR REPLACE INTO _schema_meta (key, value) VALUES ('version', ?)",
                (str(ver),),)
            conn.commit()
            print(f"[{db_label}] migrated to schema v{ver}: {desc}")


class PersistentMemory(MemoryLayer):
    """Long-term memory with vector search capabilities"""

    def __init__(self, max_size: int = 1000000):  # 1M tokens equivalent
        super().__init__("persistent", max_size, "indefinite")
        self.db_path = Path("./memory/persistent_memory.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize SQLite database for persistent storage"""
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS memory (
                key TEXT PRIMARY KEY,
                data TEXT NOT NULL,
                metadata TEXT,
                stored_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                access_count INTEGER DEFAULT 0,
                last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                importance REAL DEFAULT 0.5
            )
        """)
        self.conn.commit()
        SchemaMigrator.migrate(self.conn, "persistent_memory")

    def store(self, key: str, data: Any, metadata: Dict = None) -> bool:
        """Store data with importance scoring"""
        try:
            # Calculate importance based on metadata
            importance = metadata.get("importance", 0.5) if metadata else 0.5

            self.conn.execute("""
                INSERT OR REPLACE INTO memory
                (key, data, metadata, importance, access_count)
                VALUES (?, ?, ?, ?, COALESCE((SELECT access_count FROM memory WHERE key = ?), 0))
            """, (
                key,
                json.dumps(data, default=str),
                json.dumps(metadata or {}, default=str),
                importance,
                key
            ))
            self.conn.commit()

            self.last_accessed = datetime.now()
            return True
        except Exception as e:
            print(f"Error storing persistent memory: {e}")
            return False

    def retrieve(self, key: str) -> Optional[Any]:
        """Retrieve persistent data"""
        try:
            cursor = self.conn.execute("""
                SELECT data, access_count FROM memory WHERE key = ?
            """, (key,))

            row = cursor.fetchone()
            if row:
                data_str, access_count = row
                data = json.loads(data_str)

                # Update access statistics
                self.conn.execute("""
                    UPDATE memory
                    SET access_count = ?, last_accessed = CURRENT_TIMESTAMP
                    WHERE key = ?
                """, (access_count + 1, key))
                self.conn.commit()

                self.last_accessed = datetime.now()
                self.access_count += 1

                return data
        except Exception as e:
            print(f"Error retrieving persistent memory: {e}")

        return None

    def cleanup(self) -> int:
        """Clean up low-importance, rarely accessed data"""
        try:
            # Remove items with low importance and old access
            cutoff_date = (datetime.now() - timedelta(days=90)).isoformat()

            cursor = self.conn.execute("""
                DELETE FROM memory
                WHERE importance < 0.3
                AND last_accessed < ?
                AND (SELECT COUNT(*) FROM memory) > ?
            """, (cutoff_date, self.max_size * 0.9))

            deleted_count = cursor.rowcount
            self.conn.commit()

            return deleted_count
        except Exception as e:
            print(f"Error during cleanup: {e}")
            return 0

class MemoryDoctrineSystem:
    """Main memory doctrine system coordinating all layers"""

    def __init__(self):
        self.layers = {
            "ephemeral": EphemeralMemory(),
            "session": SessionMemory(),
            "persistent": PersistentMemory()
        }

        # Start cleanup thread
        self.cleanup_thread = threading.Thread(
            target=self._cleanup_worker, daemon=True)
        self.cleanup_thread.start()

        # Register cleanup on exit
        atexit.register(self.shutdown)

    def _cleanup_worker(self):
        """Background cleanup worker"""
        while True:
            time.sleep(3600)  # Clean up every hour
            for layer in self.layers.values():
                try:
                    cleaned = layer.cleanup()
                    if cleaned > 0:
                        print(
                            f"Cleaned {cleaned} items from {layer.name} layer")
                except Exception as e:
                    print(f"Cleanup error in {layer.name}: {e}")

    def store(self, key: str, data: Any, layer: str = "auto", metadata: Dict = None) -> bool:
        """Store data in appropriate layer"""
        if layer == "auto":
            # Auto-select layer based on data characteristics
            layer = self._select_layer(data, metadata)

        if layer not in self.layers:
            return False

        return self.layers[layer].store(key, data, metadata)

    def retrieve(
            self, key: str, search_layers: List[str]=None) ->Optional[Any]:
        """Retrieve data from memory layers"""
        layers_to_search = search_layers or [
            "ephemeral", "session", "persistent"]

        for layer_name in layers_to_search:
            if layer_name in self.layers:
                data = self.layers[layer_name].retrieve(key)
                if data is not None:
                    return data

        return None

    def _select_layer(self, data: Any, metadata: Dict = None) -> str:
        """Auto-select appropriate memory layer"""
        # Check metadata for explicit layer preference
        if metadata and "memory_layer" in metadata:
            return metadata["memory_layer"]

        # Select based on data characteristics
        data_size = len(str(data))

        if data_size < 1000:  # Small data
            return "ephemeral"
        elif data_size < 10000:  # Medium data
            return "session"
        else:  # Large or important data
            return "persistent"

    def get_stats(self) -> Dict:
        """Get comprehensive memory statistics"""
        stats = {
            "system": {
                "total_layers": len(self.layers),
                "active_cleanup": self.cleanup_thread.is_alive()
            },
            "layers": {}
        }

        for name, layer in self.layers.items():
            stats["layers"][name] = layer.get_stats()

        return stats

    def optimize(self) -> Dict:
        """Run memory optimization across all layers"""
        results = {}

        for name, layer in self.layers.items():
            try:
                cleaned = layer.cleanup()
                results[name] = {
                    "status": "success",
                    "items_cleaned": cleaned
                }
            except Exception as e:
                results[name] = {
                    "status": "error",
                    "error": str(e)
                }

        return results

    def shutdown(self):
        """Graceful shutdown"""
        print("Shutting down Memory Doctrine System...")

        # Close database connections
        for name in ("session", "persistent"):
            layer = self.layers.get(name)
            if layer and hasattr(layer, "conn"):
                try:
                    layer.conn.close()
                except Exception:
                    pass

        print("Memory Doctrine System shutdown complete.")

# Global instance
_memory_system = None

def get_memory_system() -> MemoryDoctrineSystem:
    """Get or create global memory system instance"""
    global _memory_system
    if _memory_system is None:
        _memory_system = MemoryDoctrineSystem()
    return _memory_system

# Convenience functions
def remember(
        key: str, data: Any, layer: str="auto", metadata: Dict=None) ->bool:
    """Store data in memory system"""
    return get_memory_system().store(key, data, layer, metadata)

def recall(key: str, search_layers: List[str] = None) -> Optional[Any]:
    """Retrieve data from memory system"""
    return get_memory_system().retrieve(key, search_layers)

def memory_stats() -> Dict:
    """Get memory system statistics"""
    return get_memory_system().get_stats()

def optimize_memory() -> Dict:
    """Optimize memory across all layers"""
    return get_memory_system().optimize()

if __name__ == "__main__":
    # Test the memory system
    print("🧠 Testing Memory Doctrine System...")

    # Store test data
    remember("test_ephemeral", "Quick temporary data", "ephemeral")
    remember("test_session", "Session-persistent data", "session")
    remember("test_persistent", "Long-term important data", "persistent",
             {"importance": 0.9})

    # Retrieve test data
    print("Ephemeral:", recall("test_ephemeral"))
    print("Session:", recall("test_session"))
    print("Persistent:", recall("test_persistent"))

    # Show stats
    stats = memory_stats()
    print("Memory Stats:", json.dumps(stats, indent=2, default=str))

    print("✅ Memory Doctrine System test complete!")
