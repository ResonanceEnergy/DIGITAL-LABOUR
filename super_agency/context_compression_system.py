#!/usr/bin/env python3
"""
BIT RAGE LABOUR Context Compression System
Advanced memory optimization with semantic compression and vector search
"""

import hashlib
import json
import os
import re
import sqlite3
import threading
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

try:
    # Optional: Use sentence-transformers for semantic search if available
    from sentence_transformers import SentenceTransformer
    SEMANTIC_SEARCH_AVAILABLE = True
except ImportError:
    SEMANTIC_SEARCH_AVAILABLE = False
    print("⚠️  Semantic search not available - install sentence-transformers for enhanced features")

class ContextCompressor:
    """Advanced context compression using semantic analysis"""

    def __init__(self):
        """Initialize."""
        self.compression_stats = {
            "total_compressed": 0,
            "compression_ratio": 0.0,
            "semantic_clusters": 0
        }

        # Initialize semantic model if available
        self.semantic_model = None
        global SEMANTIC_SEARCH_AVAILABLE  # pylint: disable=global-statement
        if SEMANTIC_SEARCH_AVAILABLE:
            try:
                self.semantic_model = SentenceTransformer('all-MiniLM-L6-v2')
                print("✅ Semantic search model loaded")
            except Exception as e:
                print(f"⚠️  Failed to load semantic model: {e}")
                SEMANTIC_SEARCH_AVAILABLE = False

    def compress_conversation(self, messages: List[Dict]) -> Dict:
        """Compress a conversation using semantic analysis"""
        if not messages:
            return {"compressed": "", "summary": "", "key_points": []}

        # Extract text content
        text_content = []
        for msg in messages:
            if isinstance(msg, dict) and "content" in msg:
                text_content.append(msg["content"])
            elif isinstance(msg, str):
                text_content.append(msg)

        full_text = " ".join(text_content)

        # Basic compression: remove redundant information
        compressed = self._basic_compress(full_text)

        # Semantic compression if available
        if SEMANTIC_SEARCH_AVAILABLE and self.semantic_model:
            semantic_summary = self._semantic_compress(text_content)
        else:
            semantic_summary = self._extractive_summarize(full_text)

        # Extract key points
        key_points = self._extract_key_points(full_text)

        result = {
            "compressed": compressed, "summary": semantic_summary,
            "key_points": key_points, "original_length": len(full_text),
            "compressed_length": len(compressed),
            "compression_ratio": len(compressed) /len(full_text)
            if full_text else 0, "timestamp": datetime.now().isoformat()}

        # Update stats
        self.compression_stats["total_compressed"] += 1
        if result["compression_ratio"] > 0:
            self.compression_stats["compression_ratio"] = (
                self.compression_stats["compression_ratio"] +
                result["compression_ratio"]
            ) / 2

        return result

    def _basic_compress(self, text: str) -> str:
        """Basic text compression by removing redundancy"""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text.strip())

        # Remove common filler phrases
        fillers = [
            r'\b(um|uh|like|you know|so|well|actually)\b',
            r'\b(i think|i mean|i guess)\b',
            r'\b(kind of|sort of|pretty much)\b'
        ]

        for filler in fillers:
            text = re.sub(filler, '', text, flags=re.IGNORECASE)

        # Remove repeated words/phrases
        words = text.split()
        compressed_words = []
        prev_word = None

        for word in words:
            if word.lower() != prev_word:
                compressed_words.append(word)
            prev_word = word.lower()

        return " ".join(compressed_words)

    def _semantic_compress(self, messages: List[str]) -> str:
        """Semantic compression using sentence embeddings"""
        if not self.semantic_model or not messages:
            return self._extractive_summarize(" ".join(messages))

        try:
            # Generate embeddings
            embeddings = self.semantic_model.encode(messages)

            # Find most representative sentences (centroid method)
            centroid = np.mean(embeddings, axis=0)

            # Calculate similarities to centroid
            similarities = np.dot(embeddings, centroid) / (
                np.linalg.norm(embeddings, axis=1) * np.linalg.norm(centroid)
            )

            # Select top sentences
            # Top 3 most representative
            top_indices = np.argsort(similarities)[-3:]
            summary_sentences = [messages[i] for i in sorted(top_indices)]

            return " ".join(summary_sentences)

        except Exception as e:
            print(f"⚠️  Semantic compression failed: {e}")
            return self._extractive_summarize(" ".join(messages))

    def _extractive_summarize(self, text: str, max_length: int = 200) -> str:
        """Extractive summarization as fallback"""
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]

        if not sentences:
            return text[:max_length]

        # Score sentences by length and position
        scored_sentences = []
        for i, sentence in enumerate(sentences):
            score = len(sentence.split())  # Length score
            # Position score (later sentences slightly higher)
            score += (len(sentences) - i) * 0.1
            scored_sentences.append((score, sentence))

        # Select top sentences
        scored_sentences.sort(reverse=True)
        selected = scored_sentences[:3]  # Top 3 sentences
        # Maintain original order
        selected.sort(key=lambda x: sentences.index(x[1]))

        summary = " ".join([s[1] for s in selected])
        return summary[:max_length]

    def _extract_key_points(self, text: str) -> List[str]:
        """Extract key points from text"""
        # Look for action items, decisions, and important statements
        key_indicators = [
            r'\b(will|should|must|need to|plan to|going to)\b',
            r'\b(decided|decision|conclusion|outcome)\b',
            r'\b(important|critical|key|essential)\b',
            r'\b(implement|create|build|develop)\b'
        ]

        sentences = re.split(r'[.!?]+', text)
        key_points = []

        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence.split()) < 5:  # Skip very short sentences
                continue

            # Check if sentence contains key indicators
            for indicator in key_indicators:
                if re.search(indicator, sentence, re.IGNORECASE):
                    key_points.append(sentence)
                    break

        return key_points[:5]  # Limit to 5 key points

class VectorMemoryStore:
    """Vector-based memory storage for semantic search"""


    def __init__(self, db_path: Path = None):
        """__init__ handler."""
        self.db_path = db_path or Path("./memory/vector_memory.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

        # Initialize semantic model
        self.semantic_model = None
        if SEMANTIC_SEARCH_AVAILABLE:
            try:
                self.semantic_model = SentenceTransformer('all-MiniLM-L6-v2')
            except:
                pass

    def _init_db(self):
        """Initialize vector memory database"""
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS vector_memory (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                vector TEXT,  -- JSON array of floats
                metadata TEXT,
                importance REAL DEFAULT 0.5,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                access_count INTEGER DEFAULT 0,
                last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create vector index table for fast similarity search
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS vector_index (
                id TEXT PRIMARY KEY,
                cluster_id INTEGER,
                centroid_distance REAL,
                FOREIGN KEY (id) REFERENCES vector_memory (id)
            )
        """)

        self.conn.commit()

    def store_vector(self, content: str, metadata: Dict = None, importance: float = 0.5) -> bool:
        """Store content with vector embedding"""
        try:
            vector = None
            if self.semantic_model:
                # Generate embedding
                embedding = self.semantic_model.encode([content])[0]
                vector = json.dumps(embedding.tolist())

            # Store in database
            doc_id = hashlib.md5(content.encode()).hexdigest()[:16]

            self.conn.execute("""
                INSERT OR REPLACE INTO vector_memory
                (id, content, vector, metadata, importance)
                VALUES (?, ?, ?, ?, ?)
            """, (
                doc_id,
                content,
                vector,
                json.dumps(metadata or {}),
                importance
            ))

            self.conn.commit()
            return True

        except Exception as e:
            print(f"❌ Vector storage failed: {e}")
            return False

    def semantic_search(self, query: str, limit: int = 5) -> List[Dict]:
        """Perform semantic search using vector similarity"""
        if not self.semantic_model:
            # Fallback to text search
            return self._text_search(query, limit)

        try:
            # Generate query embedding
            query_embedding = self.semantic_model.encode([query])[0]

            # Retrieve all vectors and calculate similarities
            cursor = self.conn.execute("""
                SELECT id, content, vector, metadata, importance
                FROM vector_memory
                WHERE vector IS NOT NULL
            """)

            results = []
            for row in cursor.fetchall():
                doc_id, content, vector_str, metadata_str, importance = row

                if vector_str:
                    stored_vector = np.array(json.loads(vector_str))

                    # Calculate cosine similarity
                    similarity = np.dot(query_embedding, stored_vector) / (
                        np.linalg.norm(query_embedding) * \
                                       np.linalg.norm(stored_vector)
                    )

                    metadata = json.loads(metadata_str) if metadata_str else {}

                    results.append({
                        "id": doc_id,
                        "content": content,
                        "similarity": float(similarity),
                        "metadata": metadata,
                        "importance": importance
                    })

            # Sort by similarity and importance
            results.sort(key=lambda x: x["similarity"] * \
                         (0.7 + 0.3 * x["importance"]), reverse=True)

            return results[:limit]

        except Exception as e:
            print(f"❌ Semantic search failed: {e}")
            return self._text_search(query, limit)

    def _text_search(self, query: str, limit: int = 5) -> List[Dict]:
        """Fallback text-based search"""
        try:
            # Simple text matching
            query_lower = query.lower()
            cursor = self.conn.execute("""
                SELECT id, content, metadata, importance
                FROM vector_memory
                WHERE LOWER(content) LIKE ?
                ORDER BY importance DESC
                LIMIT ?
            """, (f"%{query_lower}%", limit))

            results = []
            for row in cursor.fetchall():
                doc_id, content, metadata_str, importance = row
                metadata = json.loads(metadata_str) if metadata_str else {}

                results.append({
                    "id": doc_id,
                    "content": content,
                    "similarity": 0.5,  # Default similarity for text search
                    "metadata": metadata,
                    "importance": importance
                })

            return results

        except Exception as e:
            print(f"❌ Text search failed: {e}")
            return []


class MemoryCompressor:
    """__init__ handler."""
    """Advanced memory compression and optimization system"""

    def __init__(self, storage_path: Path = None):
        self.storage_path = storage_path or Path(
            "./memory/compressed_memory.db")
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        self.context_compressor = ContextCompressor()
        self.vector_store = VectorMemoryStore()

        # Compression settings
        self.compression_threshold = 1000  # Characters
        # How long to keep compressed data
        self.retention_period = timedelta(days=30)

        self._init_db()

    def _init_db(self):
        """Initialize compressed memory database"""
        self.conn = sqlite3.connect(str(self.storage_path))
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS compressed_memory (
                id TEXT PRIMARY KEY,
                original_content TEXT,
                compressed_data TEXT,  -- JSON with compression results
                compression_type TEXT,  -- 'context' or 'semantic'
                original_size INTEGER,
                compressed_size INTEGER,
                compression_ratio REAL,
                importance REAL DEFAULT 0.5,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                access_count INTEGER DEFAULT 0
            )
        """)
        self.conn.commit()

    def compress_and_store(
            self, content: str, content_type: str="conversation",
            metadata: Dict=None) ->Dict:
        """Compress content and store in compressed memory"""

        if len(content) < self.compression_threshold:
            # Don't compress small content
            return {
                "compressed": False,
                "reason": "content_too_small",
                "original_size": len(content)
            }

        try:
            if content_type == "conversation":
                # Use context compression for conversations
                compressed_data = self.context_compressor.compress_conversation([
                                                                                content])
                compression_type = "context"
            else:
                # Use semantic compression for other content
                compressed_data = self.context_compressor.compress_conversation([
                                                                                content])
                compression_type = "semantic"

            # Store compressed data
            doc_id = hashlib.md5(content.encode()).hexdigest()[:16]

            self.conn.execute("""
                INSERT OR REPLACE INTO compressed_memory
                (id, original_content, compressed_data, compression_type,
                 original_size, compressed_size, compression_ratio, importance)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                doc_id,
                content,
                json.dumps(compressed_data),
                compression_type,
                len(content),
                len(compressed_data.get("compressed", "")),
                compressed_data.get("compression_ratio", 0),
                metadata.get("importance", 0.5) if metadata else 0.5
            ))

            self.conn.commit()

            # Also store in vector memory for search
            summary = compressed_data.get(
                "summary", compressed_data.get("compressed", ""))
            if summary:
                self.vector_store.store_vector(
                    summary,
                    metadata={"original_id": doc_id,
                        "compression_type": compression_type},
                    importance=metadata.get(
                        "importance", 0.5) if metadata else 0.5
                )

            return {
                "compressed": True,
                "compression_type": compression_type,
                "compression_ratio": compressed_data.get("compression_ratio", 0),
                "original_size": len(content),
                "compressed_size": len(compressed_data.get("compressed", "")),
                "key_points": compressed_data.get("key_points", [])
            }

        except Exception as e:
            print(f"❌ Compression failed: {e}")
            return {
                "compressed": False,
                "reason": f"compression_error: {str(e)}",
                "original_size": len(content)
            }

    def retrieve_compressed(self, doc_id: str) -> Optional[Dict]:
        """Retrieve compressed content"""
        try:
            cursor = self.conn.execute("""
                SELECT original_content, compressed_data, compression_type,
                       original_size, compressed_size, compression_ratio
                FROM compressed_memory
                WHERE id = ?
            """, (doc_id,))

            row = cursor.fetchone()
            if row:
                original_content, compressed_data_str, compression_type, \
                original_size, compressed_size, compression_ratio = row

                compressed_data = json.loads(compressed_data_str)

                # Update access statistics
                self.conn.execute("""
                    UPDATE compressed_memory
                    SET access_count = access_count + 1,
                        last_accessed = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (doc_id,))

                self.conn.commit()

                return {
                    "id": doc_id,
                    "original_content": original_content,
                    "compressed_data": compressed_data,
                    "compression_type": compression_type,
                    "original_size": original_size,
                    "compressed_size": compressed_size,
                    "compression_ratio": compression_ratio
                }

        except Exception as e:
            print(f"❌ Retrieval failed: {e}")

        return None

    def semantic_search_memory(self, query: str, limit: int = 5) -> List[Dict]:
        """Search compressed memory using semantic similarity"""
        return self.vector_store.semantic_search(query, limit)

    def get_compression_stats(self) -> Dict:
        """Get compression statistics"""
        try:
            cursor = self.conn.execute("""
                SELECT
                    COUNT(*) as total_items,
                    AVG(compression_ratio) as avg_compression_ratio,
                    SUM(original_size) as total_original_size,
                    SUM(compressed_size) as total_compressed_size,
                    AVG(importance) as avg_importance
                FROM compressed_memory
            """)

            row = cursor.fetchone()
            if row:
                total_items, avg_ratio, total_orig, total_comp, avg_imp = row

                return {
                    "total_compressed_items": total_items or 0,
                    "average_compression_ratio": avg_ratio or 0,
                    "total_original_size": total_orig or 0,
                    "total_compressed_size": total_comp or 0,
                    "average_importance": avg_imp or 0,
                    "space_savings_percent": (
                        (total_orig - total_comp) / total_orig * 100
                        if total_orig and total_orig > 0 else 0
                    )
                }

        except Exception as e:
            print(f"❌ Stats retrieval failed: {e}")

        return {
            "total_compressed_items": 0,
            "average_compression_ratio": 0,
            "total_original_size": 0,
            "total_compressed_size": 0,
            "average_importance": 0,
            "space_savings_percent": 0
        }

    def cleanup_old_compressed(self, max_age_days: int = 90) -> int:
        """Clean up old compressed memory"""
        try:
            cutoff_date = (datetime.now() - \
                           timedelta(days=max_age_days)).isoformat()

            cursor = self.conn.execute("""
                DELETE FROM compressed_memory
                WHERE last_accessed < ?
                AND importance < 0.7  -- Keep high-importance items longer
            """, (cutoff_date,))

            deleted_count = cursor.rowcount
            self.conn.commit()

            return deleted_count

        except Exception as e:
            print(f"❌ Cleanup failed: {e}")
            return 0

# Global instances
_context_compressor = None
_memory_compressor = None

def get_context_compressor() -> ContextCompressor:
    """Get global context compressor instance"""
    global _context_compressor
    if _context_compressor is None:
        _context_compressor = ContextCompressor()
    return _context_compressor

def get_memory_compressor() -> MemoryCompressor:
    """Get global memory compressor instance"""
    global _memory_compressor
    if _memory_compressor is None:
        _memory_compressor = MemoryCompressor()
    return _memory_compressor

# Convenience functions
def compress_content(content: str, content_type: str="conversation",
                     metadata: Dict=None) ->Dict:
    """Compress content using advanced algorithms"""
    return get_memory_compressor().compress_and_store(content, content_type, metadata)

def search_memory(query: str, limit: int = 5) -> List[Dict]:
    """Search compressed memory semantically"""
    return get_memory_compressor().semantic_search_memory(query, limit)

def get_compression_stats() -> Dict:
    """Get memory compression statistics"""
    return get_memory_compressor().get_compression_stats()


class ContextCompressionSystem:
    """
    Main facade class for the Context Compression System.
    Provides unified access to compression, storage, and search capabilities.
    """

    def __init__(self):
        self.compressor = ContextCompressor()
        self.vector_store = VectorMemoryStore()
        self.memory_compressor = get_memory_compressor()

    def compress_content(
            self, content: str, content_type: str="conversation",
            metadata: Dict=None) ->Dict:
        """Compress content using advanced algorithms"""
        return self.memory_compressor.compress_and_store(
            content, content_type, metadata)

    def search_memory(self, query: str, limit: int = 5) -> List[Dict]:
        """Search compressed memory semantically"""
        return self.memory_compressor.semantic_search_memory(query, limit)

    def compress_conversation(self, messages: List[Dict]) -> Dict:
        """Compress a conversation using semantic analysis"""
        return self.compressor.compress_conversation(messages)

    def get_compression_stats(self) -> Dict:
        """Get memory compression statistics"""
        return self.memory_compressor.get_compression_stats()

    def get_system_status(self) -> Dict:
        """Get overall system status"""
        return {
            "compressor_ok": self.compressor is not None,
            "vector_store_ok": self.vector_store is not None,
            "semantic_search_available": SEMANTIC_SEARCH_AVAILABLE,
            "stats": self.get_compression_stats()
        }


if __name__ == "__main__":
    # Test the compression system
    print("🗜️  Testing Context Compression System...")

    # Test basic compression
    test_content = """
    Hello, I am working on the BIT RAGE LABOUR project. The BIT RAGE LABOUR is a comprehensive system
    that manages various aspects of AI operations. I think the memory system is really important.
    The memory system helps maintain context across conversations. I believe this will solve
    many of the issues we've been facing with AI memory loss. The doctrine system ensures that
    all operations follow established principles. I think this is a good approach.
    """

    print("📝 Original content length:", len(test_content))

    # Test compression
    result = compress_content(
        test_content, "conversation", {"importance": 0.8})
    print("✅ Compression result:", result)

    # Test semantic search
    search_results = search_memory("memory system", 3)
    print("🔍 Search results:", len(search_results), "found")

    # Test stats
    stats = get_compression_stats()
    print("📊 Compression stats:", stats)

    print("✅ Context Compression System ready!")
