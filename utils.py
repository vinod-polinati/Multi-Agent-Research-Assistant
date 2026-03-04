"""
Shared utilities for the Multi-Agent Research Assistant.

Provides common helpers used across multiple agents to avoid code duplication:
  • parse_llm_json() — safe JSON parsing with regex fallback
  • get_llm()        — factory for ChatGroq with configured model
  • sanitize_input() — input validation and cleanup
"""

from __future__ import annotations

import json
import logging
import re
import unicodedata

from langchain_groq import ChatGroq

from config import LLM_MODEL, MAX_TOPIC_LENGTH

logger = logging.getLogger(__name__)


def parse_llm_json(
    content: str,
    fallback: dict | list | None = None,
    expect_array: bool = False,
) -> dict | list:
    """Parse JSON from LLM output, with regex fallback for wrapped responses.

    Args:
        content: Raw LLM response text.
        fallback: Value to return if parsing fails entirely.
        expect_array: If True, look for a JSON array instead of object.

    Returns:
        Parsed JSON as dict or list, or the fallback value.
    """
    if fallback is None:
        fallback = [] if expect_array else {}

    # Try direct parse first
    try:
        result = json.loads(content)
        return result
    except (json.JSONDecodeError, TypeError):
        pass

    # Regex fallback: extract JSON object or array from surrounding text
    pattern = r"\[.*\]" if expect_array else r"\{.*\}"
    match = re.search(pattern, content, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    logger.warning("Failed to parse LLM JSON, using fallback. Content: %s", content[:200])
    return fallback


def get_llm(temperature: float = 0.3, max_tokens: int | None = None) -> ChatGroq:
    """Create a ChatGroq LLM instance with the configured model.

    Args:
        temperature: Sampling temperature (0.0–1.0).
        max_tokens: Optional max output tokens.

    Returns:
        Configured ChatGroq instance.
    """
    kwargs = {"model": LLM_MODEL, "temperature": temperature}
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens
    return ChatGroq(**kwargs)


def sanitize_input(text: str, max_length: int = MAX_TOPIC_LENGTH) -> str:
    """Sanitize user input: strip control characters, normalise, and truncate.

    Args:
        text: Raw user input string.
        max_length: Maximum allowed length.

    Returns:
        Cleaned and truncated string.
    """
    # Remove control characters (keep newlines and tabs)
    cleaned = "".join(
        ch for ch in text
        if unicodedata.category(ch)[0] != "C" or ch in ("\n", "\t")
    )
    # Normalise whitespace
    cleaned = " ".join(cleaned.split())
    # Truncate
    return cleaned[:max_length].strip()
