"""
Review and auto-improvement system for presentations.

This module provides AI-powered review and iterative improvement capabilities
for generated presentations, using visual and content analysis to identify
and fix issues automatically.
"""

from .analyzer import SlideReviewAnalyzer
from .claude_reviewer import ClaudeNativeReviewer
from .claude_reviewer import ClaudeReviewInterface
from .models import AutoImproveRequest
from .models import AutoImproveResult
from .models import ReviewRequest
from .models import ReviewResult
from .models import RevisionIteration
from .models import SlideIssue
from .orchestrator import RevisionOrchestrator
from .simplified_analyzer import ManualReviewProcessor
from .simplified_analyzer import SimplifiedSlideAnalyzer
from .store import ReviewStore

__all__ = [
    # Analyzers
    "SlideReviewAnalyzer",
    "SimplifiedSlideAnalyzer",
    # Claude Integration
    "ClaudeNativeReviewer",
    "ClaudeReviewInterface",
    "ManualReviewProcessor",
    # Orchestrator
    "RevisionOrchestrator",
    # Store
    "ReviewStore",
    # Models
    "SlideIssue",
    "ReviewResult",
    "ReviewRequest",
    "RevisionIteration",
    "AutoImproveRequest",
    "AutoImproveResult",
]
