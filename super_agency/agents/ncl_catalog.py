#!/usr/bin/env python3
"""
NCL Catalog Manager - Second Brain Integration

Manages the NCL (Neural Cognitive Lattice) catalog for indexing
enriched content and maintaining knowledge graph connections.
"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

# Import from common utilities
from .common import CONFIG, Log, ensure_dir

# NCL Catalog configuration
NCL_DIR = Path(CONFIG.get("ncl_dir", "./NCL"))
CATALOG_DIR = NCL_DIR / "catalog"
ensure_dir(CATALOG_DIR)

class NCLCatalog:
    """Manages NCL catalog entries and knowledge graph connections"""

    def __init__(self):
        self.catalog_file = CATALOG_DIR / "index.json"
        self.entries_file = CATALOG_DIR / "entries.ndjson"
        self.graph_file = CATALOG_DIR / "graph.json"

        # Load existing catalog
        self.catalog = self._load_catalog()
        self.graph = self._load_graph()

    def _load_catalog(self) -> Dict[str, Any]:
        """Load catalog index"""
        if self.catalog_file.exists():
            try:
                return json.loads(self.catalog_file.read_text(
                                      encoding='utf-8'))
            except (json.JSONDecodeError, OSError):
                pass
        return {
            "version": "1.0",
            "created": datetime.now().isoformat(),
            "entries": {},
            "last_updated": datetime.now().isoformat()
        }

    def _load_graph(self) -> Dict[str, Any]:
        """Load knowledge graph"""
        if self.graph_file.exists():
            try:
                return json.loads(self.graph_file.read_text(encoding='utf-8'))
            except (json.JSONDecodeError, OSError):
                pass
        return {
            "nodes": [],
            "edges": [],
            "last_updated": datetime.now().isoformat()
        }

    def add_entry(self, enrich_data: Dict[str, Any]) -> bool:
        """Add enriched content to NCL catalog"""
        try:
            video_id = enrich_data["video_id"]
            entry_id = f"video_{video_id}"

            # Create catalog entry
            entry = {
                "id": entry_id,
                "type": "youtube_video",
                "content_type": "second_brain_enrichment",
                "timestamp": datetime.now().isoformat(),
                "metadata": enrich_data,
                "tags": [
                    "youtube",
                    "second_brain",
                    "video_content"
                ] + enrich_data.get("doctrine_map", {}).get("principles", [])
            }

            # Add to catalog index
            self.catalog["entries"][entry_id] = {
                "id": entry_id,
                "type": entry["type"],
                "timestamp": entry["timestamp"],
                "summary": enrich_data.get("abstract_120w", "")[:100] + "...",
                "tags": entry["tags"]
            }
            self.catalog["last_updated"] = datetime.now().isoformat()

            # Append to entries file
            with open(self.entries_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry) + '\n')

            # Update knowledge graph
            self._update_graph(entry)

            # Save updated catalog
            self._save_catalog()

            Log.info(f"Added {entry_id} to NCL catalog")
            return True

        except Exception as e:
            Log.error(f"Failed to add entry to NCL catalog: {e}")
            return False

    def _update_graph(self, entry: Dict[str, Any]):
        """Update knowledge graph with new connections"""
        video_id = entry["metadata"]["video_id"]
        node_id = f"video_{video_id}"

        # Add node if not exists
        if not any(n["id"] == node_id for n in self.graph["nodes"]):
            self.graph["nodes"].append({
                "id": node_id,
                "type": "content",
                "label": f"YouTube: {video_id}",
                "properties": {
                    "content_type": "video_enrichment",
                    "confidence": entry["metadata"].get("confidence", "unknown"),
                    "timestamp": entry["timestamp"]
                }
            })

        # Create connections based on doctrine mapping
        doctrine_map = entry["metadata"].get("doctrine_map", {})
        principles = doctrine_map.get("principles", [])
        themes = doctrine_map.get("themes", [])

        # Connect to principles
        for principle in principles:
            principle_id = f"principle_{principle.lower().replace(' ', '_')}"
            if not any(n["id"] == principle_id for n in self.graph["nodes"]):
                self.graph["nodes"].append({
                    "id": principle_id,
                    "type": "principle",
                    "label": principle,
                    "properties": {"category": "resonance_energy"}
                })

            # Add edge
            edge = {
                "source": node_id,
                "target": principle_id,
                "type": "embodies_principle",
                "weight": 1.0,
                "timestamp": entry["timestamp"]
            }
            if not any(e["source"] ==edge["source"] and e["target"] ==
                       edge["target"] for e in self.graph["edges"]):
                self.graph["edges"].append(edge)

        # Connect to themes
        for theme in themes:
            theme_id = f"theme_{theme.lower().replace(' ', '_')}"
            if not any(n["id"] == theme_id for n in self.graph["nodes"]):
                self.graph["nodes"].append({
                    "id": theme_id,
                    "type": "theme",
                    "label": theme,
                    "properties": {"category": "doctrine"}
                })

            # Add edge
            edge = {
                "source": node_id,
                "target": theme_id,
                "type": "relates_to_theme",
                "weight": 0.8,
                "timestamp": entry["timestamp"]
            }
            if not any(e["source"] ==edge["source"] and e["target"] ==
                       edge["target"] for e in self.graph["edges"]):
                self.graph["edges"].append(edge)

        # Connect entities
        entities = entry["metadata"].get("entities", [])
        for entity in entities:
            entity_id = f"entity_{entity.lower().replace(' ', '_')}"
            if not any(n["id"] == entity_id for n in self.graph["nodes"]):
                self.graph["nodes"].append({
                    "id": entity_id,
                    "type": "entity",
                    "label": entity,
                    "properties": {"category": "named_entity"}
                })

            edge = {
                "source": node_id,
                "target": entity_id,
                "type": "mentions_entity",
                "weight": 0.6,
                "timestamp": entry["timestamp"]
            }
            if not any(e["source"] ==edge["source"] and e["target"] ==
                       edge["target"] for e in self.graph["edges"]):
                self.graph["edges"].append(edge)

    def _save_catalog(self):
        """Save catalog and graph to disk"""
        try:
            self.catalog_file.write_text(
                json.dumps(self.catalog, indent=2),
                encoding='utf-8'
            )
            self.graph_file.write_text(
                json.dumps(self.graph, indent=2),
                encoding='utf-8'
            )
        except Exception as e:
            Log.error(f"Failed to save NCL catalog: {e}")

def commit_enrichment(enrich_file: Path) -> bool:
    """Commit enrichment data to NCL catalog"""
    try:
        if not enrich_file.exists():
            Log.error(f"Enrichment file not found: {enrich_file}")
            return False

        enrich_data = json.loads(enrich_file.read_text(encoding='utf-8'))
        catalog = NCLCatalog()
        return catalog.add_entry(enrich_data)

    except Exception as e:
        Log.error(f"Failed to commit enrichment: {e}")
        return False

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="NCL Catalog Manager")
    parser.add_argument("enrich_file", help="Path to enrich.json file")
    args = parser.parse_args()

    if commit_enrichment(Path(args.enrich_file)):
        print("✓ Successfully committed to NCL catalog")
        sys.exit(0)
    else:
        print("✗ Failed to commit to NCL catalog")
        sys.exit(1)