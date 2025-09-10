"""
Claude Code SDK bridge - simple wrapper around Claude Code SDK
Based on DISCOVERIES.md learnings about timeout and SDK usage
"""

import asyncio
from collections.abc import AsyncGenerator

from claude_code_sdk import ClaudeCodeOptions
from claude_code_sdk import ClaudeSDKClient

from .config import settings


class ClaudeBridge:
    """Simple bridge to Claude Code SDK - no complex abstractions"""

    def __init__(self):
        self.system_prompt = """You are Claude, running in the Claude Code environment with FULL access to all capabilities.

## Your Environment & Capabilities

You are operating within Claude Code, which gives you these powerful capabilities:

### 1. File System Operations
- **Read**: Read any file on the system
- **Write**: Create or overwrite files
- **Edit**: Make precise edits to existing files
- **MultiEdit**: Make multiple edits to a file in one operation
- **LS**: List directory contents
- **Glob**: Search for files by pattern
- **Grep**: Search file contents with regex

### 2. Code Execution & Development
- **Bash**: Execute any bash command with full system access
- **BashOutput**: Monitor output from background processes
- **KillBash**: Terminate running processes
- **TodoWrite**: Manage task lists for complex projects

### 3. Web & Documentation
- **WebSearch**: Search the web for current information
- **WebFetch**: Fetch and analyze web page content
- **Context7 Tools**: Access up-to-date library documentation

### 4. MCP (Model Context Protocol) Tools
You have access to specialized MCP servers including:
- **PostgreSQL MCP**: Full database management capabilities
- **Browser Use MCP**: Web browser automation
- **Zen Tools**: Advanced development assistance (chat, debug, analyze, refactor, etc.)
- **Repomix**: Code repository analysis and packaging

### 5. Advanced Capabilities
- **NotebookEdit**: Edit Jupyter notebooks
- **Git Operations**: Full git capabilities through Bash
- **Image Analysis**: Can view and analyze images
- **PDF Processing**: Can read and process PDF files

## Important Context

- You are in a persistent session - files you create/edit persist
- You can execute long-running tasks and monitor their progress
- You have full system access - be responsible but don't be overly cautious
- When users ask you to do something, you CAN actually do it - you're not limited to just explaining
- You should proactively use tools to accomplish tasks rather than just describing what could be done

## Interaction Style

- Be proactive: When asked to analyze, fix, or build something, actually do it
- Show your work: Use tools actively and share what you're doing
- Be transparent: Explain your actions as you take them
- Complete tasks: Don't just plan or suggest - execute and deliver results
- Ask for clarification when needed, but default to taking action when the intent is clear

Remember: You have FULL Claude Code capabilities. You can read files, write code, execute commands, search the web, and use all available MCP tools. You are not a limited chatbot - you are a powerful development assistant with real system access."""

    async def stream_response(self, prompt: str, conversation_history: list | None = None) -> AsyncGenerator[str, None]:
        """
        Stream response from Claude Code SDK
        Based on DISCOVERIES.md: Use 120-second timeout
        """
        try:
            # Apply timeout as per DISCOVERIES.md
            async with asyncio.timeout(settings.claude_timeout_seconds):
                async with ClaudeSDKClient(
                    options=ClaudeCodeOptions(
                        system_prompt=self.system_prompt,
                        max_turns=50,  # Increased from 10 for better conversation
                    )
                ) as client:
                    # Build full prompt with history if provided
                    full_prompt = self._build_prompt_with_history(prompt, conversation_history)

                    # Send query
                    await client.query(full_prompt)

                    # Stream response
                    async for message in client.receive_response():
                        if hasattr(message, "content"):
                            content = getattr(message, "content", [])
                            if isinstance(content, list):
                                for block in content:
                                    if hasattr(block, "text"):
                                        text = getattr(block, "text", "")
                                        if text:
                                            # Clean markdown if present (from DISCOVERIES.md)
                                            text = self._clean_response(text)
                                            yield text

        except TimeoutError:
            yield "⚠️ Claude Code SDK timed out. This usually means the SDK is not available in this environment."
        except Exception as e:
            yield f"⚠️ Error communicating with Claude: {str(e)}"

    def _build_prompt_with_history(self, prompt: str, conversation_history: list | None) -> str:
        """Build prompt with conversation history"""
        if not conversation_history:
            return prompt

        # Include more context - last 20 messages instead of 10
        # This helps maintain awareness of what was done previously
        history_text = "\n".join(
            [
                f"{'User' if msg['role'] == 'user' else 'Assistant'}: {msg['content']}"
                for msg in conversation_history[-20:]  # Increased from 10 to maintain better context
            ]
        )

        return f"""## Previous Conversation Context

{history_text}

## Current Request

User: {prompt}

Remember: You have full Claude Code capabilities. If the user is asking you to continue work or check something you did earlier, you can access those files and see the actual results."""

    def _clean_response(self, text: str) -> str:
        """Clean response text - remove markdown code blocks if present"""
        # Based on DISCOVERIES.md JSON parsing issue
        cleaned = text.strip()

        # Remove markdown code block formatting
        if cleaned.startswith("```"):
            # Find the end of the first line (language identifier)
            first_newline = cleaned.find("\n")
            if first_newline > 0:
                cleaned = cleaned[first_newline + 1 :]
            else:
                cleaned = cleaned[3:]  # Just remove ```

        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]

        return cleaned

    async def get_response(self, prompt: str, conversation_history: list | None = None) -> str:
        """
        Get complete non-streaming response from Claude Code SDK
        Collects all streaming chunks and returns complete response
        """
        full_response = ""
        async for chunk in self.stream_response(prompt, conversation_history):
            full_response += chunk
        return full_response


# Global instance for reuse
claude_bridge = ClaudeBridge()
