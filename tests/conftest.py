"""
Pytest configuration and shared fixtures for slides tool tests.

This file provides common fixtures and configuration for all tests,
following the modular design philosophy.
"""

import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest

from amplifier.slides_tool.models import GenerationRequest
from amplifier.slides_tool.models import Presentation
from amplifier.slides_tool.models import Slide


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create temporary directory for test operations."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_slide() -> Slide:
    """Create sample slide for testing."""
    return Slide(
        title="Test Slide",
        content="This is test content\n\n- Point 1\n- Point 2",
        notes="Speaker notes for test",
        transition="slide",
        background=None,
        layout="content",
    )


@pytest.fixture
def sample_presentation(sample_slide: Slide) -> Presentation:
    """Create sample presentation for testing."""
    return Presentation(
        title="Test Presentation",
        subtitle="A test presentation",
        author="Test Author",
        theme="black",
        slides=[sample_slide],
        version=1,
    )


@pytest.fixture
def sample_generation_request() -> GenerationRequest:
    """Create sample generation request for testing."""
    return GenerationRequest(
        prompt="Create a presentation about testing",
        context="This is additional context",
        context_file=None,
        num_slides=5,
        style="professional",
        include_images=False,
    )


@pytest.fixture
def sample_markdown() -> str:
    """Sample presentation markdown for testing."""
    return """# Test Presentation

---

## Slide 1
Introduction slide

???
Speaker notes for slide 1

---

## Slide 2
Main content

- Point 1
- Point 2
- Point 3

???
Speaker notes for slide 2

---

## Slide 3
Conclusion

Thank you for your attention!

???
Final notes
"""


@pytest.fixture
def sample_html() -> str:
    """Sample presentation HTML for testing."""
    return """<!DOCTYPE html>
<html>
<head>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/reveal.js@4.3.1/dist/reveal.css">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/reveal.js@4.3.1/dist/theme/black.css">
</head>
<body>
    <div class="reveal">
        <div class="slides">
            <section data-markdown data-separator="^---$" data-separator-vertical="^--$" data-separator-notes="^???">
                <textarea data-template>
# Test Presentation

---

## Slide 1
Test content
                </textarea>
            </section>
        </div>
    </div>
    <script src="https://cdn.jsdelivr.net/npm/reveal.js@4.3.1/dist/reveal.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/reveal.js@4.3.1/plugin/markdown/markdown.js"></script>
    <script>
        Reveal.initialize({
            hash: true,
            plugins: [ RevealMarkdown ]
        });
    </script>
</body>
</html>"""


@pytest.fixture
def mock_claude_sdk_unavailable(monkeypatch):
    """Mock Claude SDK as unavailable for fallback testing."""

    def mock_check_claude_cli():
        return False

    monkeypatch.setattr("amplifier.slides_tool.generator.SlideGenerator._check_claude_cli", mock_check_claude_cli)


@pytest.fixture
def mock_export_tools_unavailable(monkeypatch):
    """Mock export tools as unavailable for fallback testing."""

    def mock_check_playwright():
        return False

    def mock_check_puppeteer():
        return False

    def mock_check_imagemagick():
        return False

    monkeypatch.setattr("amplifier.slides_tool.exporter.PresentationExporter._check_playwright", mock_check_playwright)
    monkeypatch.setattr("amplifier.slides_tool.exporter.PresentationExporter._check_puppeteer", mock_check_puppeteer)
    monkeypatch.setattr(
        "amplifier.slides_tool.exporter.PresentationExporter._check_imagemagick", mock_check_imagemagick
    )


@pytest.fixture
def mock_file_io_error(monkeypatch):
    """Mock file I/O errors for retry logic testing."""
    import errno

    call_count = 0

    def mock_open_with_error(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count <= 2:  # Fail first two attempts
            error = OSError("Mocked I/O error")
            error.errno = errno.EIO  # errno 5 - I/O error
            raise error
        # Succeed on third attempt
        return open(*args, **kwargs)

    monkeypatch.setattr("builtins.open", mock_open_with_error)
    return lambda: call_count


# Test data constants
LARGE_PRESENTATION_SLIDES = 50
TIMEOUT_TEST_DURATION = 5  # seconds for timeout testing (shorter than real 120s)

# Test categories for parametrization
EXPORT_FORMATS = ["html", "pdf", "png", "gif"]
PRESENTATION_STYLES = ["professional", "academic", "creative", "minimal"]
REVEAL_THEMES = ["black", "white", "league", "beige", "sky", "night", "serif", "simple", "solarized"]
