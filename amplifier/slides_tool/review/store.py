"""
Review history storage for tracking presentation improvement over time.

This module provides the ReviewStore class for persisting review results
and tracking the improvement history of presentations.
"""

import json
import logging
from datetime import datetime
from pathlib import Path

from .models import AutoImproveResult
from .models import ReviewResult
from .models import RevisionIteration
from .models import SlideIssue

logger = logging.getLogger(__name__)


class ReviewStore:
    """Manages storage and retrieval of review history."""

    def __init__(self, storage_dir: Path | str):
        """
        Initialize the review store.

        Args:
            storage_dir: Directory to store review history
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.history_file = self.storage_dir / "review_history.json"

    def save_review(self, presentation_id: str, review_result: ReviewResult) -> None:
        """
        Save a review result to history.

        Args:
            presentation_id: Unique identifier for the presentation
            review_result: Review result to save
        """
        history = self._load_history()

        if presentation_id not in history:
            history[presentation_id] = []

        # Convert to dict for JSON serialization
        review_data = {
            "timestamp": review_result.timestamp.isoformat(),
            "overall_score": review_result.overall_score,
            "issues": [self._issue_to_dict(issue) for issue in review_result.issues],
            "strengths": review_result.strengths,
            "general_feedback": review_result.general_feedback,
            "needs_revision": review_result.needs_revision,
        }

        history[presentation_id].append(review_data)
        self._save_history(history)

        logger.info(f"Saved review for {presentation_id} with score {review_result.overall_score}")

    def save_improvement_session(self, presentation_id: str, result: AutoImproveResult) -> None:
        """
        Save an entire auto-improvement session.

        Args:
            presentation_id: Unique identifier for the presentation
            result: Auto-improvement result with all iterations
        """
        session_dir = self.storage_dir / presentation_id / f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        session_dir.mkdir(parents=True, exist_ok=True)

        # Save session summary
        summary = {
            "success": result.success,
            "iterations_count": len(result.iterations),
            "final_score": result.final_score,
            "total_time": result.total_time,
            "stopped_reason": result.stopped_reason,
            "error": result.error,
        }

        with open(session_dir / "summary.json", "w") as f:
            json.dump(summary, f, indent=2)

        # Save each iteration
        for iteration in result.iterations:
            self._save_iteration(session_dir, iteration)

        logger.info(f"Saved improvement session for {presentation_id} with {len(result.iterations)} iterations")

    def get_review_history(self, presentation_id: str) -> list[dict]:
        """
        Get review history for a presentation.

        Args:
            presentation_id: Unique identifier for the presentation

        Returns:
            List of review results as dictionaries
        """
        history = self._load_history()
        return history.get(presentation_id, [])

    def get_latest_review(self, presentation_id: str) -> ReviewResult | None:
        """
        Get the most recent review for a presentation.

        Args:
            presentation_id: Unique identifier for the presentation

        Returns:
            Latest ReviewResult or None if no reviews exist
        """
        history = self.get_review_history(presentation_id)
        if not history:
            return None

        latest = history[-1]
        return self._dict_to_review_result(latest)

    def get_improvement_trend(self, presentation_id: str) -> list[float]:
        """
        Get the score trend over time for a presentation.

        Args:
            presentation_id: Unique identifier for the presentation

        Returns:
            List of scores in chronological order
        """
        history = self.get_review_history(presentation_id)
        return [review["overall_score"] for review in history]

    def _save_iteration(self, session_dir: Path, iteration: RevisionIteration) -> None:
        """Save a single iteration to disk."""
        iteration_file = session_dir / f"iteration_{iteration.iteration}.json"

        data = {
            "iteration": iteration.iteration,
            "review_result": {
                "overall_score": iteration.review_result.overall_score,
                "issues": [self._issue_to_dict(issue) for issue in iteration.review_result.issues],
                "strengths": iteration.review_result.strengths,
                "general_feedback": iteration.review_result.general_feedback,
                "needs_revision": iteration.review_result.needs_revision,
            },
            "revision_applied": iteration.revision_applied,
            "presentation_file": iteration.presentation_file,
            "improvement_delta": iteration.improvement_delta,
            "timestamp": iteration.timestamp.isoformat(),
        }

        with open(iteration_file, "w") as f:
            json.dump(data, f, indent=2)

    def _issue_to_dict(self, issue: SlideIssue) -> dict:
        """Convert SlideIssue to dictionary."""
        return {
            "slide_index": issue.slide_index,
            "issue_type": issue.issue_type,
            "severity": issue.severity,
            "description": issue.description,
            "suggestion": issue.suggestion,
            "location": issue.location,
        }

    def _dict_to_review_result(self, data: dict) -> ReviewResult:
        """Convert dictionary to ReviewResult."""
        issues = []
        for issue_data in data.get("issues", []):
            issues.append(SlideIssue(**issue_data))

        return ReviewResult(
            overall_score=data["overall_score"],
            issues=issues,
            strengths=data.get("strengths", []),
            general_feedback=data.get("general_feedback"),
            needs_revision=data.get("needs_revision", False),
            timestamp=datetime.fromisoformat(data["timestamp"]) if "timestamp" in data else datetime.now(),
        )

    def _load_history(self) -> dict:
        """Load review history from disk."""
        if not self.history_file.exists():
            return {}

        try:
            with open(self.history_file) as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            logger.error(f"Error loading review history: {e}")
            return {}

    def _save_history(self, history: dict) -> None:
        """Save review history to disk."""
        try:
            with open(self.history_file, "w") as f:
                json.dump(history, f, indent=2)
        except OSError as e:
            logger.error(f"Error saving review history: {e}")

    def clear_history(self, presentation_id: str | None = None) -> None:
        """
        Clear review history.

        Args:
            presentation_id: If provided, clear only for this presentation.
                           If None, clear all history.
        """
        if presentation_id:
            history = self._load_history()
            if presentation_id in history:
                del history[presentation_id]
                self._save_history(history)
                logger.info(f"Cleared review history for {presentation_id}")
        else:
            self.history_file.unlink(missing_ok=True)
            logger.info("Cleared all review history")
