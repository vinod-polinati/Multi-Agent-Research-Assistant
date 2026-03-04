"""
ResearchState — The shared state schema for the LangGraph research pipeline.

Every agent reads from and writes to this TypedDict. LangGraph passes
it automatically between nodes via the StateGraph.
"""

from __future__ import annotations

from typing import TypedDict


class ResearchState(TypedDict):
    # ── Input ──────────────────────────────────────────────────────────
    topic: str
    depth: str  # "quick" | "deep"

    # ── Planning ───────────────────────────────────────────────────────
    sub_questions: list[str]  # 3–5 research sub-questions from Supervisor

    # ── Research outputs ───────────────────────────────────────────────
    web_results: list[dict]  # {url, title, snippet, relevance_score}
    paper_results: list[dict]  # {arxiv_id, title, summary, key_findings}

    # ── Critic outputs ─────────────────────────────────────────────────
    critique: dict  # {quality_score: int, gaps: list[str], contradictions: list[str]}
    follow_up_queries: list[str]  # gap-filling queries for loop re-entry

    # ── Loop control ───────────────────────────────────────────────────
    iterations: int  # incremented each full research loop, max 2

    # ── Error handling ─────────────────────────────────────────────────
    errors: list[str]  # non-fatal errors (e.g. "ArXiv timeout on query 2")

    # ── Output ─────────────────────────────────────────────────────────
    final_report: str
    status: str  # planning | web_research | paper_research | critiquing | synthesizing | done | failed
