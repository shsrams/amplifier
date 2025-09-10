# Knowledge System Workflow

## Overview
A clean, simple workflow for managing knowledge extraction from content files.

## Complete Workflow

### 1. Add New Content
- Place content files in directories configured in AMPLIFIER_CONTENT_DIRS
- Supported formats: .txt, .md, .json, .html files

### 2. Update Knowledge Base
Run the complete pipeline with one command:
```bash
make knowledge-update
```

This runs:
1. `content-scan` - Scans configured directories for content files
2. `knowledge-sync` - Extracts concepts, relationships, insights, patterns
3. `knowledge-synthesize` - Finds meta-patterns across all knowledge

### 3. Query Knowledge (for Claude Code)

Simple query from command line:
```bash
make knowledge-query Q="prompt engineering"
```

Or use the Python script directly:
```bash
python ai_working/knowledge_integration/query_knowledge.py "AI agents" --limit 10
```

## Individual Commands

If you want more control:

```bash
# Just scan content directories
make content-scan

# Just extract knowledge
make knowledge-sync

# Just synthesize patterns
make knowledge-synthesize

# Check statistics
make knowledge-stats
```

## File Locations

- Content files: Configured via AMPLIFIER_CONTENT_DIRS
- Extracted knowledge: `.data/knowledge/extractions.jsonl`
- Synthesis results: `.data/knowledge/synthesis.json`

## Philosophy

Following ruthless simplicity:
- One command for the full pipeline
- Direct access to individual steps when needed
- Clear file locations
- No unnecessary abstractions