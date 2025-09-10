"""
Knowledge Synthesis Module

Simple, direct knowledge extraction from text using Claude Code SDK.
Extracts concepts, relationships, insights, and patterns in a single pass.
"""

from .extractor import KnowledgeSynthesizer
from .store import KnowledgeStore

__all__ = ["KnowledgeSynthesizer", "KnowledgeStore"]
