"""
Simple knowledge store for querying extracted knowledge.
"""

import json
from pathlib import Path
from typing import Any

from amplifier.config.paths import paths


class KnowledgeStore:
    """Simple store for searching extracted knowledge"""

    def __init__(self, data_dir: Path | None = None):
        """Initialize the knowledge store"""
        if data_dir is None:
            data_dir = paths.data_dir / "knowledge"
        self.data_dir = data_dir

        # Load all knowledge
        self.concepts = []
        self.relationships = []
        self.insights = []
        self.patterns = []

        self._load_knowledge()

    def _load_knowledge(self):
        """Load knowledge from extractions.jsonl"""
        extractions_file = self.data_dir / "extractions.jsonl"

        if not extractions_file.exists():
            print(f"Warning: No extractions found at {extractions_file}")
            return

        with open(extractions_file) as f:
            for line in f:
                if line.strip():
                    try:
                        data = json.loads(line)

                        # Add source info to each item
                        source_info = {
                            "source_id": data.get("source_id", ""),
                            "title": data.get("title", ""),
                            "url": data.get("url", ""),
                            "author": data.get("author", ""),
                        }

                        # Store concepts
                        for concept in data.get("concepts", []):
                            concept.update(source_info)
                            self.concepts.append(concept)

                        # Store relationships
                        for rel in data.get("relationships", []):
                            rel.update(source_info)
                            self.relationships.append(rel)

                        # Store insights
                        for insight in data.get("insights", []):
                            if isinstance(insight, str):
                                insight = {"description": insight}
                            insight.update(source_info)
                            self.insights.append(insight)

                        # Store patterns
                        for pattern in data.get("patterns", []):
                            pattern.update(source_info)
                            self.patterns.append(pattern)

                    except json.JSONDecodeError:
                        print(f"Warning: Could not parse line: {line[:100]}...")

    def search(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Search across all knowledge"""
        query_lower = query.lower()
        results = []

        # Search concepts
        for concept in self.concepts:
            if query_lower in concept.get("name", "").lower() or query_lower in concept.get("description", "").lower():
                concept["_type"] = "concept"
                results.append(concept)

        # Search relationships
        for rel in self.relationships:
            if (
                query_lower in rel.get("subject", "").lower()
                or query_lower in rel.get("predicate", "").lower()
                or query_lower in rel.get("object", "").lower()
            ):
                rel["_type"] = "relationship"
                results.append(rel)

        # Search insights
        for insight in self.insights:
            desc = insight.get("description", "")
            if isinstance(desc, str) and query_lower in desc.lower():
                insight["_type"] = "insight"
                results.append(insight)

        # Search patterns
        for pattern in self.patterns:
            if query_lower in pattern.get("name", "").lower() or query_lower in pattern.get("description", "").lower():
                pattern["_type"] = "pattern"
                results.append(pattern)

        # Sort by importance/confidence if available
        results.sort(key=lambda x: x.get("importance", x.get("confidence", 0)), reverse=True)

        return results[:limit]

    def get_stats(self) -> dict[str, int]:
        """Get statistics about the knowledge base"""
        return {
            "concepts": len(self.concepts),
            "relationships": len(self.relationships),
            "insights": len(self.insights),
            "patterns": len(self.patterns),
            "total": len(self.concepts) + len(self.relationships) + len(self.insights) + len(self.patterns),
        }
