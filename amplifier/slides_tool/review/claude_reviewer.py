"""
Claude Code native review system using Read tool for image analysis.

This module provides a review system that works directly with Claude Code's
Read tool capability rather than trying to use Claude Code SDK recursively.
"""

import json
import logging
from pathlib import Path

from .models import ReviewRequest
from .models import ReviewResult
from .models import SlideIssue

logger = logging.getLogger(__name__)


class ClaudeNativeReviewer:
    """Review system that works directly with Claude Code's Read tool."""

    def __init__(self, review_dir: Path | None = None):
        """
        Initialize the Claude native reviewer.

        Args:
            review_dir: Directory for review requests/responses (default: ./review_requests)
        """
        self.review_dir = review_dir or Path("review_requests")
        self.review_dir.mkdir(exist_ok=True)

    def create_review_request(
        self, slide_images: list[Path], request: ReviewRequest, request_id: str = "default"
    ) -> Path:
        """
        Create a review request file for Claude to process.

        Args:
            slide_images: List of paths to slide PNG files
            request: Review request configuration
            request_id: Unique ID for this review request

        Returns:
            Path to the review request file
        """
        # Create review request data
        review_data = {
            "request_id": request_id,
            "review_type": request.review_type,
            "focus_areas": request.focus_areas,
            "strict_mode": request.strict_mode,
            "slide_images": [str(img.absolute()) for img in slide_images],
            "instructions": self._get_review_instructions(request),
            "response_format": self._get_response_format(),
        }

        # Save request file
        request_file = self.review_dir / f"review_request_{request_id}.json"
        with open(request_file, "w") as f:
            json.dump(review_data, f, indent=2)

        logger.info(f"Created review request: {request_file}")
        return request_file

    def check_review_response(self, request_id: str = "default") -> ReviewResult | None:
        """
        Check if Claude has provided a review response.

        Args:
            request_id: The request ID to check

        Returns:
            ReviewResult if response exists, None otherwise
        """
        response_file = self.review_dir / f"review_response_{request_id}.json"

        if not response_file.exists():
            return None

        try:
            with open(response_file) as f:
                data = json.load(f)

            # Convert to ReviewResult
            issues = []
            for issue_data in data.get("issues", []):
                issues.append(SlideIssue(**issue_data))

            return ReviewResult(
                overall_score=data.get("overall_score", 5.0),
                issues=issues,
                strengths=data.get("strengths", []),
                general_feedback=data.get("general_feedback"),
                needs_revision=data.get("needs_revision", len(issues) > 0),
            )
        except Exception as e:
            logger.error(f"Error parsing review response: {e}")
            return None

    def _get_review_instructions(self, request: ReviewRequest) -> str:
        """Get review instructions for Claude."""
        focus = self._get_review_focus(request)

        return f"""Please analyze these presentation slides using the Read tool.

CRITICAL INSTRUCTIONS:
1. Use the Read tool to examine each PNG file listed in 'slide_images'
2. Look carefully for text truncation at ALL edges, especially the bottom
3. Check for overlapping elements, poor contrast, and formatting issues
4. Identify any content that appears cut off or incomplete

Review Type: {request.review_type}
Focus Areas: {focus}
Strict Mode: {request.strict_mode}

For each issue found, provide specific details including:
- Which slide it appears on (slide_index)
- The type of issue (content, formatting, visual, readability, consistency)
- Severity (critical, major, minor, suggestion)
- Detailed description of what's wrong
- Specific suggestion for how to fix it
- Location on the slide where the issue appears"""

    def _get_review_focus(self, request: ReviewRequest) -> str:
        """Get review focus areas as string."""
        if request.focus_areas:
            return ", ".join(request.focus_areas)

        # Default focus based on review type
        if request.review_type == "visual":
            return "visual design, formatting, readability, color contrast, text truncation"
        if request.review_type == "content":
            return "content structure, clarity, flow, completeness"
        # comprehensive
        return "all aspects: content, visual design, consistency, text truncation, professionalism"

    def _get_response_format(self) -> dict:
        """Get the expected response format."""
        return {
            "overall_score": "float 0-10 rating of presentation quality",
            "issues": [
                {
                    "slide_index": "int - which slide (0-based)",
                    "issue_type": "content|formatting|visual|readability|consistency",
                    "severity": "critical|major|minor|suggestion",
                    "description": "detailed description of the issue",
                    "suggestion": "specific fix recommendation",
                    "location": "where on slide (e.g., 'bottom edge', 'center', 'title area')",
                }
            ],
            "strengths": ["list of positive aspects"],
            "general_feedback": "overall assessment and recommendations",
            "needs_revision": "boolean - whether revision is needed",
        }

    def save_review_response(self, request_id: str, review_result: dict) -> Path:
        """
        Save a review response (for manual creation or testing).

        Args:
            request_id: The request ID
            review_result: The review result data

        Returns:
            Path to the saved response file
        """
        response_file = self.review_dir / f"review_response_{request_id}.json"
        with open(response_file, "w") as f:
            json.dump(review_result, f, indent=2)
        return response_file


class ClaudeReviewInterface:
    """
    Interface for Claude to easily review slides using the Read tool.

    This class provides helper methods that Claude can use to review slides
    and provide structured feedback.
    """

    @staticmethod
    def analyze_slide_for_truncation(image_path: str) -> dict:
        """
        Helper prompt for Claude to analyze a single slide.

        When Claude uses the Read tool on this image, they should check for:
        1. Text cut off at any edge (especially bottom)
        2. Elements that appear incomplete
        3. Content that extends beyond visible boundaries
        4. Overlapping or hidden elements

        Returns a structured analysis dict.
        """
        return {
            "prompt": f"Use Read tool on {image_path} and check for text truncation",
            "focus_areas": [
                "Bottom edge text cutoff",
                "Side edge truncation",
                "Overlapping elements",
                "Hidden content indicators",
            ],
        }

    @staticmethod
    def create_review_response_template() -> dict:
        """
        Template for Claude to fill in when reviewing slides.

        Claude should copy this template and fill in the actual findings.
        """
        return {
            "overall_score": 7.5,  # 0-10 scale
            "issues": [
                {
                    "slide_index": 0,
                    "issue_type": "visual",  # content|formatting|visual|readability|consistency
                    "severity": "critical",  # critical|major|minor|suggestion
                    "description": "Text is truncated at the bottom of the slide",
                    "suggestion": "Reduce content or adjust spacing to fit within boundaries",
                    "location": "bottom edge",
                }
            ],
            "strengths": ["Clear title hierarchy", "Consistent color scheme"],
            "general_feedback": "The presentation has good structure but needs layout adjustments to prevent text truncation.",
            "needs_revision": True,
        }
