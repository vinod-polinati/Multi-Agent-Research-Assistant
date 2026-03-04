"""
Critic Agent — Reviews combined research and scores quality.

Responsibilities:
  • Review all web_results + paper_results holistically.
  • Score quality 1-10, identify gaps and contradictions.
  • Populate follow_up_queries for potential Supervisor re-entry.
"""

from __future__ import annotations

import logging
from datetime import datetime

from langchain_core.messages import SystemMessage, HumanMessage

from config import LLM_TEMPERATURE_ANALYSIS
from state import ResearchState
from utils import get_llm, parse_llm_json

logger = logging.getLogger(__name__)

CRITIC_PROMPT = """You are a research quality critic. Evaluate the following research results 
and provide a thorough critique.

Today's date: {today}
Topic: {topic}

Sub-questions investigated:
{sub_questions}

Web Research Results ({n_web} items):
{web_summary}

Academic Paper Results ({n_papers} items):
{paper_summary}

Provide your critique in this exact JSON format:
{{
    "quality_score": <integer 1-10>,
    "gaps": ["gap1", "gap2", ...],
    "contradictions": ["contradiction1", ...],
    "follow_up_queries": ["specific search query to fill gap1", ...]
}}

Scoring guide:
- 1-3: Major gaps, insufficient coverage
- 4-6: Decent coverage but notable gaps
- 7-8: Good coverage, minor gaps
- 9-10: Comprehensive, well-sourced

RECENCY IS CRITICAL:
- If most sources are older than 6 months from today's date, penalize the score by 2-3 points.
- Identify missing coverage of very recent developments (last 3 months) as a gap.
- Follow-up queries should include the current year and recent time references
  (e.g. "{year}", "latest", "announced this month") to surface fresh information.

Return ONLY the JSON, no other text."""


def critic_node(state: ResearchState) -> dict:
    """LangGraph node: critiques the combined research results."""

    llm = get_llm(temperature=LLM_TEMPERATURE_ANALYSIS)

    web_results = state.get("web_results", [])
    paper_results = state.get("paper_results", [])

    # Build concise summaries for the prompt
    web_summary = "\n".join(
        f"- [{r.get('title', 'Untitled')}]({r.get('url', '')}) — {r.get('snippet', '')[:200]}"
        for r in web_results[:15]  # cap to avoid token overflow
    ) or "No web results."

    paper_summary = "\n".join(
        f"- {r.get('title', 'Untitled')} (ArXiv) — {r.get('summary', '')[:200]}"
        for r in paper_results[:10]
    ) or "No paper results."

    sub_questions = "\n".join(f"- {q}" for q in state.get("sub_questions", []))

    today = datetime.now().strftime("%B %d, %Y")
    current_year = datetime.now().strftime("%Y")

    response = llm.invoke([
        SystemMessage(content="You are a research quality critic."),
        HumanMessage(content=CRITIC_PROMPT.format(
            topic=state["topic"],
            today=today,
            year=current_year,
            sub_questions=sub_questions,
            n_web=len(web_results),
            web_summary=web_summary,
            n_papers=len(paper_results),
            paper_summary=paper_summary,
        )),
    ])

    critique = parse_llm_json(
        response.content,
        fallback={
            "quality_score": 5,
            "gaps": ["Could not parse critique response"],
            "contradictions": [],
            "follow_up_queries": [],
        },
    )

    follow_up_queries = critique.pop("follow_up_queries", [])

    logger.info(
        "Critic scored quality at %d/10 with %d gaps",
        critique.get("quality_score", 0),
        len(critique.get("gaps", [])),
    )

    return {
        "critique": critique,
        "follow_up_queries": follow_up_queries,
        "status": "critiquing",
    }
