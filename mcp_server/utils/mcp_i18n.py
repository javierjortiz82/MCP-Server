"""
MCP Handler i18n Utilities

Provides internationalization helpers for MCP context messages.
Automatically handles language detection and message translation for handler context methods.

Usage:
    from utils.mcp_i18n import mcp_info, mcp_debug, mcp_progress

    # Simple message
    await mcp_info(ctx, "booking.create.info_start",
                   customer_name="Juan", booking_date="2025-10-20", booking_time="15:00")

    # Progress reporting
    await mcp_progress(ctx, 1, 3, "booking.create.progress_create")
"""

from typing import Any
from mcp.server.fastmcp import Context
from utils.i18n import t
from utils.language_context import get_current_language
from utils.logger import setup_logging

logger = setup_logging("mcp_i18n")


async def mcp_info(
    ctx: Context,
    message_key: str,
    **kwargs: Any,
) -> None:
    """
    Send an info-level message to MCP context with automatic translation.

    Args:
        ctx: MCP context for message output
        message_key: i18n key (e.g., "booking.create.info_start")
        **kwargs: Parameters for message substitution

    Example:
        await mcp_info(ctx, "booking.create.info_start",
                      customer_name="Juan", booking_date="2025-10-20")
    """
    try:
        user_lang = get_current_language()
        message = t(message_key, lang=user_lang, **kwargs)
        await ctx.info(message)
    except Exception as e:
        logger.warning(f"Error translating info message {message_key}: {e}")
        # Fallback to key if translation fails
        await ctx.info(f"[{message_key}] {kwargs}")


async def mcp_debug(
    ctx: Context,
    message_key: str,
    **kwargs: Any,
) -> None:
    """
    Send a debug-level message to MCP context with automatic translation.

    Args:
        ctx: MCP context for message output
        message_key: i18n key (e.g., "booking.cancel.error_validation")
        **kwargs: Parameters for message substitution

    Example:
        await mcp_debug(ctx, "booking.cancel.error_validation", error=str(e))
    """
    try:
        user_lang = get_current_language()
        message = t(message_key, lang=user_lang, **kwargs)
        await ctx.debug(message)
    except Exception as e:
        logger.warning(f"Error translating debug message {message_key}: {e}")
        # Fallback to key if translation fails
        await ctx.debug(f"[{message_key}] {kwargs}")


async def mcp_progress(
    ctx: Context,
    step: int,
    total: int,
    message_key: str,
    **kwargs: Any,
) -> None:
    """
    Report progress to MCP context with automatic translation.

    Args:
        ctx: MCP context for progress reporting
        step: Current step number (0-based)
        total: Total number of steps
        message_key: i18n key (e.g., "booking.create.progress_validate")
        **kwargs: Parameters for message substitution

    Example:
        await mcp_progress(ctx, 1, 3, "booking.create.progress_create")
    """
    try:
        user_lang = get_current_language()
        message = t(message_key, lang=user_lang, **kwargs)
        await ctx.report_progress(step, total, message)
    except Exception as e:
        logger.warning(f"Error translating progress message {message_key}: {e}")
        # Fallback to key if translation fails
        await ctx.report_progress(step, total, f"[{message_key}]")


async def mcp_info_with_fallback(
    ctx: Context,
    message_key: str,
    fallback_message: str,
    **kwargs: Any,
) -> None:
    """
    Send an info message with fallback text if translation fails.

    Args:
        ctx: MCP context for message output
        message_key: i18n key
        fallback_message: Message to show if translation fails
        **kwargs: Parameters for message substitution

    Example:
        await mcp_info_with_fallback(ctx, "booking.create.info_success",
                                    f"✅ Booking created: ID={booking_id}")
    """
    try:
        user_lang = get_current_language()
        message = t(message_key, lang=user_lang, **kwargs)
        await ctx.info(message)
    except Exception as e:
        logger.warning(f"Error translating message {message_key}, using fallback: {e}")
        await ctx.info(fallback_message)


async def mcp_debug_with_fallback(
    ctx: Context,
    message_key: str,
    fallback_message: str,
    **kwargs: Any,
) -> None:
    """
    Send a debug message with fallback text if translation fails.

    Args:
        ctx: MCP context for message output
        message_key: i18n key
        fallback_message: Message to show if translation fails
        **kwargs: Parameters for message substitution

    Example:
        await mcp_debug_with_fallback(ctx, "booking.cancel.error",
                                     f"Error cancelling booking: {str(e)}", error=str(e))
    """
    try:
        user_lang = get_current_language()
        message = t(message_key, lang=user_lang, **kwargs)
        await ctx.debug(message)
    except Exception as e:
        logger.warning(f"Error translating message {message_key}, using fallback: {e}")
        await ctx.debug(fallback_message)


async def mcp_progress_with_fallback(
    ctx: Context,
    step: int,
    total: int,
    message_key: str,
    fallback_message: str,
    **kwargs: Any,
) -> None:
    """
    Report progress with fallback text if translation fails.

    Args:
        ctx: MCP context for progress reporting
        step: Current step number
        total: Total number of steps
        message_key: i18n key
        fallback_message: Message to show if translation fails
        **kwargs: Parameters for message substitution

    Example:
        await mcp_progress_with_fallback(ctx, 1, 3, "booking.create.progress_create",
                                        "Creating booking in database")
    """
    try:
        user_lang = get_current_language()
        message = t(message_key, lang=user_lang, **kwargs)
        await ctx.report_progress(step, total, message)
    except Exception as e:
        logger.warning(f"Error translating progress message {message_key}, using fallback: {e}")
        await ctx.report_progress(step, total, fallback_message)
