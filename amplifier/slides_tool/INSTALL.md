# Amplifier Slides Tool - Installation Guide

## Overview

The Amplifier Slides Tool generates presentations from natural language using AI, with export capabilities to multiple formats (HTML, PDF, PNG, GIF).

## Dependencies Status

✅ **Core dependencies already configured** - All Python packages are in `pyproject.toml`
✅ **Claude Code SDK** - Already installed (`claude-code-sdk>=0.0.20`)
✅ **Click CLI framework** - Added to dependencies
✅ **Playwright** - Available in dev dependencies and slides-exports group

## Required External Tools

### 1. Claude CLI (Required for AI Generation)

The Claude CLI must be globally installed for AI-powered slide generation:

```bash
# Install globally via npm
npm install -g @anthropic-ai/claude-code

# Verify installation
which claude
claude --help
```

**Critical**: The CLI must be globally accessible, not locally installed. The Python SDK uses subprocess to call the CLI.

### 2. Playwright Browser (Required for PDF/PNG Export)

Install browser binaries for export functionality:

```bash
# Install Playwright browsers (requires sudo for system dependencies)
uv run --group slides-exports playwright install chromium --with-deps

# Or without system dependencies (may have issues)
uv run --group slides-exports playwright install chromium
```

**Note**: If you can't install browsers due to sudo restrictions, PDF and PNG exports will fall back to print-ready HTML.

### 3. Optional Tools

**ImageMagick** (for GIF export):
```bash
# Ubuntu/Debian
sudo apt-get install imagemagick

# macOS
brew install imagemagick

# Check installation
convert --version
```

**Puppeteer** (alternative to Playwright):
```bash
npm install -g puppeteer
```

## Installation Steps

### 1. Install Python Dependencies

```bash
# Install main dependencies
uv sync

# Install export tools (includes Playwright)
uv sync --group slides-exports
```

### 2. Install External Tools

```bash
# Required: Claude CLI
npm install -g @anthropic-ai/claude-code

# Recommended: Playwright browsers
uv run --group slides-exports playwright install chromium --with-deps

# Optional: ImageMagick for GIF export
sudo apt-get install imagemagick  # Linux
brew install imagemagick          # macOS
```

### 3. Verify Installation

```bash
# Check all dependencies
uv run python -m amplifier.slides_tool.cli check

# Run test suite
uv run python test_slides_tool.py
```

Expected output:
```
🔍 Checking dependencies...

✅ Claude CLI: Installed
✅ Playwright: Installed
⚠️  Puppeteer: Not found (optional)
⚠️  ImageMagick: Not found (needed for GIF export)

📝 Note: The tool works with fallback options even if some dependencies are missing.
```

## Usage

### Command Line Interface

```bash
# Generate a presentation
uv run python -m amplifier.slides_tool.cli generate \
    --prompt "Create a presentation about machine learning basics" \
    --num-slides 5 \
    --export html pdf

# Check status
uv run python -m amplifier.slides_tool.cli check

# List presentations
uv run python -m amplifier.slides_tool.cli list

# Get help
uv run python -m amplifier.slides_tool.cli --help
```

### Python API

```python
from amplifier.slides_tool import (
    SlideGenerator, 
    GenerationRequest, 
    PresentationExporter,
    StateManager
)

# Generate slides
generator = SlideGenerator()
request = GenerationRequest(
    prompt="Python programming fundamentals",
    num_slides=4,
    style="professional"
)

presentation, markdown = await generator.generate(request)
```

## Troubleshooting

### Claude CLI Issues

**Error**: "Claude CLI not found"
```bash
# Check PATH
echo $PATH
which claude

# Reinstall globally
npm uninstall -g @anthropic-ai/claude-code
npm install -g @anthropic-ai/claude-code
```

**Error**: "Claude SDK timeout"
- Ensure you're running within Claude Code environment, or
- Accept that fallback generation will be used outside Claude Code

### Playwright Issues

**Error**: "playwright not found" or browser crashes
```bash
# Reinstall browsers
uv run --group slides-exports playwright install --force

# Check browser installation
uv run --group slides-exports playwright install --dry-run
```

### Permission Issues

**Error**: "Permission denied" during browser install
- Run with sudo for system dependencies, or
- Use the tool without PDF/PNG export (HTML export always works)

## Fallback Behavior

The tool is designed to work with graceful degradation:

| Missing Tool | Impact | Fallback |
|-------------|--------|----------|
| Claude CLI | No AI generation | Template-based generation |
| Playwright | No PDF/PNG export | Print-ready HTML created |
| ImageMagick | No GIF export | Use PNG sequence instead |
| Puppeteer | No alternative export | Playwright or native fallback |

## Development Setup

For development work:

```bash
# Install all development dependencies
uv sync --all-groups

# Run tests
make test

# Run linting and type checking
make check
```

## Cloud Sync Issues

If you experience file I/O errors (especially on WSL with OneDrive):

1. Enable "Always keep on this device" for your data directory
2. Or move your working directory to a non-synced location
3. The tool includes retry logic for cloud sync delays

## Integration with Amplifier Tools

This tool follows the established amplifier tool patterns:

- Uses `uv` for dependency management
- Follows the same error handling patterns
- Integrates with existing file I/O utilities
- Compatible with Claude Code SDK architecture

## Support

For issues:
1. Check dependency status with `cli check`
2. Run the test suite to isolate problems
3. Verify external tools are in PATH
4. Check the Claude CLI is globally installed