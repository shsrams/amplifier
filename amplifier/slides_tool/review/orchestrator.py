"""
Revision orchestrator that coordinates review and improvement cycles.

This module provides the RevisionOrchestrator class that manages the
auto-improvement process by coordinating between the analyzer, generator,
and exporter components using dependency injection.
"""

import logging
import time
from pathlib import Path
from typing import TYPE_CHECKING

from ..state_manager import StateManager
from ..utils import ensure_output_dir
from .analyzer import SlideReviewAnalyzer
from .models import AutoImproveRequest
from .models import AutoImproveResult
from .models import ReviewRequest
from .models import RevisionIteration

if TYPE_CHECKING:
    from ..exporter import PresentationExporter
    from ..generator import SlideGenerator

logger = logging.getLogger(__name__)


class RevisionOrchestrator:
    """Orchestrates the revision and improvement process for presentations."""

    def __init__(
        self,
        generator: "SlideGenerator",
        exporter: "PresentationExporter",
        analyzer: SlideReviewAnalyzer | None = None,
    ):
        """
        Initialize the orchestrator with dependencies.

        Args:
            generator: SlideGenerator instance for revisions
            exporter: PresentationExporter for exporting presentations
            analyzer: Optional SlideReviewAnalyzer (creates one if not provided)
        """
        self.generator = generator
        self.exporter = exporter
        self.analyzer = analyzer or SlideReviewAnalyzer()
        self.batch_exporter = None

    async def auto_improve(self, request: AutoImproveRequest) -> AutoImproveResult:
        """
        Automatically improve a presentation through iterative review and revision.

        Args:
            request: Auto-improvement request with settings

        Returns:
            AutoImproveResult with iteration history and final results
        """
        start_time = time.time()
        iterations = []
        current_file = Path(request.presentation_file)

        if not current_file.exists():
            return AutoImproveResult(
                success=False,
                iterations=[],
                final_score=None,
                final_presentation_file=None,
                total_time=time.time() - start_time,
                stopped_reason="error",
                error=f"Presentation file not found: {current_file}",
            )

        # Set up output directory if specified
        output_dir = None
        state_manager = None
        if request.output_dir:
            output_dir = ensure_output_dir(Path(request.output_dir))
            state_manager = StateManager(output_dir)

        # Initialize batch exporter if needed
        if self.exporter and request.export_formats:
            from ..exporter import BatchExporter

            self.batch_exporter = BatchExporter(self.exporter)

        try:
            previous_score = None

            for iteration_num in range(1, request.max_iterations + 1):
                logger.info(f"Starting improvement iteration {iteration_num}")

                # Analyze current presentation
                review_request = ReviewRequest(
                    presentation_file=str(current_file),
                    review_type=request.review_type,
                    focus_areas=None,
                    strict_mode=(iteration_num > 1),  # Be stricter after first iteration
                )

                review_result = await self.analyzer.analyze(review_request)

                # Check if we've reached target score
                if review_result.overall_score >= request.target_score:
                    logger.info(f"Target score {request.target_score} reached: {review_result.overall_score}")
                    iterations.append(
                        RevisionIteration(
                            iteration=iteration_num,
                            review_result=review_result,
                            revision_applied=False,
                            presentation_file=str(current_file),
                            improvement_delta=0,
                        )
                    )
                    return AutoImproveResult(
                        success=True,
                        iterations=iterations,
                        final_score=review_result.overall_score,
                        final_presentation_file=str(current_file),
                        total_time=time.time() - start_time,
                        stopped_reason="target_reached",
                        error=None,
                    )

                # Check if there's no improvement
                if previous_score and review_result.overall_score <= previous_score:
                    logger.warning(f"No improvement detected (score: {review_result.overall_score})")
                    iterations.append(
                        RevisionIteration(
                            iteration=iteration_num,
                            review_result=review_result,
                            revision_applied=False,
                            presentation_file=str(current_file),
                            improvement_delta=0,
                        )
                    )
                    return AutoImproveResult(
                        success=True,
                        iterations=iterations,
                        final_score=review_result.overall_score,
                        final_presentation_file=str(current_file),
                        total_time=time.time() - start_time,
                        stopped_reason="no_improvement",
                        error=None,
                    )

                # Apply revision if needed
                if review_result.needs_revision and review_result.issues:
                    feedback = review_result.to_feedback_text()
                    logger.info(f"Applying revision based on {len(review_result.issues)} issues")

                    # Load current presentation
                    if current_file.suffix == ".md":
                        current_markdown = current_file.read_text()
                    elif current_file.suffix == ".html":
                        # For HTML, we need to extract or regenerate markdown
                        # This is a simplified approach - ideally we'd extract from HTML
                        current_markdown = current_file.read_text()
                    else:
                        raise ValueError(f"Unsupported file type: {current_file.suffix}")

                    # Apply revision using generator
                    revised_presentation, revised_markdown = await self.generator.revise(
                        current_markdown=current_markdown,
                        feedback=feedback,
                        preserve_structure=True,
                    )

                    # Save revised presentation
                    if state_manager:
                        # Generate HTML
                        from ..generator import markdown_to_html

                        html = markdown_to_html(revised_markdown, revised_presentation.theme)

                        # Save with state manager
                        save_path = state_manager.save_presentation(revised_presentation, revised_markdown, html)

                        # Export to requested formats
                        if self.batch_exporter and request.export_formats:
                            html_file = save_path / "presentation.html"
                            # Convert to list[str] for type compatibility
                            export_formats: list[str] = [str(fmt) for fmt in request.export_formats]
                            await self.batch_exporter.export_all(html_file, export_formats, save_path)

                        # Update current file for next iteration
                        if "png" in request.export_formats:
                            # For PNG exports, point to the directory containing slide PNGs
                            current_file = save_path
                        else:
                            current_file = save_path / "presentation.html"
                    else:
                        # Save in place (update original)
                        current_file.write_text(revised_markdown)

                    improvement_delta = (
                        review_result.overall_score - previous_score if previous_score else review_result.overall_score
                    )

                    iterations.append(
                        RevisionIteration(
                            iteration=iteration_num,
                            review_result=review_result,
                            revision_applied=True,
                            presentation_file=str(current_file),
                            improvement_delta=improvement_delta,
                        )
                    )

                    previous_score = review_result.overall_score
                else:
                    # No revision needed
                    iterations.append(
                        RevisionIteration(
                            iteration=iteration_num,
                            review_result=review_result,
                            revision_applied=False,
                            presentation_file=str(current_file),
                            improvement_delta=0,
                        )
                    )
                    break

            # Reached max iterations
            return AutoImproveResult(
                success=True,
                iterations=iterations,
                final_score=iterations[-1].review_result.overall_score if iterations else None,
                final_presentation_file=str(current_file),
                total_time=time.time() - start_time,
                stopped_reason="max_iterations",
                error=None,
            )

        except Exception as e:
            logger.error(f"Error during auto-improvement: {e}")
            return AutoImproveResult(
                success=False,
                iterations=iterations,
                final_score=iterations[-1].review_result.overall_score if iterations else None,
                final_presentation_file=str(current_file) if current_file else None,
                total_time=time.time() - start_time,
                stopped_reason="error",
                error=str(e),
            )

    async def single_review_and_revise(
        self, presentation_file: str, output_dir: str | None = None
    ) -> tuple[AutoImproveResult, str | None]:
        """
        Perform a single review and revision cycle.

        Args:
            presentation_file: Path to presentation to review
            output_dir: Optional output directory for revised version

        Returns:
            Tuple of (AutoImproveResult, path to revised file or None)
        """
        request = AutoImproveRequest(
            presentation_file=presentation_file,
            max_iterations=1,
            target_score=10.0,  # Won't be reached in one iteration
            review_type="comprehensive",
            output_dir=output_dir,
        )

        result = await self.auto_improve(request)

        if result.success and result.iterations:
            return result, result.final_presentation_file

        return result, None
