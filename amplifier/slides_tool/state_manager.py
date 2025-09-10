"""
State management for presentations with versioning support.

This module handles persistence and versioning of presentations,
implementing incremental saves as required by DISCOVERIES.md.
"""

import shutil
from datetime import datetime
from pathlib import Path

from .models import Presentation
from .utils import read_json
from .utils import read_text
from .utils import write_json
from .utils import write_text


class StateManager:
    """Manages presentation state with versioning."""

    def __init__(self, base_dir: Path):
        """Initialize state manager with base directory."""
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.current_dir = self.base_dir / "current"
        self.versions_dir = self.base_dir / "versions"
        self.current_dir.mkdir(exist_ok=True)
        self.versions_dir.mkdir(exist_ok=True)

    def save_presentation(
        self, presentation: Presentation, markdown: str, html: str, auto_version: bool = True
    ) -> Path:
        """
        Save presentation with incremental versioning.

        Args:
            presentation: Presentation object to save
            markdown: Markdown representation
            html: HTML representation
            auto_version: Whether to create a version automatically

        Returns:
            Path to saved presentation directory
        """
        # Save current version
        current_path = self.current_dir / "presentation.json"
        # Use mode='json' to properly serialize datetime
        write_json(presentation.model_dump(mode="json"), current_path)

        # Save markdown and HTML
        write_text(markdown, self.current_dir / "presentation.md")
        write_text(html, self.current_dir / "presentation.html")

        # Create versioned copy if requested
        if auto_version:
            version_dir = self._create_version_dir(presentation.version)
            write_json(presentation.model_dump(mode="json"), version_dir / "presentation.json")
            write_text(markdown, version_dir / "presentation.md")
            write_text(html, version_dir / "presentation.html")

            # Update version metadata
            self._update_version_metadata(version_dir, presentation)

        return self.current_dir

    def load_presentation(self, version: int | None = None) -> tuple[Presentation, str, str]:
        """
        Load presentation from storage.

        Args:
            version: Specific version to load, or None for current

        Returns:
            Tuple of (presentation, markdown, html)
        """
        if version is None:
            load_dir = self.current_dir
        else:
            load_dir = self._get_version_dir(version)
            if not load_dir.exists():
                raise FileNotFoundError(f"Version {version} not found")

        presentation_data = read_json(load_dir / "presentation.json")
        presentation = Presentation(**presentation_data)

        markdown = read_text(load_dir / "presentation.md")
        html = read_text(load_dir / "presentation.html")

        return presentation, markdown, html

    def save_checkpoint(self, data: dict, checkpoint_name: str) -> Path:
        """
        Save intermediate checkpoint (for crash recovery).

        Implements incremental saves from DISCOVERIES.md.
        """
        checkpoint_dir = self.base_dir / "checkpoints"
        checkpoint_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        checkpoint_file = checkpoint_dir / f"{checkpoint_name}_{timestamp}.json"

        write_json(data, checkpoint_file)

        # Keep only last 10 checkpoints
        self._cleanup_old_checkpoints(checkpoint_dir, keep=10)

        return checkpoint_file

    def load_latest_checkpoint(self, checkpoint_name: str) -> dict | None:
        """Load the most recent checkpoint if available."""
        checkpoint_dir = self.base_dir / "checkpoints"
        if not checkpoint_dir.exists():
            return None

        # Find matching checkpoints
        checkpoints = sorted(
            checkpoint_dir.glob(f"{checkpoint_name}_*.json"), key=lambda p: p.stat().st_mtime, reverse=True
        )

        if checkpoints:
            return read_json(checkpoints[0])

        return None

    def list_versions(self) -> list[dict]:
        """List all available versions with metadata."""
        versions = []

        for version_dir in sorted(self.versions_dir.iterdir()):
            if version_dir.is_dir():
                metadata_file = version_dir / "metadata.json"
                if metadata_file.exists():
                    metadata = read_json(metadata_file)
                    versions.append(metadata)

        return versions

    def export_version(self, version: int, export_path: Path) -> None:
        """Export a specific version to another location."""
        version_dir = self._get_version_dir(version)
        if not version_dir.exists():
            raise FileNotFoundError(f"Version {version} not found")

        export_path.parent.mkdir(parents=True, exist_ok=True)

        # Copy all files from version directory
        if export_path.is_dir():
            shutil.copytree(version_dir, export_path, dirs_exist_ok=True)
        else:
            # If export_path is a file, copy the presentation file
            shutil.copy2(version_dir / "presentation.html", export_path)

    def cleanup_old_versions(self, keep_last: int = 10) -> None:
        """Remove old versions, keeping the most recent ones."""
        version_dirs = sorted(
            [d for d in self.versions_dir.iterdir() if d.is_dir()], key=lambda d: d.stat().st_mtime, reverse=True
        )

        for old_dir in version_dirs[keep_last:]:
            shutil.rmtree(old_dir)

    def _create_version_dir(self, version: int) -> Path:
        """Create a directory for a specific version."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        version_dir = self.versions_dir / f"v{version}_{timestamp}"
        version_dir.mkdir(parents=True, exist_ok=True)
        return version_dir

    def _get_version_dir(self, version: int) -> Path:
        """Get the directory for a specific version."""
        # Find the directory that starts with the version number
        for version_dir in self.versions_dir.iterdir():
            if version_dir.name.startswith(f"v{version}_"):
                return version_dir

        raise FileNotFoundError(f"Version {version} not found")

    def _update_version_metadata(self, version_dir: Path, presentation: Presentation) -> None:
        """Update metadata for a version."""
        metadata = {
            "version": presentation.version,
            "title": presentation.title,
            "created": datetime.now().isoformat(),
            "slide_count": len(presentation.slides),
            "author": presentation.author,
            "theme": presentation.theme,
        }

        write_json(metadata, version_dir / "metadata.json")

    def _cleanup_old_checkpoints(self, checkpoint_dir: Path, keep: int = 10) -> None:
        """Remove old checkpoint files."""
        checkpoints = sorted(checkpoint_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)

        for old_checkpoint in checkpoints[keep:]:
            old_checkpoint.unlink()


class QuickSave:
    """Context manager for automatic checkpoint saves."""

    def __init__(self, state_manager: StateManager, name: str):
        """Initialize quick save context."""
        self.state_manager = state_manager
        self.name = name
        self.data = {}

    def update(self, **kwargs) -> None:
        """Update checkpoint data."""
        self.data.update(kwargs)
        self.state_manager.save_checkpoint(self.data, self.name)

    def __enter__(self):
        """Enter context."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context and save final state."""
        if exc_type is None:
            # Save successful completion
            self.data["completed"] = True
            self.state_manager.save_checkpoint(self.data, f"{self.name}_final")
        else:
            # Save error state
            self.data["error"] = str(exc_val)
            self.state_manager.save_checkpoint(self.data, f"{self.name}_error")
