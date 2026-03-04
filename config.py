"""
Central configuration — all tuneable parameters in one place.

Override any value via environment variables. Agents and graph import from here
instead of hardcoding model names, temperatures, and limits.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

# ── LLM settings ──────────────────────────────────────────────────────
LLM_MODEL: str = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")
LLM_TEMPERATURE_PLANNING: float = float(os.getenv("LLM_TEMP_PLANNING", "0.3"))
LLM_TEMPERATURE_ANALYSIS: float = float(os.getenv("LLM_TEMP_ANALYSIS", "0.2"))
LLM_TEMPERATURE_SYNTHESIS: float = float(os.getenv("LLM_TEMP_SYNTHESIS", "0.4"))
LLM_MAX_TOKENS_SYNTHESIS: int = int(os.getenv("LLM_MAX_TOKENS_SYNTHESIS", "4096"))

# ── Search settings ───────────────────────────────────────────────────
MAX_WEB_RESULTS_PER_QUERY: int = int(os.getenv("MAX_WEB_RESULTS", "5"))
MAX_ARXIV_RESULTS_PER_QUERY: int = int(os.getenv("MAX_ARXIV_RESULTS", "3"))
TAVILY_RECENCY_DAYS: int = int(os.getenv("TAVILY_RECENCY_DAYS", "180"))

# ── Pipeline settings ─────────────────────────────────────────────────
MAX_ITERATIONS: int = int(os.getenv("MAX_ITERATIONS", "2"))
QUALITY_THRESHOLD: int = int(os.getenv("QUALITY_THRESHOLD", "7"))

# ── API / server settings ────────────────────────────────────────────
MAX_TOPIC_LENGTH: int = int(os.getenv("MAX_TOPIC_LENGTH", "500"))
MAX_CONCURRENT_JOBS: int = int(os.getenv("MAX_CONCURRENT_JOBS", "5"))
RATE_LIMIT: str = os.getenv("RATE_LIMIT", "10/minute")

# ── Retry settings ────────────────────────────────────────────────────
RETRY_ATTEMPTS: int = int(os.getenv("RETRY_ATTEMPTS", "3"))
RETRY_MIN_WAIT: int = int(os.getenv("RETRY_MIN_WAIT", "1"))
RETRY_MAX_WAIT: int = int(os.getenv("RETRY_MAX_WAIT", "10"))
