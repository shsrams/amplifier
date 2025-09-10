"""
Command-line interface for knowledge synthesis.
Simple, direct commands for extracting knowledge from content files.
"""

import asyncio
import json
import logging
from typing import Any

import click

from amplifier.config.paths import paths
from amplifier.knowledge_integration import UnifiedKnowledgeExtractor

from .events import EventEmitter
from .store import KnowledgeStore

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


@click.group()
def cli():
    """Knowledge synthesis from content files."""
    pass


@cli.command()
@click.option(
    "--max-items",
    default=None,
    type=int,
    help="Maximum number of content items to process (default: all)",
)
def sync(max_items: int | None):
    """
    Sync and extract knowledge from content files.

    Scans all configured content directories for content files and extracts
    concepts, relationships, insights, and patterns.
    """
    asyncio.run(_sync_content(max_items))


async def _sync_content(max_items: int | None):
    """Sync and extract knowledge from content files."""
    # Import the new content loader
    from amplifier.content_loader import ContentLoader

    # Initialize components
    synthesizer = UnifiedKnowledgeExtractor()
    store = KnowledgeStore()
    emitter = EventEmitter()
    loader = ContentLoader()

    # Load all content items
    content_items = list(loader.load_all())

    if not content_items:
        logger.info("No content files found in configured directories.")
        logger.info("Check AMPLIFIER_CONTENT_DIRS environment variable.")
        emitter.emit("sync_finished", stage="init", data={"processed": 0, "skipped": 0, "reason": "no_content"})
        return

    logger.info(f"Found {len(content_items)} content files")

    # Process content items
    processed = 0
    skipped = 0
    emitter.emit("sync_started", stage="sync", data={"total": len(content_items), "max": max_items})

    for item in content_items:
        # Check max items limit
        if max_items and processed >= max_items:
            break

        # Skip if already processed
        if store.is_processed(item.content_id):
            logger.info(f"✓ Already processed: {item.title}")
            skipped += 1
            emitter.emit(
                "content_skipped",
                stage="precheck",
                source_id=item.content_id,
                data={"title": item.title, "reason": "already_processed"},
            )
            continue

        # Extract knowledge
        logger.info(f"\nProcessing: {item.title}")
        logger.debug(f"  From: {item.source_path}")
        emitter.emit(
            "extraction_started",
            stage="extract",
            source_id=item.content_id,
            data={"title": item.title},
        )
        try:
            # Create a task for extraction with progress indicator
            extraction_task = asyncio.create_task(
                synthesizer.extract_from_text(
                    text=item.content,
                    title=item.title,
                    source=item.content_id,
                )
            )

            # Show progress while extraction is running
            dots = 0
            while not extraction_task.done():
                await asyncio.sleep(3)  # Check every 3 seconds
                if not extraction_task.done():
                    dots = (dots + 1) % 4
                    progress_msg = "  Extracting" + "." * (dots + 1) + " " * (3 - dots)
                    print(f"\r{progress_msg}", end="", flush=True)

            # Clear the progress line
            print("\r" + " " * 40 + "\r", end="", flush=True)

            # Get the result
            extraction_result = await extraction_task

            # Convert UnifiedExtraction to dict format expected by store
            extraction = {
                "source_id": item.content_id,
                "title": item.title,
                "concepts": extraction_result.concepts,  # Already a list of dicts
                "relationships": [
                    {"subject": r.subject, "predicate": r.predicate, "object": r.object, "confidence": r.confidence}
                    for r in extraction_result.relationships
                ],
                "insights": extraction_result.key_insights,  # Use key_insights field
                "patterns": extraction_result.code_patterns,  # Use code_patterns field
            }

            # Add metadata from ContentItem
            from pathlib import Path

            extraction["url"] = item.metadata.get("url", "")
            extraction["author"] = item.metadata.get("author", "")
            extraction["publication"] = item.metadata.get("publication", "")
            extraction["content_dir"] = str(Path(item.source_path).parent)  # Track source directory

            # Save extraction
            store.save(extraction)

            # Report results
            logger.info(
                f"  → Extracted: {len(extraction.get('concepts', []))} concepts, "
                f"{len(extraction.get('relationships', []))} relationships, "
                f"{len(extraction.get('insights', []))} insights"
            )
            processed += 1
            emitter.emit(
                "extraction_succeeded",
                stage="extract",
                source_id=item.content_id,
                data={
                    "title": item.title,
                    "concepts": len(extraction.get("concepts", [])),
                    "relationships": len(extraction.get("relationships", [])),
                    "insights": len(extraction.get("insights", [])),
                },
            )

        except KeyboardInterrupt:
            logger.info("\n⚠ Interrupted - saving progress...")
            break
        except Exception as e:
            logger.error(f"\n{'=' * 60}")
            logger.error(f"FATAL: Extraction failed for {item.content_id}")
            logger.error(f"Error: {e}")
            logger.error(f"{'=' * 60}")
            emitter.emit(
                "extraction_failed",
                stage="extract",
                source_id=item.content_id,
                data={"title": item.title, "error": str(e)},
            )
            raise  # Stop immediately on extraction failure

    # Summary
    logger.info(f"\n{'=' * 50}")
    logger.info(f"Processed: {processed} items")
    logger.info(f"Skipped (already done): {skipped}")
    logger.info(f"Total extractions: {store.count()}")
    emitter.emit(
        "sync_finished",
        stage="sync",
        data={"processed": processed, "skipped": skipped, "total": len(content_items)},
    )


@cli.command()
@click.option("--n", "n", default=50, type=int, help="Number of events to show")
@click.option("--event", "event_filter", default=None, type=str, help="Filter by event type")
@click.option("--follow/--no-follow", default=False, help="Follow events (like tail -f)")
def events(n: int, event_filter: str | None, follow: bool) -> None:
    """Show or follow pipeline events."""
    path = paths.data_dir / "knowledge" / "events.jsonl"
    emitter = EventEmitter(path)

    import time as _time

    if not path.exists():
        logger.info(f"No events found at {path}")
        return

    def _print_once() -> None:
        rows = emitter.tail(n=n, event_filter=event_filter)
        if not rows:
            logger.info("No matching events")
            return
        for ev in rows:
            ts = _time.strftime("%Y-%m-%d %H:%M:%S", _time.localtime(ev.timestamp))
            src = f" [{ev.source_id}]" if ev.source_id else ""
            details = ""
            if ev.data:
                # Compact one-line detail
                try:
                    details = " " + json.dumps(ev.data, ensure_ascii=False)
                except Exception:
                    details = ""
            print(f"{ts} - {ev.event}{src}{details}")

    _print_once()
    if follow:
        # Simple follow: print new lines as they arrive
        last_size = path.stat().st_size
        try:
            while True:
                _time.sleep(1)
                new_size = path.stat().st_size
                if new_size > last_size:
                    # Read newly appended lines
                    with open(path, encoding="utf-8") as f:
                        f.seek(last_size)
                        for line in f:
                            try:
                                obj = json.loads(line)
                            except json.JSONDecodeError:
                                continue
                            if event_filter and obj.get("event") != event_filter:
                                continue
                            ts = _time.strftime("%Y-%m-%d %H:%M:%S", _time.localtime(float(obj.get("timestamp", 0.0))))
                            src = f" [{obj.get('source_id')}]" if obj.get("source_id") else ""
                            data = obj.get("data")
                            details = ""
                            if data is not None:
                                try:
                                    details = " " + json.dumps(data, ensure_ascii=False)
                                except Exception:
                                    details = ""
                            print(f"{ts} - {obj.get('event')}{src}{details}")
                    last_size = new_size
        except KeyboardInterrupt:
            return


@cli.command("events-summary")
@click.option(
    "--scope",
    type=click.Choice(["last", "all"], case_sensitive=False),
    default="last",
    help="Summarize last run (default) or all events",
)
def events_summary(scope: str) -> None:
    """Summarize pipeline events."""
    path = paths.data_dir / "knowledge" / "events.jsonl"
    if not path.exists():
        logger.info(f"No events found at {path}")
        return

    # Load events
    rows: list[dict[str, Any]] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    if not rows:
        logger.info("No events to summarize")
        return

    # Determine window
    start_idx = 0
    end_idx = len(rows) - 1
    if scope.lower() == "last":
        # Find last sync_finished, then back to the preceding sync_started
        last_finish = None
        for i in range(len(rows) - 1, -1, -1):
            if rows[i].get("event") == "sync_finished":
                last_finish = i
                break
        if last_finish is None:
            # No completed runs; take from last sync_started if any
            for i in range(len(rows) - 1, -1, -1):
                if rows[i].get("event") == "sync_started":
                    start_idx = i
                    break
            end_idx = len(rows) - 1
        else:
            end_idx = last_finish
            start_idx = 0
            for i in range(last_finish, -1, -1):
                if rows[i].get("event") == "sync_started":
                    start_idx = i
                    break

    window = rows[start_idx : end_idx + 1]
    if not window:
        logger.info("No events in selected window")
        return

    # Aggregate
    from collections import Counter

    by_type: Counter[str] = Counter(ev.get("event", "") for ev in window)
    skipped_reasons: Counter[str] = Counter(
        (ev.get("data", {}) or {}).get("reason", "") for ev in window if ev.get("event") == "content_skipped"
    )
    success = by_type.get("extraction_succeeded", 0)
    failures = by_type.get("extraction_failed", 0)
    started = by_type.get("extraction_started", 0)

    # Duration
    started_ts = next((ev.get("timestamp") for ev in window if ev.get("event") == "sync_started"), None)
    finished_ts = next((ev.get("timestamp") for ev in reversed(window) if ev.get("event") == "sync_finished"), None)
    duration_s = (float(finished_ts) - float(started_ts)) if started_ts and finished_ts else None

    # Processed/skipped totals from summary if present
    processed = None
    skipped = None
    total = None
    for ev in reversed(window):
        if ev.get("event") == "sync_finished":
            data = ev.get("data", {}) or {}
            processed = data.get("processed")
            skipped = data.get("skipped")
            total = data.get("total")
            break

    # Print
    print("\n=== Event Summary ===")
    print(f"Scope: {'last run' if scope.lower() == 'last' else 'all events'}")
    if duration_s is not None:
        print(f"Duration: {duration_s:.1f}s")
    if processed is not None:
        print(f"Processed: {processed}  Skipped: {skipped}  Total: {total}")
    print(f"Starts: {started}  Success: {success}  Failures: {failures}")
    rate = (success / started * 100.0) if started else 0.0
    print(f"Success rate: {rate:.1f}%")

    print("\nBy Event Type:")
    for k, v in by_type.most_common():
        print(f"  {k}: {v}")

    top_skip = [(k, c) for k, c in skipped_reasons.items() if k]
    if top_skip:
        print("\nTop Skipped Reasons:")
        for k, v in sorted(top_skip, key=lambda x: x[1], reverse=True)[:5]:
            print(f"  {k}: {v}")


@cli.command()
@click.argument("query", required=True)
def search(query: str):
    """
    Search extracted knowledge.

    Search through concepts, relationships, and insights.
    """
    store = KnowledgeStore()
    extractions = store.load_all()

    if not extractions:
        logger.info("No extractions found. Run 'sync' command first.")
        return

    # Simple text search across all fields
    query_lower = query.lower()
    matches = []

    for extraction in extractions:
        # Search in concepts
        for concept in extraction.get("concepts", []):
            if query_lower in concept.get("name", "").lower() or query_lower in concept.get("description", "").lower():
                matches.append(
                    {
                        "type": "concept",
                        "name": concept.get("name"),
                        "description": concept.get("description"),
                        "source": extraction.get("title", "Unknown"),
                    }
                )

        # Search in relationships
        for rel in extraction.get("relationships", []):
            if (
                query_lower in rel.get("subject", "").lower()
                or query_lower in rel.get("predicate", "").lower()
                or query_lower in rel.get("object", "").lower()
            ):
                matches.append(
                    {
                        "type": "relationship",
                        "triple": f"{rel.get('subject')} --{rel.get('predicate')}--> {rel.get('object')}",
                        "source": extraction.get("title", "Unknown"),
                    }
                )

        # Search in insights
        for insight in extraction.get("insights", []):
            if query_lower in insight.lower():
                matches.append({"type": "insight", "text": insight, "source": extraction.get("title", "Unknown")})

    # Display results
    if not matches:
        logger.info(f"No matches found for '{query}'")
        return

    logger.info(f"\nFound {len(matches)} matches for '{query}':\n")
    for match in matches[:20]:  # Limit to first 20
        if match["type"] == "concept":
            logger.info(f"📌 Concept: {match['name']}")
            logger.info(f"   {match['description'][:100]}...")
            logger.info(f"   Source: {match['source']}\n")
        elif match["type"] == "relationship":
            logger.info(f"🔗 Relationship: {match['triple']}")
            logger.info(f"   Source: {match['source']}\n")
        elif match["type"] == "insight":
            logger.info(f"💡 Insight: {match['text'][:100]}...")
            logger.info(f"   Source: {match['source']}\n")

    if len(matches) > 20:
        logger.info(f"... and {len(matches) - 20} more matches")


@cli.command()
def stats():
    """Show statistics about extracted knowledge."""
    store = KnowledgeStore()
    extractions = store.load_all()

    if not extractions:
        logger.info("No extractions found. Run 'sync' command first.")
        return

    # Calculate statistics
    total_concepts = sum(len(e.get("concepts", [])) for e in extractions)
    total_relationships = sum(len(e.get("relationships", [])) for e in extractions)
    total_insights = sum(len(e.get("insights", [])) for e in extractions)
    total_patterns = sum(len(e.get("patterns", [])) for e in extractions)

    # Display stats
    logger.info("\n" + "=" * 50)
    logger.info("Knowledge Base Statistics")
    logger.info("=" * 50)
    logger.info(f"Items processed: {len(extractions)}")
    logger.info(f"Total concepts: {total_concepts}")
    logger.info(f"Total relationships: {total_relationships}")
    logger.info(f"Total insights: {total_insights}")
    logger.info(f"Total patterns: {total_patterns}")
    logger.info("-" * 50)
    logger.info(f"Avg concepts/item: {total_concepts / len(extractions):.1f}")
    logger.info(f"Avg relationships/item: {total_relationships / len(extractions):.1f}")
    logger.info(f"Avg insights/item: {total_insights / len(extractions):.1f}")


@cli.command()
@click.option("--format", type=click.Choice(["json", "text"]), default="text", help="Output format")
def export(format: str):
    """Export all extracted knowledge."""
    store = KnowledgeStore()
    extractions = store.load_all()

    if not extractions:
        logger.info("No extractions found. Run 'sync' command first.")
        return

    if format == "json":
        # Export as JSON
        output = {"extractions": extractions, "total": len(extractions)}
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        # Export as readable text
        for extraction in extractions:
            print(f"\n{'=' * 60}")
            print(f"Title: {extraction.get('title', 'Unknown')}")
            print(f"Source: {extraction.get('source_id', 'Unknown')}")
            print(f"URL: {extraction.get('url', 'N/A')}")
            print(f"{'=' * 60}")

            if concepts := extraction.get("concepts"):
                print(f"\nConcepts ({len(concepts)}):")
                for concept in concepts[:10]:
                    print(f"  • {concept.get('name')}: {concept.get('description', '')[:80]}...")

            if relationships := extraction.get("relationships"):
                print(f"\nRelationships ({len(relationships)}):")
                for rel in relationships[:10]:
                    print(f"  • {rel.get('subject')} --{rel.get('predicate')}--> {rel.get('object')}")

            if insights := extraction.get("insights"):
                print(f"\nInsights ({len(insights)}):")
                for insight in insights[:5]:
                    print(f"  • {insight[:100]}...")


@cli.command()
def synthesize():
    """
    Run cross-article synthesis to find patterns and tensions.

    Analyzes all extracted knowledge to find:
    - Entity resolutions (same concept, different names)
    - Contradictions and tensions between articles
    - Emergent insights from pattern analysis
    - Concepts evolving over time
    """
    # Lazy import to avoid circular dependencies
    from .synthesis_engine import SynthesisEngine

    extractions_path = paths.data_dir / "knowledge" / "extractions.jsonl"

    if not extractions_path.exists():
        logger.info("No extractions found. Run 'sync' command first.")
        return

    # Run synthesis
    engine = SynthesisEngine(extractions_path)
    results = engine.run_synthesis()

    # Print summary
    engine.print_summary(results)

    logger.info(f"\nFull results saved to: {engine.synthesis_path}")


if __name__ == "__main__":
    cli()
