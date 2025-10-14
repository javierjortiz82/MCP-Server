"""Thinking Manager for Gemini 2.5+ Models.

This module manages the thinking mode feature of Gemini 2.5 series models,
which provides internal reasoning and multi-step planning capabilities.
"""

from typing import Any

from google.genai import types

from client_mcp.config.settings import settings
from client_mcp.utils.logger import get_logger


class ThinkingManager:
    """Manage Gemini 2.5 thinking mode and thought signatures.

    The thinking mode enables models to use an internal "thinking process"
    that significantly improves reasoning and multi-step planning for complex
    tasks such as coding, advanced mathematics, and data analysis.

    Features:
        - Control thinking budget (tokens allocated for internal reasoning)
        - Include thought summaries in responses (for debugging)
        - Automatic thought signature preservation for multi-turn conversations

    Example:
        manager = ThinkingManager(
            enable_thinking=True,
            thinking_budget=1024,
            include_thoughts=False
        )

        config = manager.get_thinking_config()
        # Use config in GenerateContentConfig
    """

    def __init__(
        self,
        enable_thinking: bool = settings.ENABLE_THINKING,
        thinking_budget: int = settings.THINKING_BUDGET,
        include_thoughts: bool = settings.INCLUDE_THOUGHTS,
    ):
        """Initialize thinking manager.

        Args:
            enable_thinking: Enable/disable thinking mode
            thinking_budget: Tokens for thinking (-1=auto, 0=off, >0=fixed)
            include_thoughts: Include thought summaries in response
        """
        self.enable_thinking = enable_thinking
        self.thinking_budget = thinking_budget
        self.include_thoughts = include_thoughts
        self.logger = get_logger("ThinkingManager")

        if self.enable_thinking:
            budget_str = (
                "auto" if thinking_budget == -1 else f"{thinking_budget} tokens"
            )
            self.logger.info(f"🧠 Thinking mode enabled (budget: {budget_str})")
            if self.include_thoughts:
                self.logger.info("💭 Thought summaries will be included in responses")

    def get_thinking_config(self) -> types.ThinkingConfig | None:
        """Build ThinkingConfig for GenerateContentConfig.

        Returns:
            ThinkingConfig if enabled, None otherwise
        """
        if not self.enable_thinking:
            return None

        return types.ThinkingConfig(
            thinking_budget=self.thinking_budget,
            include_thoughts=self.include_thoughts,
        )

    def extract_thoughts(self, response: Any) -> list[str]:
        """Extract thought summaries from model response.

        Thought summaries provide transparency into the model's reasoning
        process before generating the final answer.

        Args:
            response: Gemini API response object

        Returns:
            List of thought summary strings
        """
        thoughts: list[str] = []

        if not response or not hasattr(response, "candidates"):
            return thoughts

        for candidate in response.candidates:
            if not hasattr(candidate, "content") or not candidate.content:
                continue

            if not hasattr(candidate.content, "parts") or not candidate.content.parts:
                continue

            for part in candidate.content.parts:
                # Check if part contains a thought with text
                if (
                    hasattr(part, "thought")
                    and part.thought
                    and hasattr(part, "text")
                    and part.text
                ):
                    thoughts.append(part.text)

        return thoughts

    def log_thoughts(self, thoughts: list[str]) -> None:
        """Log thought summaries for debugging.

        Args:
            thoughts: List of thought summary strings
        """
        if not thoughts:
            return

        self.logger.debug("🧠 Model Thinking Process:")
        for i, thought in enumerate(thoughts, 1):
            # Truncate long thoughts for logging
            thought_preview = thought[:200] + "..." if len(thought) > 200 else thought
            self.logger.debug(f"  {i}. {thought_preview}")

    def format_thoughts_for_display(self, thoughts: list[str]) -> str:
        """Format thoughts for user display.

        Args:
            thoughts: List of thought summary strings

        Returns:
            Formatted string with thought summaries
        """
        if not thoughts:
            return ""

        lines = ["💭 Model Reasoning:"]
        for i, thought in enumerate(thoughts, 1):
            lines.append(f"  {i}. {thought}")

        return "\n".join(lines)

    def is_thinking_enabled(self) -> bool:
        """Check if thinking mode is enabled.

        Returns:
            True if thinking is enabled
        """
        return self.enable_thinking and self.thinking_budget != 0

    def get_stats(self) -> dict[str, Any]:
        """Get thinking manager statistics.

        Returns:
            Dictionary with thinking configuration and stats
        """
        return {
            "thinking_enabled": self.enable_thinking,
            "thinking_budget": self.thinking_budget,
            "include_thoughts": self.include_thoughts,
            "budget_type": (
                "auto"
                if self.thinking_budget == -1
                else "fixed" if self.thinking_budget > 0 else "disabled"
            ),
        }
