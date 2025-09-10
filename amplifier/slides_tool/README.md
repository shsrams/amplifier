# Amplifier Slides Tool

A hybrid code + Claude SDK tool for generating professional reveal.js presentations from natural language prompts.

## Features

- 🎯 **Natural Language Generation** - Create presentations from simple prompts
- 🔄 **Revision Workflow** - Iterate on presentations with feedback
- 📦 **Multi-Format Export** - HTML, PNG, GIF outputs
- 💾 **Version Management** - Automatic versioning and recovery
- 🎨 **Theme Support** - All reveal.js themes available
- ⚡ **Fast Generation** - 120-second timeout with fallback

## Installation

```bash
# Install Python dependencies
pip install click pydantic

# Optional: Install Claude CLI for AI generation
npm install -g @anthropic-ai/claude-code

# Optional: Install export tools
pip install playwright
playwright install chromium
apt-get install imagemagick  # For GIF export
```

## Usage

### Command Line Interface

```bash
# Generate a presentation
python -m amplifier.slides_tool.cli generate \
  --prompt "Create 5 slides about Python programming" \
  --theme black \
  --export html --export png

# Revise an existing presentation
python -m amplifier.slides_tool.cli revise \
  --file slides_output/presentation.md \
  --feedback "Add more code examples"

# Export to different formats
python -m amplifier.slides_tool.cli export \
  --file presentation.html \
  --format png

# Check dependencies
python -m amplifier.slides_tool.cli check

# List saved presentations
python -m amplifier.slides_tool.cli list
```

### Python API

```python
import asyncio
from amplifier.slides_tool import (
    SlideGenerator,
    GenerationRequest,
    StateManager,
    PresentationExporter,
    markdown_to_html
)

async def create_presentation():
    # Generate slides
    generator = SlideGenerator()
    request = GenerationRequest(
        prompt="Create a presentation about AI",
        num_slides=5,
        style="professional"
    )
    
    presentation, markdown = await generator.generate(request)
    
    # Save presentation
    state_manager = StateManager("./output")
    html = markdown_to_html(markdown, presentation.theme)
    save_path = state_manager.save_presentation(
        presentation, markdown, html
    )
    
    # Export to PNG
    exporter = PresentationExporter()
    await exporter.export(ExportRequest(
        presentation_file=str(save_path / "presentation.html"),
        format="png"
    ))
    
    return save_path

# Run
result = asyncio.run(create_presentation())
print(f"Saved to: {result}")
```

## Module Structure

```
amplifier/slides_tool/
├── cli.py           # Click CLI interface
├── generator.py     # Claude SDK integration
├── exporter.py      # Multi-format export
├── state_manager.py # Versioning and persistence
├── models.py        # Pydantic data models
└── utils.py         # Utilities with retry logic
```

## Key Components

### SlideGenerator
- Integrates with Claude SDK for AI generation
- Falls back to templates if SDK unavailable
- Parses markdown to structured presentations

### StateManager
- Automatic versioning of presentations
- Checkpoint saves for crash recovery
- Load/save presentations with metadata

### PresentationExporter
- HTML export (self-contained)
- PNG export (via Playwright)
- PNG screenshots (via Playwright)
- Animated GIF (via ImageMagick)

### Models
- `Presentation` - Complete presentation structure
- `Slide` - Individual slide with content and notes
- `GenerationRequest` - Input for generation
- `ExportRequest` - Export configuration

## Architecture

Following the "bricks and studs" philosophy:
- Each module is self-contained (brick)
- Clear public interfaces (studs)
- Regeneratable from specifications
- Minimal dependencies between modules

## Error Handling

- **120-second timeout** for Claude SDK operations
- **File I/O retry logic** for cloud sync issues
- **Fallback generation** when SDK unavailable
- **Incremental saves** to prevent data loss

## Dependencies

### Required
- Python 3.11+
- click
- pydantic

### Optional
- claude-code-sdk (for AI generation)
- playwright (for PNG export)
- imagemagick (for GIF export)

## Testing

```bash
# Run the test suite
python test_slides_tool.py

# Check specific functionality
python -c "from amplifier.slides_tool import SlideGenerator; print(SlideGenerator().sdk_available)"
```

## Troubleshooting

### Claude SDK Timeout
- Ensure Claude CLI is installed: `npm install -g @anthropic-ai/claude-code`
- Check with: `which claude`
- The tool will use fallback generation if SDK is unavailable

### Export Issues
- PNG export requires Playwright
- PNG export requires Playwright with Chromium
- GIF export requires ImageMagick

### File I/O Errors
- May occur with cloud-synced folders (OneDrive, Dropbox)
- Enable "Always keep on this device" for data folders
- The tool includes automatic retry logic

## License

Part of the Amplifier project. See main project license.