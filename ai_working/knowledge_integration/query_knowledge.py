#!/usr/bin/env python3
"""
Simple knowledge query interface for Claude Code to search the knowledge base.

Usage:
    python query_knowledge.py "your query"
    python query_knowledge.py "your query" --limit 10
    python query_knowledge.py "your query" --format json
"""

import argparse
import json
from typing import Any

from ai_working.knowledge_integration.knowledge_store import KnowledgeStore


def format_result(result: dict[str, Any], format_type: str = "text") -> str:
    """Format a single result for display"""
    if format_type == "json":
        return json.dumps(result, indent=2)

    # Text format
    output = []

    # Handle different types of results
    if "name" in result:
        output.append(f"📌 {result['name']}")
        if "description" in result:
            output.append(f"   {result['description']}")
        if "importance" in result:
            output.append(f"   Importance: {result['importance']:.1%}")
    elif "description" in result:
        output.append(f"• {result['description']}")
    elif "subject" in result and "predicate" in result and "object" in result:
        # Relationship
        output.append(f"🔗 {result['subject']} {result['predicate']} {result['object']}")
        if "confidence" in result:
            output.append(f"   Confidence: {result['confidence']:.1%}")
    else:
        # Generic fallback
        output.append(f"• {str(result)[:200]}...")

    if "source_id" in result:
        output.append(f"   Source: {result['source_id'][:50]}...")

    return "\n".join(output)


def main():
    parser = argparse.ArgumentParser(description="Query the knowledge base")
    parser.add_argument("query", help="Search query")
    parser.add_argument("--limit", type=int, default=5, help="Number of results (default: 5)")
    parser.add_argument("--format", choices=["text", "json"], default="text", help="Output format (default: text)")

    args = parser.parse_args()

    # Initialize store
    store = KnowledgeStore()

    # Search
    print(f"🔍 Searching for: {args.query}\n")
    results = store.search(args.query, limit=args.limit)

    if not results:
        print("No results found.")
        return

    print(f"Found {len(results)} results:\n")
    print("=" * 60)

    for i, result in enumerate(results, 1):
        print(f"\n[{i}] {format_result(result, args.format)}")
        if i < len(results):
            print("-" * 40)

    print("\n" + "=" * 60)
    print("\n💡 Use --limit N to see more results")
    print(
        f"📊 Total knowledge items: {len(store.concepts)} concepts, "
        f"{len(store.relationships)} relationships, "
        f"{len(store.insights)} insights, "
        f"{len(store.patterns)} patterns"
    )


if __name__ == "__main__":
    main()
