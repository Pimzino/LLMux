"""
Request preparation and conversion logic.
"""
import logging
from typing import Dict, Any

from openai_compat import convert_openai_request_to_anthropic, ensure_thinking_prefix
from anthropic import (
    sanitize_anthropic_request,
    inject_claude_code_system_message,
    add_prompt_caching,
)
from anthropic.thinking_keywords import process_thinking_keywords

logger = logging.getLogger(__name__)


def prepare_anthropic_request(
    openai_request: Dict[str, Any],
    request_id: str,
    is_native_anthropic: bool = False
) -> Dict[str, Any]:
    """
    Prepare an Anthropic API request from OpenAI or native format.

    Args:
        openai_request: The request data (OpenAI or Anthropic format)
        request_id: Request ID for logging
        is_native_anthropic: If True, skip OpenAI conversion

    Returns:
        Prepared Anthropic request dict
    """
    # Convert from OpenAI format if needed
    if not is_native_anthropic:
        anthropic_request = convert_openai_request_to_anthropic(openai_request)
    else:
        anthropic_request = openai_request.copy()

    # Process thinking keywords in messages (detect, strip, and get config)
    messages = anthropic_request.get("messages", [])
    processed_messages, thinking_config = process_thinking_keywords(messages)

    if thinking_config:
        anthropic_request["messages"] = processed_messages
        # Only set thinking if not already configured
        if not anthropic_request.get("thinking"):
            anthropic_request["thinking"] = thinking_config
            logger.info(f"[{request_id}] Injected thinking config from keyword: {thinking_config}")
        else:
            # Update budget if keyword specifies higher budget
            existing_budget = anthropic_request["thinking"].get("budget_tokens", 0)
            keyword_budget = thinking_config.get("budget_tokens", 0)
            if keyword_budget > existing_budget:
                anthropic_request["thinking"]["budget_tokens"] = keyword_budget
                logger.info(f"[{request_id}] Updated thinking budget from {existing_budget} to {keyword_budget}")

    # Ensure max_tokens is sufficient if thinking is enabled
    thinking = anthropic_request.get("thinking")
    if thinking and thinking.get("type") == "enabled":
        thinking_budget = thinking.get("budget_tokens", 16000)
        min_response_tokens = 1024
        required_total = thinking_budget + min_response_tokens
        if anthropic_request["max_tokens"] < required_total:
            anthropic_request["max_tokens"] = required_total
            logger.debug(
                f"[{request_id}] Increased max_tokens to {required_total} "
                f"(thinking: {thinking_budget} + response: {min_response_tokens})"
            )

        # Ensure all assistant messages have thinking blocks for multi-turn conversations
        anthropic_request["messages"] = ensure_thinking_prefix(anthropic_request["messages"])
        logger.debug(f"[{request_id}] Ensured thinking prefix on all assistant messages")

    # Sanitize request for Anthropic API constraints
    anthropic_request = sanitize_anthropic_request(anthropic_request)

    # Inject Claude Code system message to bypass authentication detection
    anthropic_request = inject_claude_code_system_message(anthropic_request)

    # Add cache_control to message content blocks for optimal caching
    anthropic_request = add_prompt_caching(anthropic_request)

    return anthropic_request
