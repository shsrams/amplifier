"""
Simplified slide review analyzer that works with Claude Code environment.

This analyzer creates review requests that Claude can process using the Read tool,
avoiding the complexity of trying to use Claude Code SDK recursively.
"""

import json
import logging
from pathlib import Path

from .claude_reviewer import ClaudeNativeReviewer
from .models import ReviewRequest
from .models import ReviewResult
from .models import SlideIssue

logger = logging.getLogger(__name__)


class SimplifiedSlideAnalyzer:
    """
    Simplified analyzer that works with Claude Code's Read tool.

    This analyzer exports slides as PNGs and creates review requests
    that Claude can process using the native Read tool.
    """

    def __init__(self, review_dir: Path | None = None):
        """
        Initialize the simplified analyzer.

        Args:
            review_dir: Directory for review requests/responses
        """
        self.reviewer = ClaudeNativeReviewer(review_dir)

    async def analyze(self, request: ReviewRequest) -> ReviewResult:
        """
        Analyze a presentation by creating a review request for Claude.

        Args:
            request: Review request with presentation file and options

        Returns:
            ReviewResult with issues found and feedback
        """
        presentation_path = Path(request.presentation_file)

        if not presentation_path.exists():
            raise FileNotFoundError(f"Presentation file not found: {presentation_path}")

        # Handle different input types
        slide_images = []

        if presentation_path.is_dir():
            # Directory with PNG files
            slide_images = sorted(presentation_path.glob("slide_*.png"))
            if not slide_images:
                raise ValueError(f"No slide PNG files found in: {presentation_path}")

        elif presentation_path.suffix in [".png", ".jpg", ".jpeg"]:
            # Single image file
            slide_images = [presentation_path]

        elif presentation_path.suffix == ".html":
            # HTML file - need to export to PNG first
            logger.info("HTML review requires PNG export first")
            return self._create_export_needed_result()

        else:
            raise ValueError(f"Unsupported file type: {presentation_path.suffix}")

        # Create review request
        request_id = f"review_{presentation_path.stem}"
        request_file = self.reviewer.create_review_request(
            slide_images=slide_images, request=request, request_id=request_id
        )

        # Check for existing response (in case Claude already reviewed)
        existing_result = self.reviewer.check_review_response(request_id)
        if existing_result:
            logger.info("Found existing review response")
            return existing_result

        # Return a pending result with instructions for Claude
        return self._create_pending_result(request_file, slide_images)

    def _create_pending_result(self, request_file: Path, slide_images: list[Path]) -> ReviewResult:
        """Create a result indicating review is pending Claude's analysis."""

        # Create instructions for Claude
        instructions = f"""
REVIEW NEEDED: Please analyze the presentation slides.

1. Review request created at: {request_file}
2. Slide images to analyze:
{chr(10).join(f"   - {img}" for img in slide_images[:5])}
{f"   ... and {len(slide_images) - 5} more" if len(slide_images) > 5 else ""}

TO COMPLETE REVIEW:
1. Use the Read tool on each slide image
2. Look for text truncation, especially at bottom edges
3. Check for formatting and visual issues
4. Create a review response file with your findings

The review system is waiting for your analysis.
"""

        return ReviewResult(
            overall_score=0.0,  # Pending score
            issues=[
                SlideIssue(
                    slide_index=0,
                    issue_type="content",
                    severity="suggestion",
                    description="Review pending - awaiting Claude's image analysis",
                    suggestion=instructions,
                    location=None,
                )
            ],
            strengths=["Review request created successfully"],
            general_feedback="Review request created. Waiting for Claude to analyze slide images using Read tool.",
            needs_revision=False,  # Don't trigger revision until review is complete
        )

    def _create_export_needed_result(self) -> ReviewResult:
        """Create a result indicating PNG export is needed first."""
        return ReviewResult(
            overall_score=0.0,
            issues=[
                SlideIssue(
                    slide_index=0,
                    issue_type="content",
                    severity="suggestion",
                    description="HTML presentations must be exported to PNG for visual review",
                    suggestion="Export the presentation to PNG format first, then run review on the PNG files",
                    location=None,
                )
            ],
            strengths=[],
            general_feedback="Please export HTML to PNG format for visual review analysis.",
            needs_revision=False,
        )


class ManualReviewProcessor:
    """
    Helper class for manually processing Claude's review feedback.

    This can be used when Claude provides review feedback through
    conversation rather than through the review file system.
    """

    @staticmethod
    def parse_claude_feedback(feedback_text: str) -> ReviewResult:
        """
        Parse Claude's textual feedback into a ReviewResult.

        Args:
            feedback_text: Claude's review feedback as text

        Returns:
            ReviewResult parsed from the feedback
        """
        # Try to parse as JSON first
        try:
            # Remove markdown formatting if present
            cleaned = feedback_text.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            elif cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]

            data = json.loads(cleaned.strip())

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

        except (json.JSONDecodeError, KeyError):
            # Fall back to text parsing
            return ManualReviewProcessor._parse_text_feedback(feedback_text)

    @staticmethod
    def _parse_text_feedback(feedback_text: str) -> ReviewResult:
        """Parse unstructured text feedback."""
        lines = feedback_text.lower()

        # Simple heuristics to detect issues
        has_truncation = "truncat" in lines or "cut off" in lines
        has_overlap = "overlap" in lines
        has_formatting = "format" in lines or "spacing" in lines

        issues = []
        if has_truncation:
            issues.append(
                SlideIssue(
                    slide_index=0,
                    issue_type="visual",
                    severity="critical",
                    description="Text truncation detected",
                    suggestion="Adjust content to fit within slide boundaries",
                    location="edges",
                )
            )

        if has_overlap:
            issues.append(
                SlideIssue(
                    slide_index=0,
                    issue_type="formatting",
                    severity="major",
                    description="Overlapping elements detected",
                    suggestion="Adjust element positioning",
                    location="various",
                )
            )

        if has_formatting:
            issues.append(
                SlideIssue(
                    slide_index=0,
                    issue_type="formatting",
                    severity="minor",
                    description="Formatting issues detected",
                    suggestion="Review spacing and formatting",
                    location="various",
                )
            )

        score = 5.0 if issues else 8.0

        return ReviewResult(
            overall_score=score,
            issues=issues,
            strengths=["Feedback parsed from text"],
            general_feedback=feedback_text[:200],  # First 200 chars
            needs_revision=len(issues) > 0,
        )
