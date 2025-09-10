"""
Slide review analyzer using Claude Code SDK for visual analysis.

This module provides the SlideReviewAnalyzer class that analyzes presentation
slides (HTML or images) and identifies issues for improvement.
"""

import asyncio
import base64
import json
import logging
import subprocess
from pathlib import Path

from .models import ReviewRequest
from .models import ReviewResult
from .models import SlideIssue

logger = logging.getLogger(__name__)


class SlideReviewAnalyzer:
    """Analyzes presentation slides for quality issues using Claude SDK."""

    def __init__(self):
        """Initialize the analyzer and check for Claude CLI availability."""
        self.sdk_available = self._check_claude_cli()

    def _check_claude_cli(self) -> bool:
        """Check if Claude CLI is available."""
        try:
            result = subprocess.run(["which", "claude"], capture_output=True, text=True, timeout=2)
            if result.returncode == 0:
                logger.info("Claude CLI found for review analysis")
                return True
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        logger.warning("Claude CLI not found - review features will use fallback")
        return False

    async def analyze(self, request: ReviewRequest) -> ReviewResult:
        """
        Analyze a presentation and return review results.

        Args:
            request: Review request with presentation file and options

        Returns:
            ReviewResult with issues found and feedback
        """
        presentation_path = Path(request.presentation_file)

        if not presentation_path.exists():
            raise FileNotFoundError(f"Presentation file not found: {presentation_path}")

        # Check if it's a directory with slide PNGs
        if presentation_path.is_dir():
            # Look for slide_XXX.png files
            slide_files = list(presentation_path.glob("slide_*.png"))
            if slide_files:
                return await self._analyze_images(presentation_path, request)
            raise ValueError(f"No slide PNG files found in directory: {presentation_path}")

        # Determine file type and analyze accordingly
        if presentation_path.suffix in [".png", ".jpg", ".jpeg"]:
            return await self._analyze_images(presentation_path, request)
        if presentation_path.suffix == ".html":
            return await self._analyze_html(presentation_path, request)
        raise ValueError(f"Unsupported file type: {presentation_path.suffix}")

    async def _analyze_images(self, image_path: Path, request: ReviewRequest) -> ReviewResult:
        """Analyze PNG/JPEG images of slides using Claude SDK vision capabilities."""
        if not self.sdk_available:
            return self._fallback_review(request)

        try:
            # Use Claude SDK for image analysis with proper timeout
            from claude_code_sdk import ClaudeCodeOptions
            from claude_code_sdk import ClaudeSDKClient

            # Check if this is a directory with multiple slide PNGs
            slide_images = []
            if image_path.is_dir():
                # Find all slide_XXX.png files
                slide_files = sorted(image_path.glob("slide_*.png"))
                if not slide_files:
                    raise FileNotFoundError(f"No slide PNG files found in {image_path}")

                # Encode all slide images (limit to first 5 for now to avoid token limits)
                for slide_file in slide_files[:5]:
                    with open(slide_file, "rb") as f:
                        encoded = base64.b64encode(f.read()).decode("utf-8")
                        slide_images.append({"file": slide_file.name, "data": encoded})
                logger.info(f"Analyzing {len(slide_images)} slide images (of {len(slide_files)} total)")
            else:
                # Single image file
                with open(image_path, "rb") as f:
                    image_data = base64.b64encode(f.read()).decode("utf-8")
                slide_images = [{"file": image_path.name, "data": image_data}]

            # Build analysis prompt based on review type
            # For multiple images, we'll analyze them all together
            if len(slide_images) == 1:
                prompt = self._build_image_analysis_prompt(request, slide_images[0]["data"])
            else:
                prompt = self._build_multi_image_analysis_prompt(request, slide_images)

            # Use 120-second timeout as per DISCOVERIES.md
            response = ""
            async with asyncio.timeout(120):
                async with ClaudeSDKClient(
                    options=ClaudeCodeOptions(
                        system_prompt=self._get_review_system_prompt(),
                        max_turns=1,
                    )
                ) as client:
                    await client.query(prompt)

                    async for message in client.receive_response():
                        if hasattr(message, "content"):
                            content = getattr(message, "content", [])
                            if isinstance(content, list):
                                for block in content:
                                    if hasattr(block, "text"):
                                        response += getattr(block, "text", "")

            # Parse response and create ReviewResult
            return self._parse_review_response(response)

        except TimeoutError:
            logger.warning("Claude SDK timeout during image analysis - using fallback")
            return self._fallback_review(request)
        except Exception as e:
            logger.error(f"Error in image analysis: {e}")
            return self._fallback_review(request)

    async def _analyze_html(self, html_path: Path, request: ReviewRequest) -> ReviewResult:
        """Analyze HTML presentation by extracting content and structure."""
        if not self.sdk_available:
            return self._fallback_review(request)

        try:
            # Read HTML content
            html_content = html_path.read_text()

            # Extract slide content from HTML
            slides_content = self._extract_slides_from_html(html_content)

            # Build analysis prompt
            prompt = self._build_content_analysis_prompt(request, slides_content)

            # Use Claude SDK for content analysis with proper timeout
            from claude_code_sdk import ClaudeCodeOptions
            from claude_code_sdk import ClaudeSDKClient

            response = ""
            async with asyncio.timeout(120):
                async with ClaudeSDKClient(
                    options=ClaudeCodeOptions(
                        system_prompt=self._get_review_system_prompt(),
                        max_turns=1,
                    )
                ) as client:
                    await client.query(prompt)

                    async for message in client.receive_response():
                        if hasattr(message, "content"):
                            content = getattr(message, "content", [])
                            if isinstance(content, list):
                                for block in content:
                                    if hasattr(block, "text"):
                                        response += getattr(block, "text", "")

            return self._parse_review_response(response)

        except TimeoutError:
            logger.warning("Claude SDK timeout during HTML analysis - using fallback")
            return self._fallback_review(request)
        except Exception as e:
            logger.error(f"Error in HTML analysis: {e}")
            return self._fallback_review(request)

    def _get_review_system_prompt(self) -> str:
        """Get the system prompt for presentation review."""
        return """You are an expert presentation designer and reviewer. Your task is to analyze
presentations and identify issues that affect their quality, readability, and effectiveness.

Focus on:
1. Content clarity and structure
2. Visual design and formatting
3. Text readability and hierarchy
4. Consistency across slides
5. Professional appearance

Provide your analysis as JSON with specific, actionable feedback."""

    def _build_image_analysis_prompt(self, request: ReviewRequest, image_data: str) -> str:
        """Build prompt for image-based slide analysis."""
        review_focus = self._get_review_focus(request)

        # Properly format the image for Claude SDK vision capability
        # The prompt should include the image as a data URL
        return f"""Analyze this presentation slide image and identify any issues, especially:
1. Text truncation or cut-off content at edges
2. Content that doesn't fit within slide boundaries
3. Overlapping or hidden elements
4. Text that appears incomplete or cut off

Review Type: {request.review_type}
Focus Areas: {review_focus}
Strict Mode: {request.strict_mode}

<image>data:image/png;base64,{image_data}</image>

CRITICAL: Look carefully at ALL edges of the slide, especially the bottom edge, for any text that appears cut off or truncated. Even partial text visibility indicates truncation.

Please analyze the slide(s) and return a JSON response with this EXACT structure:
{{
    "overall_score": <float 0-10>,
    "issues": [
        {{
            "slide_index": <int>,
            "issue_type": <"content"|"formatting"|"visual"|"readability"|"consistency">,
            "severity": <"critical"|"major"|"minor"|"suggestion">,
            "description": "<detailed description>",
            "suggestion": "<how to fix>",
            "location": "<specific location>"
        }}
    ],
    "strengths": ["<positive aspect 1>", "<positive aspect 2>"],
    "general_feedback": "<overall feedback>",
    "needs_revision": <true|false>
}}

Return ONLY the JSON, no markdown formatting or explanation."""

    def _build_content_analysis_prompt(self, request: ReviewRequest, slides_content: list[dict]) -> str:
        """Build prompt for content-based slide analysis."""
        review_focus = self._get_review_focus(request)

        slides_text = json.dumps(slides_content, indent=2)

        return f"""Analyze this presentation content and identify any issues.

Review Type: {request.review_type}
Focus Areas: {review_focus}
Strict Mode: {request.strict_mode}

Presentation Content:
{slides_text}

Please analyze the slides and return a JSON response with this EXACT structure:
{{
    "overall_score": <float 0-10>,
    "issues": [
        {{
            "slide_index": <int>,
            "issue_type": <"content"|"formatting"|"visual"|"readability"|"consistency">,
            "severity": <"critical"|"major"|"minor"|"suggestion">,
            "description": "<detailed description>",
            "suggestion": "<how to fix>",
            "location": "<specific location>"
        }}
    ],
    "strengths": ["<positive aspect 1>", "<positive aspect 2>"],
    "general_feedback": "<overall feedback>",
    "needs_revision": <true|false>
}}

Return ONLY the JSON, no markdown formatting or explanation."""

    def _get_review_focus(self, request: ReviewRequest) -> str:
        """Get review focus areas as string."""
        if request.focus_areas:
            return ", ".join(request.focus_areas)

        # Default focus based on review type
        if request.review_type == "visual":
            return "visual design, formatting, readability, color contrast"
        if request.review_type == "content":
            return "content structure, clarity, flow, completeness"
        # comprehensive
        return "all aspects: content, visual design, consistency, professionalism"

    def _extract_slides_from_html(self, html_content: str) -> list[dict]:
        """Extract slide content from HTML."""
        slides = []

        # Simple extraction - look for reveal.js sections
        import re

        # Find all sections (slides)
        section_pattern = r"<section[^>]*>(.*?)</section>"
        sections = re.findall(section_pattern, html_content, re.DOTALL)

        for idx, section in enumerate(sections):
            # Extract title (h1, h2, h3)
            title_match = re.search(r"<h[1-3][^>]*>(.*?)</h[1-3]>", section)
            title = title_match.group(1) if title_match else f"Slide {idx + 1}"

            # Extract content (remove HTML tags for simplicity)
            content = re.sub(r"<[^>]+>", " ", section)
            content = " ".join(content.split())  # Clean whitespace

            slides.append(
                {
                    "index": idx,
                    "title": title,
                    "content": content[:500],  # Limit content length
                }
            )

        return slides

    def _build_multi_image_analysis_prompt(self, request: ReviewRequest, slide_images: list[dict]) -> str:
        """Build prompt for analyzing multiple slide images."""
        review_focus = self._get_review_focus(request)

        # Build prompt with all images
        prompt = f"""Analyze these presentation slides and identify any issues, especially:
1. Text truncation or cut-off content at edges
2. Content that doesn't fit within slide boundaries
3. Overlapping or hidden elements
4. Text that appears incomplete or cut off

Review Type: {request.review_type}
Focus Areas: {review_focus}
Strict Mode: {request.strict_mode}

Slides to analyze:
"""

        for i, slide in enumerate(slide_images):
            prompt += f"\n\nSlide {i + 1} ({slide['file']}):"
            prompt += f"\n<image>data:image/png;base64,{slide['data']}</image>"

        prompt += """\n\nCRITICAL: Look carefully at ALL edges of EACH slide, especially the bottom edges, for any text that appears cut off or truncated. Even partial text visibility indicates truncation.

Please analyze ALL slides and return a JSON response with this EXACT structure:
{
    "overall_score": <float 0-10>,
    "issues": [
        {
            "slide_index": <int>,
            "issue_type": <"content"|"formatting"|"visual"|"readability"|"consistency">,
            "severity": <"critical"|"major"|"minor"|"suggestion">,
            "description": "<detailed description>",
            "suggestion": "<how to fix>",
            "location": "<specific location>"
        }
    ],
    "strengths": ["<positive aspect 1>", "<positive aspect 2>"],
    "general_feedback": "<overall feedback>",
    "needs_revision": <true|false>
}

Return ONLY the JSON, no markdown formatting or explanation."""

        return prompt

    def _parse_review_response(self, response: str) -> ReviewResult:
        """Parse Claude's response into ReviewResult."""
        try:
            # Strip markdown code block formatting if present (from DISCOVERIES.md)
            cleaned_response = response.strip()
            if cleaned_response.startswith("```json"):
                cleaned_response = cleaned_response[7:]
            elif cleaned_response.startswith("```"):
                cleaned_response = cleaned_response[3:]

            if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-3]

            cleaned_response = cleaned_response.strip()

            # Parse JSON
            data = json.loads(cleaned_response)

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

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.error(f"Failed to parse review response: {e}")
            return self._fallback_review(
                ReviewRequest(presentation_file="", review_type="comprehensive", focus_areas=None, strict_mode=False)
            )

    def _fallback_review(self, request: ReviewRequest) -> ReviewResult:
        """Provide a fallback review when Claude SDK is not available."""
        logger.info("Using fallback review (Claude SDK not available)")

        return ReviewResult(
            overall_score=7.0,
            issues=[
                SlideIssue(
                    slide_index=0,
                    issue_type="content",  # Changed from "suggestion" to valid type
                    severity="minor",
                    description="Review system running in fallback mode",
                    suggestion="Install Claude CLI for full review capabilities",
                    location=None,
                )
            ],
            strengths=["Presentation successfully generated"],
            general_feedback="Automated review unavailable - manual review recommended",
            needs_revision=False,
        )
