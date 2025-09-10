"""
Amplifier Slides Tool - AI-powered presentation generation.

This module provides tools for generating, revising, and exporting presentations
using natural language prompts and the Claude Code SDK.
"""

from .exporter import BatchExporter
from .exporter import PresentationExporter
from .generator import SlideGenerator
from .models import ExportRequest
from .models import ExportResult
from .models import GenerationRequest
from .models import GenerationResult
from .models import Presentation
from .models import RevisionRequest
from .models import Slide
from .review import AutoImproveRequest
from .review import AutoImproveResult
from .review import ReviewRequest
from .review import ReviewResult
from .review import ReviewStore
from .review import RevisionIteration
from .review import RevisionOrchestrator
from .review import SlideIssue
from .review import SlideReviewAnalyzer
from .state_manager import QuickSave
from .state_manager import StateManager
from .utils import clean_ai_response
from .utils import ensure_output_dir
from .utils import format_duration
from .utils import parse_slide_count

__all__ = [
    # Models
    "Slide",
    "Presentation",
    "GenerationRequest",
    "RevisionRequest",
    "ExportRequest",
    "GenerationResult",
    "ExportResult",
    # Core functionality
    "SlideGenerator",
    "PresentationExporter",
    "BatchExporter",
    "StateManager",
    "QuickSave",
    # Review system
    "SlideReviewAnalyzer",
    "RevisionOrchestrator",
    "ReviewStore",
    "SlideIssue",
    "ReviewResult",
    "ReviewRequest",
    "RevisionIteration",
    "AutoImproveRequest",
    "AutoImproveResult",
    # Utilities
    "format_duration",
    "ensure_output_dir",
    "parse_slide_count",
    "clean_ai_response",
]

__version__ = "1.0.0"
