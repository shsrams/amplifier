"""
Simple, direct knowledge extraction using Claude Code SDK.
Extracts concepts, relationships, insights, and patterns in a single pass.
"""

import asyncio
import json
import logging
from typing import Any

# Import TimeoutError from asyncio for proper exception handling
TimeoutError = asyncio.TimeoutError

logger = logging.getLogger(__name__)

# Try to import Claude Code SDK - it may not be available outside Claude Code environment
try:
    from claude_code_sdk import ClaudeCodeOptions
    from claude_code_sdk import ClaudeSDKClient

    CLAUDE_SDK_AVAILABLE = True
except ImportError:
    CLAUDE_SDK_AVAILABLE = False
    logger.warning("Claude Code SDK not available - extraction will return empty results")


class KnowledgeSynthesizer:
    """Single-pass knowledge extraction from text."""

    def __init__(self):
        """Initialize the knowledge synthesizer."""
        self.extraction_count = 0

    async def extract(self, text: str, title: str = "", source_id: str = "") -> dict[str, Any]:
        """
        Extract all knowledge in one pass.

        Args:
            text: The text to extract from
            title: Optional title for context
            source_id: Optional source identifier

        Returns:
            Dict with concepts, relationships, insights, and patterns
        """
        if not text:
            return self._empty_extraction(source_id)

        if not CLAUDE_SDK_AVAILABLE:
            logger.warning("Claude Code SDK not available - returning empty extraction")
            return self._empty_extraction(source_id)

        prompt = self._build_prompt(text, title)
        response = ""  # Initialize to avoid unbound variable errors

        try:
            # Use 120-second timeout as per DISCOVERIES.md
            async with asyncio.timeout(120):
                response = await self._call_claude(prompt)
                if not response:
                    logger.warning("Empty response from Claude Code SDK")
                    return self._empty_extraction(source_id)

                # Clean and parse response
                cleaned = self._clean_response(response)
                extraction = json.loads(cleaned)

                # Add metadata
                extraction["source_id"] = source_id
                extraction["title"] = title
                self.extraction_count += 1

                return extraction

        except TimeoutError:
            logger.error("Claude Code SDK timeout - likely running outside Claude Code environment")
            return self._empty_extraction(source_id)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse extraction: {e}")
            logger.debug(f"Response was: {response[:500] if response else 'empty'}")
            return self._empty_extraction(source_id)
        except Exception as e:
            logger.error(f"Extraction failed: {e}")
            return self._empty_extraction(source_id)

    def _build_prompt(self, text: str, title: str) -> str:
        """Build extraction prompt."""
        # Limit text to ~50K tokens (roughly 37K words) to leave room for response
        max_chars = 150000
        if len(text) > max_chars:
            text = text[:max_chars] + "\n\n[Text truncated...]"

        prompt = f"""Extract structured knowledge from this text.

Title: {title if title else "Untitled"}

Analyze the text and extract:
1. Key concepts with descriptions and importance scores
2. Relationships between concepts (subject-predicate-object triples)
3. Actionable insights that could be applied
4. Patterns or themes that emerge across the content

Return ONLY valid JSON in this exact format:
{{
  "concepts": [
    {{
      "name": "concept name",
      "description": "clear description of the concept",
      "importance": 0.8
    }}
  ],
  "relationships": [
    {{
      "subject": "subject concept",
      "predicate": "relationship type",
      "object": "object concept",
      "confidence": 0.9
    }}
  ],
  "insights": [
    "Actionable insight from the text"
  ],
  "patterns": [
    {{
      "name": "pattern name",
      "description": "description of the recurring pattern"
    }}
  ]
}}

Text to analyze:
{text}
"""
        return prompt

    async def _call_claude(self, prompt: str) -> str:
        """Call Claude Code SDK and collect response."""
        if not CLAUDE_SDK_AVAILABLE:
            return ""

        response = ""

        async with ClaudeSDKClient(  # type: ignore
            options=ClaudeCodeOptions(  # type: ignore
                system_prompt="You are a knowledge extraction system. Extract structured information and return ONLY valid JSON.",
                max_turns=1,
            )
        ) as client:
            await client.query(prompt)

            # Collect response from message stream
            async for message in client.receive_response():
                if hasattr(message, "content"):
                    content = getattr(message, "content", [])
                    if isinstance(content, list):
                        for block in content:
                            if hasattr(block, "text"):
                                response += getattr(block, "text", "")

        return response

    def _clean_response(self, response: str) -> str:
        """Clean markdown formatting from response."""
        cleaned = response.strip()

        # Remove markdown code block formatting if present
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]  # Remove ```json
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]  # Remove ```

        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]  # Remove trailing ```

        return cleaned.strip()

    def _empty_extraction(self, source_id: str) -> dict[str, Any]:
        """Return empty extraction structure."""
        return {
            "source_id": source_id,
            "concepts": [],
            "relationships": [],
            "insights": [],
            "patterns": [],
            "error": "Extraction not available",
        }
