"""
Slide generation using Claude SDK.

This module handles the AI-powered generation of slide content,
following the 120-second timeout pattern from DISCOVERIES.md.
"""

import logging
import subprocess
from pathlib import Path

from .models import GenerationRequest
from .models import Presentation
from .models import Slide
from .utils import clean_ai_response
from .utils import parse_slide_count

logger = logging.getLogger(__name__)


class SlideGenerator:
    """Generate slides using Claude SDK."""

    def __init__(self):
        """Initialize generator and check for Claude CLI."""
        self.sdk_available = self._check_claude_cli()
        if not self.sdk_available:
            logger.warning("Claude CLI not found. Install with: npm install -g @anthropic-ai/claude-code")

    def _check_claude_cli(self) -> bool:
        """Check if Claude CLI is available."""
        try:
            result = subprocess.run(["which", "claude"], capture_output=True, text=True, timeout=2)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    async def generate(self, request: GenerationRequest) -> tuple[Presentation, str]:
        """
        Generate presentation from request.

        Returns:
            Tuple of (Presentation object, markdown content)
        """
        # Build the generation prompt
        prompt = self._build_prompt(request)

        # Generate content using Claude SDK or fallback
        if self.sdk_available:
            markdown = await self._generate_with_sdk(prompt)
        else:
            markdown = await self._generate_fallback(prompt, request)

        # Parse markdown into Presentation object
        presentation = self._parse_markdown_to_presentation(markdown, request)

        return presentation, markdown

    async def revise(
        self, current_markdown: str, feedback: str, preserve_structure: bool = True
    ) -> tuple[Presentation, str]:
        """
        Revise existing presentation based on feedback.

        Args:
            current_markdown: Current presentation markdown
            feedback: Revision feedback
            preserve_structure: Whether to keep slide boundaries

        Returns:
            Tuple of (revised Presentation, revised markdown)
        """
        revision_prompt = self._build_revision_prompt(current_markdown, feedback, preserve_structure)

        if self.sdk_available:
            revised_markdown = await self._generate_with_sdk(revision_prompt)
        else:
            revised_markdown = await self._revise_fallback(current_markdown, feedback, preserve_structure)

        # Parse revised markdown
        presentation = self._parse_markdown_to_presentation(revised_markdown, None)
        presentation.version += 1  # Increment version for revision

        return presentation, revised_markdown

    async def _generate_with_sdk(self, prompt: str) -> str:
        """Generate content using Claude Code SDK with proper timeout."""
        import asyncio

        try:
            # Import SDK only when needed
            from claude_code_sdk import ClaudeCodeOptions
            from claude_code_sdk import ClaudeSDKClient

            # Use 120-second timeout as per DISCOVERIES.md
            async def _run_sdk():
                async with ClaudeSDKClient(
                    options=ClaudeCodeOptions(
                        system_prompt="""You are a professional presentation designer that ONLY outputs reveal.js markdown slides.

CRITICAL INSTRUCTIONS:
1. Output ONLY the slide content in reveal.js markdown format
2. Do NOT include any explanatory text, planning, or commentary
3. Do NOT start with phrases like "I'll create..." or "Let me..."
4. Start DIRECTLY with the slide content

FORMAT RULES:
- Use --- to separate horizontal slides (on its own line)
- Use -- for vertical slides if needed (on its own line)
- DO NOT USE speaker notes - they cause regex issues
- Start with # for presentation title
- Use ## for slide titles
- Use standard markdown for lists, code blocks, emphasis, etc.

EXAMPLE OUTPUT:
# Presentation Title

---

## Slide 1 Title
- Bullet point 1
- Bullet point 2

---

## Slide 2 Title
Content here""",
                        max_turns=1,
                    )
                ) as client:
                    await client.query(prompt)

                    response = ""
                    async for message in client.receive_response():
                        if hasattr(message, "content"):
                            content = getattr(message, "content", [])
                            if isinstance(content, list):
                                for block in content:
                                    if hasattr(block, "text"):
                                        response += getattr(block, "text", "")

                    return clean_ai_response(response)

            # Use asyncio.wait_for for timeout
            result = await asyncio.wait_for(_run_sdk(), timeout=120)
            return result if result is not None else ""

        except TimeoutError:
            logger.error("Claude SDK timeout after 120 seconds")
            raise TimeoutError("Claude SDK operation timed out")
        except ImportError:
            logger.warning("Claude Code SDK not installed")
            self.sdk_available = False
            return await self._generate_fallback(prompt, None)
        except Exception as e:
            logger.error(f"Claude SDK error: {e}")
            raise

    async def _generate_fallback(self, prompt: str, request: GenerationRequest | None) -> str:
        """Fallback generation when SDK is not available."""
        # Generate a simple template based on the request
        num_slides = 5  # Default
        if request and request.num_slides:
            num_slides = request.num_slides
        else:
            parsed_count = parse_slide_count(prompt)
            if parsed_count:
                num_slides = parsed_count

        # Extract topic from prompt
        topic = prompt.split("\n")[0] if prompt else "Presentation"

        # Generate basic markdown template
        markdown = f"""# {topic}

---

## Slide 1
Introduction slide

---

## Slide 2
Main content

- Point 1
- Point 2
- Point 3

"""

        # Add more slides as needed
        for i in range(3, min(num_slides + 1, 11)):
            markdown += f"""---

## Slide {i}
Content for slide {i}

"""

        return markdown

    async def _revise_fallback(self, current_markdown: str, feedback: str, preserve_structure: bool) -> str:
        """Fallback revision when SDK is not available."""
        # Simple revision: just add a note about the feedback
        lines = current_markdown.split("\n")

        # Find the first slide and add a revision note
        for i, line in enumerate(lines):
            if line.startswith("## "):
                lines.insert(i + 1, f"\n*[Revision requested: {feedback}]*\n")
                break

        return "\n".join(lines)

    def _build_prompt(self, request: GenerationRequest) -> str:
        """Build generation prompt from request."""
        prompt_parts = [f"Create a presentation: {request.prompt}"]

        if request.context:
            prompt_parts.append(f"\nContext:\n{request.context}")

        if request.context_file:
            try:
                context_content = Path(request.context_file).read_text()
                prompt_parts.append(f"\nFile context:\n{context_content}")
            except Exception as e:
                logger.warning(f"Could not read context file: {e}")

        if request.num_slides:
            prompt_parts.append(f"\nGenerate exactly {request.num_slides} slides.")

        prompt_parts.append(f"\nStyle: {request.style}")

        if request.include_images:
            prompt_parts.append("\nInclude image placeholders where appropriate.")

        prompt_parts.append("""

OUTPUT REQUIREMENTS:
1. Generate EXACTLY the requested number of slides
2. Output ONLY reveal.js markdown format - no explanatory text
3. Start DIRECTLY with the content (# Title)
4. Each slide must have substantial content
5. Use --- between slides (on its own line)
6. DO NOT include speaker notes (they cause issues)

DO NOT include any text like "I'll create..." or "Let me analyze..." - just output the slides directly.""")

        return "\n".join(prompt_parts)

    def _build_revision_prompt(self, current_markdown: str, feedback: str, preserve_structure: bool) -> str:
        """Build revision prompt."""
        prompt = f"""Revise this presentation based on the feedback below.

Current presentation:
{current_markdown}

Feedback:
{feedback}

"""

        if preserve_structure:
            prompt += "Keep the same number of slides and overall structure."
        else:
            prompt += "Feel free to restructure as needed."

        prompt += """

Output the revised presentation in the same Markdown format.
"""

        return prompt

    def _parse_markdown_to_presentation(self, markdown: str, request: GenerationRequest | None) -> Presentation:
        """Parse markdown into Presentation object."""
        slides = []
        current_slide = None
        current_content = []
        current_notes = []
        in_notes = False

        # Extract title from first heading or request
        title = "Presentation"
        subtitle = None

        lines = markdown.split("\n")

        for line in lines:
            # Check for title (first # heading)
            if line.startswith("# ") and title == "Presentation":
                title = line[2:].strip()
                continue

            # Check for slide separator
            if line.strip() in ["---", "--"]:
                # Save current slide if exists
                if current_slide or current_content:
                    if current_slide is None:
                        current_slide = Slide(
                            title="Slide",
                            content="\n".join(current_content).strip(),
                            notes=None,
                            transition="slide",
                            background=None,
                            layout="content",
                        )
                    else:
                        current_slide.content = "\n".join(current_content).strip()

                    if current_notes:
                        current_slide.notes = "\n".join(current_notes).strip()

                    slides.append(current_slide)

                # Reset for next slide
                current_slide = None
                current_content = []
                current_notes = []
                in_notes = False
                continue

            # Check for speaker notes separator
            if line.strip().startswith("Note:"):
                in_notes = True
                # If there's content after "Note:", add it to notes
                note_content = line.strip()[5:].strip()  # Remove "Note:" and get content
                if note_content:
                    current_notes.append(note_content)
                continue

            # Check for slide title (## heading)
            if line.startswith("## "):
                slide_title = line[3:].strip()
                current_slide = Slide(
                    title=slide_title, content="", notes=None, transition="slide", background=None, layout="content"
                )
                continue

            # Add to appropriate section
            if in_notes:
                current_notes.append(line)
            else:
                current_content.append(line)

        # Don't forget the last slide
        if current_slide or current_content:
            if current_slide is None:
                current_slide = Slide(
                    title="Slide",
                    content="\n".join(current_content).strip(),
                    notes=None,
                    transition="slide",
                    background=None,
                    layout="content",
                )
            else:
                current_slide.content = "\n".join(current_content).strip()

            if current_notes:
                current_slide.notes = "\n".join(current_notes).strip()

            slides.append(current_slide)

        # Create presentation object
        presentation = Presentation(
            title=title,
            subtitle=subtitle,
            author=None,
            theme=request.style if request else "black",
            slides=slides,
            version=1,
        )

        return presentation


def markdown_to_html(markdown: str, theme: str = "black") -> str:
    """
    Convert markdown to reveal.js HTML.

    This is a simple conversion - the full HTML template
    will be handled by the exporter module.
    """
    html = f"""<!DOCTYPE html>
<html>
<head>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/reveal.js@4.3.1/dist/reveal.css">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/reveal.js@4.3.1/dist/theme/{theme}.css">
</head>
<body>
    <div class="reveal">
        <div class="slides">
            <section data-markdown data-separator="^---$" data-separator-vertical="^--$" data-separator-notes="^Note:">
                <textarea data-template>
{markdown}
                </textarea>
            </section>
        </div>
    </div>
    <script src="https://cdn.jsdelivr.net/npm/reveal.js@4.3.1/dist/reveal.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/reveal.js@4.3.1/plugin/markdown/markdown.js"></script>
    <script>
        Reveal.initialize({{
            hash: true,
            plugins: [ RevealMarkdown ]
        }});
    </script>
</body>
</html>"""

    return html
