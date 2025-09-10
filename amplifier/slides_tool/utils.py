"""
Shared utilities for the slides tool.

This module provides common utilities with retry logic for file I/O,
following patterns from DISCOVERIES.md.
"""

import asyncio
import json
import logging
import time
from collections.abc import Callable
from pathlib import Path
from typing import TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


def retry_file_operation(
    func: Callable[..., T], max_retries: int = 3, initial_delay: float = 0.5, backoff_factor: float = 2.0
) -> T:
    """
    Retry file operations with exponential backoff.

    Based on DISCOVERIES.md - handles cloud sync issues.
    """
    delay = initial_delay
    last_error = None

    for attempt in range(max_retries):
        try:
            return func()
        except OSError as e:
            last_error = e
            if e.errno == 5 and attempt < max_retries - 1:  # I/O error, likely cloud sync
                if attempt == 0:
                    logger.warning(
                        "File I/O error - retrying. "
                        "This may be due to cloud-synced files (OneDrive, Dropbox, etc.). "
                        "Consider enabling 'Always keep on this device' for the data folder."
                    )
                time.sleep(delay)
                delay *= backoff_factor
            else:
                raise

    if last_error:
        raise last_error
    raise RuntimeError("Retry failed without error")


def write_json(data: dict, filepath: Path, ensure_parents: bool = True) -> None:
    """Write JSON to file with retry logic."""
    if ensure_parents:
        filepath.parent.mkdir(parents=True, exist_ok=True)

    def _write():
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.flush()

    retry_file_operation(_write)


def read_json(filepath: Path) -> dict:
    """Read JSON from file with retry logic."""

    def _read():
        with open(filepath, encoding="utf-8") as f:
            return json.load(f)

    return retry_file_operation(_read)


def write_text(content: str, filepath: Path, ensure_parents: bool = True) -> None:
    """Write text to file with retry logic."""
    if ensure_parents:
        filepath.parent.mkdir(parents=True, exist_ok=True)

    def _write():
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
            f.flush()

    retry_file_operation(_write)


def read_text(filepath: Path) -> str:
    """Read text from file with retry logic."""

    def _read():
        with open(filepath, encoding="utf-8") as f:
            return f.read()

    return retry_file_operation(_read)


def append_text(content: str, filepath: Path, ensure_parents: bool = True) -> None:
    """Append text to file with retry logic."""
    if ensure_parents:
        filepath.parent.mkdir(parents=True, exist_ok=True)

    def _append():
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(content)
            f.flush()

    retry_file_operation(_append)


def clean_ai_response(response: str) -> str:
    """
    Clean AI response by removing markdown code blocks.

    Based on DISCOVERIES.md - strips markdown formatting.
    """
    cleaned = response.strip()

    # Remove markdown code block formatting
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```markdown"):
        cleaned = cleaned[11:]
    elif cleaned.startswith("```md"):
        cleaned = cleaned[5:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]

    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]

    return cleaned.strip()


def parse_slide_count(prompt: str) -> int | None:
    """Extract slide count from natural language prompt."""
    import re

    # Common patterns for slide count
    patterns = [
        r"(\d+)\s*slides?",
        r"create\s*(\d+)",
        r"generate\s*(\d+)",
        r"make\s*(\d+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, prompt.lower())
        if match:
            return int(match.group(1))

    return None


def ensure_output_dir(base_dir: Path, prefix: str = "presentation") -> Path:
    """Create a timestamped output directory."""
    from datetime import datetime

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = base_dir / f"{prefix}_{timestamp}"
    output_dir.mkdir(parents=True, exist_ok=True)

    return output_dir


async def with_timeout(coro, timeout_seconds: int = 120, timeout_message: str | None = None):
    """
    Execute async operation with timeout.

    Based on DISCOVERIES.md - 120 second timeout for Claude SDK.
    """
    try:
        return await asyncio.wait_for(coro, timeout=timeout_seconds)
    except TimeoutError:
        message = timeout_message or f"Operation timed out after {timeout_seconds} seconds"
        logger.error(message)
        raise TimeoutError(message)


def format_duration(seconds: float) -> str:
    """Format duration in seconds to human-readable string."""
    if seconds < 1:
        return f"{seconds * 1000:.0f}ms"
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes = int(seconds // 60)
    remaining_seconds = seconds % 60
    return f"{minutes}m {remaining_seconds:.0f}s"
