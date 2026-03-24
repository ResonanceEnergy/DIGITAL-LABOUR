#!/usr/bin/env python3
"""
DIGITAL LABOUR Vector Database Integration
Enhanced semantic search and memory retrieval
"""

import hashlib
import json
import os
import pickle
import sqlite3
import threading
import time
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import faiss
import numpy as np

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    print("⚠️  sentence-transformers not available. Using fallback embedding method.")
    SENTENCE_TRANSFORMERS_AVAILABLE = False

class VectorStore:
    """Vector database for semantic search and similarity matching"""

    def __init__(self, storage_path: Path = None, embedding_model: str = "all-MiniLM-L6-v2"):
        self.storage_path = storage_path or Path("./vector_store")
        self.storage_path.mkdir(parents=True, exist_ok=True)

        # Initialize embedding model
        self.embedding_model_name = embedding_model
        self.embedding_model = None
        self.embedding_dim = 384  # Default for all-MiniLM-L6-v2

        global SENTENCE_TRANSFORMERS_AVAILABLE  # pylint: disable=global-statement
        if SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                self.embedding_model = SentenceTransformer(embedding_model)
                self.embedding_dim = self.embedding_model.get_sentence_embedding_dimension()
                print(f"✅ Loaded embedding model: {embedding_model} (dim: {self.embedding_dim})")
            except Exception as e:
                print(f"❌ Failed to load embedding model: {e}")
                SENTENCE_TRANSFORMERS_AVAILABLE = False

        # Initialize FAISS index
        self.index = faiss.IndexFlatIP(self.embedding_dim)  # Inner product (cosine similarity)
        self.id_to_vector = {}  # Maps IDs to vectors
        self.vector_to_id = {}  # Maps vector indices to IDs
        self.metadata = {}      # Additional metadata for each vector

        # Load existing data
        self._load_index()

        print(f"🗂️  Vector store initialized with {self.index.ntotal} vectors")

    def _load_index(self):
        """Load existing FAISS index and metadata"""

        index_path = self.storage_path / "faiss_index.bin"
        metadata_path = self.storage_path / "metadata.json"

        if index_path.exists():
            try:
                self.index = faiss.read_index(str(index_path))
                print(f"✅ Loaded FAISS index with {self.index.ntotal} vectors")
            except Exception as e:
                print(f"❌ Failed to load FAISS index: {e}")
                self.index = faiss.IndexFlatIP(self.embedding_dim)

        if metadata_path.exists():
            try:
                with open(metadata_path, 'r') as f:
                    data = json.load(f)
                    self.id_to_vector = data.get('id_to_vector', {})
                    self.vector_to_id = {int(k): v for k, v in data.get('vector_to_id', {}).items()}
                    self.metadata = data.get('metadata', {})
                print(f"✅ Loaded metadata for {len(self.metadata)} items")
            except Exception as e:
                print(f"❌ Failed to load metadata: {e}")

    def _save_index(self):
        """Save FAISS index and metadata"""

        try:
            # Save FAISS index
            faiss.write_index(self.index, str(self.storage_path / "faiss_index.bin"))

            # Save metadata
            data = {
                'id_to_vector': self.id_to_vector,
                'vector_to_id': self.vector_to_id,
                'metadata': self.metadata,
                'last_updated': datetime.now().isoformat()
            }

            with open(self.storage_path / "metadata.json", 'w') as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            print(f"❌ Failed to save vector store: {e}")

    def _get_embedding(self, text: str) -> np.ndarray:
        """Get embedding vector for text"""

        if SENTENCE_TRANSFORMERS_AVAILABLE and self.embedding_model:
            return self.embedding_model.encode(text, convert_to_numpy=True, normalize_embeddings=True)
        else:
            # Fallback: simple hash-based embedding (not semantic, but deterministic)
            hash_obj = hashlib.md5(text.encode())
            hash_bytes = hash_obj.digest()
            # Convert to fixed-size vector and normalize
            vector = np.frombuffer(hash_bytes, dtype=np.uint8).astype(np.float32)
            # Pad or truncate to embedding dimension
            if len(vector) < self.embedding_dim:
                vector = np.pad(vector, (0, self.embedding_dim - len(vector)))
            else:
                vector = vector[:self.embedding_dim]
            # Normalize
            norm = np.linalg.norm(vector)
            return vector / norm if norm > 0 else vector

    def add_vector(self, id: str, text: str, metadata: Dict[str, Any] = None) -> bool:
        """Add a text vector to the store"""

        try:
            # Get embedding
            vector = self._get_embedding(text)

            # Add to FAISS index
            vector_2d = vector.reshape(1, -1)
            self.index.add(vector_2d)

            # Store mappings
            vector_index = self.index.ntotal - 1
            self.id_to_vector[id] = vector_index
            self.vector_to_id[vector_index] = id
            self.metadata[id] = {
                "text": text,
                "added_at": datetime.now().isoformat(),
                "vector_norm": float(np.linalg.norm(vector)),
                **(metadata or {})
            }

            # Auto-save periodically
            if self.index.ntotal % 100 == 0:
                self._save_index()

            return True

        except Exception as e:
            print(f"❌ Failed to add vector {id}: {e}")
            return False

    def search_similar(self, query: str, top_k: int = 5,
                      threshold: float = 0.0) -> List[Dict[str, Any]]:
        """Search for similar vectors"""

        try:
            # Get query embedding
            query_vector = self._get_embedding(query)
            query_2d = query_vector.reshape(1, -1)

            # Search
            scores, indices = self.index.search(query_2d, min(top_k, self.index.ntotal))

            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx == -1 or score < threshold:
                    continue

                vector_id = self.vector_to_id.get(idx)
                if vector_id and vector_id in self.metadata:
                    result = {
                        "id": vector_id,
                        "score": float(score),
                        "metadata": self.metadata[vector_id]
                    }
                    results.append(result)

            return results

        except Exception as e:
            print(f"❌ Search failed: {e}")
            return []

    def get_vector(self, id: str) -> Optional[np.ndarray]:
        """Get vector by ID"""

        if id in self.id_to_vector:
            vector_index = self.id_to_vector[id]
            try:
                # Use FAISS reconstruct to get the stored vector
                vector = self.index.reconstruct(int(vector_index))
                return vector
            except Exception as e:
                # Fallback: re-embed from stored text if reconstruction fails
                if id in self.metadata and 'text' in self.metadata[id]:
                    return self._get_embedding(self.metadata[id]['text'])
                return None

        return None

    def update_vector(self, id: str, new_text: str, metadata: Dict[str, Any] = None) -> bool:
        """Update existing vector"""

        try:
            # Remove old vector
            if id in self.id_to_vector:
                # FAISS doesn't support direct removal, so we'd need to rebuild the index
                # For simplicity, we'll add the new vector and mark the old one as obsolete
                pass

            # Add new vector
            return self.add_vector(id, new_text, metadata)

        except Exception as e:
            print(f"❌ Failed to update vector {id}: {e}")
            return False

    def delete_vector(self, id: str) -> bool:
        """Delete vector (marks as deleted, doesn't rebuild index)"""

        try:
            if id in self.metadata:
                self.metadata[id]["deleted"] = True
                self.metadata[id]["deleted_at"] = datetime.now().isoformat()
                return True
            return False

        except Exception as e:
            print(f"❌ Failed to delete vector {id}: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """Get vector store statistics"""

        total_vectors = self.index.ntotal
        active_vectors = len([m for m in self.metadata.values() if not m.get("deleted", False)])

        return {
            "total_vectors": total_vectors,
            "active_vectors": active_vectors,
            "deleted_vectors": total_vectors - active_vectors,
            "embedding_dimension": self.embedding_dim,
            "embedding_model": self.embedding_model_name,
            "model_available": SENTENCE_TRANSFORMERS_AVAILABLE and self.embedding_model is not None
        }

    def cleanup(self):
        """Cleanup and save state"""
        self._save_index()

class SemanticMemoryStore:
    """Enhanced memory store with semantic search capabilities"""

    def __init__(self, storage_path: Path = None):
        self.storage_path = storage_path or Path("./semantic_memory")
        self.storage_path.mkdir(parents=True, exist_ok=True)

        # Initialize vector store
        self.vector_store = VectorStore(self.storage_path / "vectors")

        # Initialize SQLite for structured data
        self.db_path = self.storage_path / "semantic_memory.db"
        self._init_db()

        print("🧠 Semantic memory store initialized")

    def _init_db(self):
        """Initialize semantic memory database"""

        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS memory_records (
                id TEXT PRIMARY KEY,
                content_type TEXT NOT NULL,
                content TEXT NOT NULL,
                summary TEXT,
                tags TEXT,  -- JSON array
                importance REAL DEFAULT 0.5,
                access_count INTEGER DEFAULT 0,
                last_accessed TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                layer TEXT DEFAULT 'persistent'
            )
        """)

        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS memory_relationships (
                id TEXT PRIMARY KEY,
                source_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                relationship_type TEXT NOT NULL,
                strength REAL DEFAULT 0.5,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (source_id) REFERENCES memory_records(id),
                FOREIGN KEY (target_id) REFERENCES memory_records(id)
            )
        """)

        # Create indexes
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_content_type ON memory_records(content_type)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_tags ON memory_records(tags)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_importance ON memory_records(importance)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_relationships ON memory_relationships(source_id, target_id)")

        self.conn.commit()

    def store_memory(self, content: str, content_type: str = "text",
                    summary: str = None, tags: List[str] = None,
                    importance: float = 0.5, layer: str = "persistent",
                    expires_at: datetime = None) -> str:
        """Store memory with semantic indexing"""

        try:
            # Generate ID
            memory_id = hashlib.md5(f"{content_type}_{content}_{datetime.now().isoformat()}".encode()).hexdigest()[:16]

            # Auto-generate summary if not provided
            if not summary:
                summary = self._generate_summary(content)

            # Auto-generate tags if not provided
            if not tags:
                tags = self._extract_tags(content)

            # Store in database
            self.conn.execute("""
                INSERT INTO memory_records
                (id, content_type, content, summary, tags, importance, layer, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                memory_id,
                content_type,
                content,
                summary,
                json.dumps(tags),
                importance,
                layer,
                expires_at.isoformat() if expires_at else None
            ))

            # Add to vector store for semantic search
            vector_text = f"{summary} {' '.join(tags)} {content[:500]}"  # Combine for better search
            metadata = {
                "content_type": content_type,
                "importance": importance,
                "tags": tags,
                "layer": layer
            }

            self.vector_store.add_vector(memory_id, vector_text, metadata)

            self.conn.commit()

            print(f"✅ Stored semantic memory: {memory_id}")
            return memory_id

        except Exception as e:
            print(f"❌ Failed to store memory: {e}")
            return None

    def retrieve_memory(self, query: str, content_type: str = None,
                       tags: List[str] = None, min_importance: float = 0.0,
                       top_k: int = 5) -> List[Dict[str, Any]]:
        """Retrieve memory using semantic search"""

        try:
            # Semantic search
            semantic_results = self.vector_store.search_similar(query, top_k=top_k * 2)

            # Filter and rank results
            filtered_results = []

            for result in semantic_results:
                memory_id = result["id"]
                score = result["score"]
                metadata = result["metadata"]

                # Apply filters
                if content_type and metadata.get("content_type") != content_type:
                    continue
                if tags and not any(tag in metadata.get("tags", []) for tag in tags):
                    continue
                if metadata.get("importance", 0) < min_importance:
                    continue
                if metadata.get("deleted"):
                    continue

                # Get full record from database
                record = self._get_memory_record(memory_id)
                if record:
                    record["semantic_score"] = score
                    filtered_results.append(record)

                    # Update access statistics
                    self._update_access_stats(memory_id)

            # Sort by combined score (semantic + importance + recency)
            filtered_results.sort(key=lambda x: self._calculate_combined_score(x), reverse=True)

            return filtered_results[:top_k]

        except Exception as e:
            print(f"❌ Memory retrieval failed: {e}")
            return []

    def _get_memory_record(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """Get memory record from database"""

        cursor = self.conn.execute("""
            SELECT * FROM memory_records WHERE id = ?
        """, (memory_id,))

        row = cursor.fetchone()
        if row:
            columns = [desc[0] for desc in cursor.description]
            record = dict(zip(columns, row))

            # Parse JSON fields
            record["tags"] = json.loads(record["tags"]) if record["tags"] else []
            record["expires_at"] = datetime.fromisoformat(record["expires_at"]) if record["expires_at"] else None
            record["last_accessed"] = datetime.fromisoformat(record["last_accessed"]) if record["last_accessed"] else None

            return record

        return None

    def _update_access_stats(self, memory_id: str):
        """Update access statistics for memory record"""

        self.conn.execute("""
            UPDATE memory_records SET
                access_count = access_count + 1,
                last_accessed = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (memory_id,))
        self.conn.commit()

    def _calculate_combined_score(self, record: Dict) -> float:
        """Calculate combined relevance score"""

        semantic_score = record.get("semantic_score", 0.0)
        importance = record.get("importance", 0.5)
        access_count = record.get("access_count", 0)

        # Recency bonus (newer items get slight boost)
        recency_bonus = 0.0
        if record.get("last_accessed"):
            days_since_access = (datetime.now() - record["last_accessed"]).days
            recency_bonus = max(0, 0.1 * (30 - days_since_access) / 30)  # Bonus decays over 30 days

        # Access frequency bonus
        access_bonus = min(0.2, access_count * 0.01)  # Up to 0.2 bonus for frequently accessed items

        return semantic_score + (importance * 0.3) + recency_bonus + access_bonus

    def _generate_summary(self, content: str) -> str:
        """Generate automatic summary of content"""

        # Simple extractive summarization
        sentences = content.split('.')
        sentences = [s.strip() for s in sentences if s.strip()]

        if len(sentences) <= 2:
            return content[:200] + "..." if len(content) > 200 else content

        # Return first and last sentences as summary
        summary = f"{sentences[0]}. {sentences[-1] if len(sentences) > 1 else ''}".strip()
        return summary[:300] + "..." if len(summary) > 300 else summary

    def _extract_tags(self, content: str) -> List[str]:
        """Extract tags from content"""

        # Simple keyword extraction
        words = content.lower().split()
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}

        keywords = [word for word in words if len(word) > 3 and word not in stop_words]

        # Get most common keywords (simple frequency)
        from collections import Counter
        word_counts = Counter(keywords)
        top_keywords = [word for word, count in word_counts.most_common(5) if count > 1]

        return top_keywords

    def add_relationship(self, source_id: str, target_id: str,
                        relationship_type: str, strength: float = 0.5) -> bool:
        """Add relationship between memory records"""

        try:
            rel_id = hashlib.md5(f"{source_id}_{target_id}_{relationship_type}".encode()).hexdigest()[:16]

            self.conn.execute("""
                INSERT OR REPLACE INTO memory_relationships
                (id, source_id, target_id, relationship_type, strength)
                VALUES (?, ?, ?, ?, ?)
            """, (rel_id, source_id, target_id, relationship_type, strength))

            self.conn.commit()
            return True

        except Exception as e:
            print(f"❌ Failed to add relationship: {e}")
            return False

    def get_related_memories(self, memory_id: str, relationship_type: str = None,
                           min_strength: float = 0.0) -> List[Dict[str, Any]]:
        """Get related memories"""

        try:
            query = """
                SELECT mr.*, rel.relationship_type, rel.strength
                FROM memory_relationships rel
                JOIN memory_records mr ON rel.target_id = mr.id
                WHERE rel.source_id = ? AND rel.strength >= ?
            """

            params = [memory_id, min_strength]

            if relationship_type:
                query += " AND rel.relationship_type = ?"
                params.append(relationship_type)

            cursor = self.conn.execute(query, params)

            related = []
            for row in cursor.fetchall():
                columns = [desc[0] for desc in cursor.description]
                record = dict(zip(columns, row))
                record["tags"] = json.loads(record["tags"]) if record["tags"] else []
                related.append(record)

            return related

        except Exception as e:
            print(f"❌ Failed to get related memories: {e}")
            return []

    def cleanup_expired(self) -> int:
        """Clean up expired memory records"""

        try:
            cursor = self.conn.execute("""
                SELECT id FROM memory_records
                WHERE expires_at IS NOT NULL AND expires_at < CURRENT_TIMESTAMP
            """)

            expired_ids = [row[0] for row in cursor.fetchall()]

            if expired_ids:
                # Mark as deleted in vector store
                for memory_id in expired_ids:
                    self.vector_store.delete_vector(memory_id)

                # Delete from database
                self.conn.executemany("""
                    DELETE FROM memory_records WHERE id = ?
                """, [(mid,) for mid in expired_ids])

                self.conn.commit()

                print(f"🧹 Cleaned up {len(expired_ids)} expired memories")
                return len(expired_ids)

            return 0

        except Exception as e:
            print(f"❌ Cleanup failed: {e}")
            return 0

    def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory statistics"""

        try:
            # Get record counts
            cursor = self.conn.execute("""
                SELECT
                    COUNT(*) as total_records,
                    COUNT(CASE WHEN layer = 'ephemeral' THEN 1 END) as ephemeral_count,
                    COUNT(CASE WHEN layer = 'session' THEN 1 END) as session_count,
                    COUNT(CASE WHEN layer = 'persistent' THEN 1 END) as persistent_count,
                    AVG(importance) as avg_importance,
                    SUM(access_count) as total_accesses
                FROM memory_records
            """)

            row = cursor.fetchone()
            record_stats = {
                "total_records": row[0],
                "ephemeral_count": row[1],
                "session_count": row[2],
                "persistent_count": row[3],
                "avg_importance": row[4] or 0.0,
                "total_accesses": row[5] or 0
            }

            # Get relationship stats
            cursor = self.conn.execute("""
                SELECT COUNT(*) as total_relationships,
                       COUNT(DISTINCT relationship_type) as relationship_types,
                       AVG(strength) as avg_strength
                FROM memory_relationships
            """)

            row = cursor.fetchone()
            relationship_stats = {
                "total_relationships": row[0],
                "relationship_types": row[1],
                "avg_strength": row[2] or 0.0
            }

            # Get vector store stats
            vector_stats = self.vector_store.get_stats()

            return {
                "records": record_stats,
                "relationships": relationship_stats,
                "vectors": vector_stats,
                "last_cleanup": datetime.now().isoformat()
            }

        except Exception as e:
            print(f"❌ Failed to get memory stats: {e}")
            return {}

    def optimize_storage(self):
        """Optimize storage and rebuild indexes if needed"""

        try:
            # Cleanup expired records
            expired_count = self.cleanup_expired()

            # Rebuild vector index if needed (simplified - just save current state)
            self.vector_store.cleanup()

            # Vacuum database
            self.conn.execute("VACUUM")
            self.conn.commit()

            print(f"🔧 Optimized storage: cleaned {expired_count} expired records")

        except Exception as e:
            print(f"❌ Optimization failed: {e}")

# Global instance
_semantic_memory = None

def get_semantic_memory() -> SemanticMemoryStore:
    """Get global semantic memory instance"""
    global _semantic_memory
    if _semantic_memory is None:
        _semantic_memory = SemanticMemoryStore()
    return _semantic_memory

# Convenience functions
def store_semantic_memory(content: str, **kwargs) -> str:
    """Store content in semantic memory"""
    return get_semantic_memory().store_memory(content, **kwargs)

def retrieve_semantic_memory(query: str, **kwargs) -> List[Dict[str, Any]]:
    """Retrieve from semantic memory using semantic search"""
    return get_semantic_memory().retrieve_memory(query, **kwargs)

def get_semantic_memory_stats() -> Dict[str, Any]:
    """Get semantic memory statistics"""
    return get_semantic_memory().get_memory_stats()

if __name__ == "__main__":
    # Test semantic memory system
    print("🧠 Testing Semantic Memory System...")

    try:
        # Initialize semantic memory
        memory = get_semantic_memory()
        print("✅ Semantic memory initialized")

        # Test storing memory
        memory_id = memory.store_memory(
            "The DIGITAL LABOUR doctrine emphasizes memory optimization and context preservation across all operations.",
            content_type="doctrine",
            importance=0.9,
            tags=["doctrine", "memory", "optimization"]
        )
        print(f"✅ Stored memory: {memory_id}")

        # Test semantic search
        results = memory.retrieve_memory("memory optimization doctrine", top_k=3)
        print(f"✅ Semantic search returned {len(results)} results")

        # Test relationships
        memory_id2 = memory.store_memory(
            "Context compression algorithms improve memory efficiency by semantic analysis.",
            content_type="technical",
            importance=0.8,
            tags=["compression", "algorithms", "efficiency"]
        )

        memory.add_relationship(memory_id, memory_id2, "related_technology", 0.8)
        print("✅ Added memory relationship")

        # Test related memories
        related = memory.get_related_memories(memory_id)
        print(f"✅ Found {len(related)} related memories")

        # Test stats
        stats = memory.get_memory_stats()
        print(f"✅ Memory stats: {stats['records']['total_records']} records")

        print("🎉 Semantic Memory System ready!")

    except Exception as e:
        print(f"❌ Semantic memory test failed: {e}")
        import traceback
        traceback.print_exc()
