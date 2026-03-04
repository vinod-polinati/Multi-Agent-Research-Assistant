"""
Supervisor Agent — Plans sub-questions and routes the research loop.

Responsibilities:
  • Receive the topic, use Groq LLM to generate 3-5 sub-questions.
  • On loop re-entry, merge follow_up_queries into sub_questions.
  • Increment iterations counter on each re-entry.
"""

from __future__ import annotations

import logging
from datetime import datetime

from langchain_core.messages import SystemMessage, HumanMessage

from config import LLM_TEMPERATURE_PLANNING
from state import ResearchState
from utils import get_llm, parse_llm_json

logger = logging.getLogger(__name__)

PLANNING_PROMPT = """You are a research planning expert. Given a topic, generate {n_questions} focused, 
specific sub-questions that together would provide a comprehensive understanding of the topic.

Today's date: {today}

Rules:
- Each question should target a different aspect (definition, current state, key players, 
  recent breakthroughs, open challenges).
- Questions should be specific enough to yield useful search results.
- PRIORITIZE RECENCY: questions should focus on the most recent developments
  (last 6 months). Include time references like "{year}" or "latest" or "recent" in your questions
  to help surface up-to-date information.
- At least one question should specifically ask about breakthroughs or announcements
  from the last 3-6 months.
- Return ONLY a JSON array of strings, no other text.

Topic: {topic}"""

REPLAN_PROMPT = """You are a research planning expert. The initial research on the topic below had gaps.
Generate {n_questions} follow-up questions to fill these gaps.

Topic: {topic}

Gaps identified:
{gaps}

Previous questions already researched:
{previous_questions}

Rules:
- Each question should directly address one or more of the identified gaps.
- Do NOT repeat questions that were already researched.
- Return ONLY a JSON array of strings, no other text."""


def supervisor_node(state: ResearchState) -> dict:
    """LangGraph node: plans sub-questions or re-plans on loop re-entry."""

    llm = get_llm(temperature=LLM_TEMPERATURE_PLANNING)
    iterations = state.get("iterations", 0)
    follow_ups = state.get("follow_up_queries", [])

    # ── First pass: generate sub-questions from scratch ────────────────
    if iterations == 0 and not state.get("sub_questions"):
        depth = state.get("depth", "quick")
        n_questions = 5 if depth == "deep" else 3

        today = datetime.now().strftime("%B %d, %Y")
        current_year = datetime.now().strftime("%Y")

        response = llm.invoke([
            SystemMessage(content="You are a research planning assistant."),
            HumanMessage(content=PLANNING_PROMPT.format(
                topic=state["topic"],
                n_questions=n_questions,
                today=today,
                year=current_year,
            )),
        ])

        sub_questions = parse_llm_json(
            response.content,
            fallback=[state["topic"]],
            expect_array=True,
        )

        logger.info("Supervisor planned %d sub-questions", len(sub_questions))
        return {
            "sub_questions": sub_questions,
            "iterations": 1,
            "status": "planning",
        }

    # ── Re-entry: merge follow-up queries for a second research loop ──
    if follow_ups:
        gaps = state.get("critique", {}).get("gaps", [])
        previous = state.get("sub_questions", [])
        n_questions = min(len(follow_ups), 3)

        response = llm.invoke([
            SystemMessage(content="You are a research planning assistant."),
            HumanMessage(content=REPLAN_PROMPT.format(
                topic=state["topic"],
                n_questions=n_questions,
                gaps="\n".join(f"- {g}" for g in gaps),
                previous_questions="\n".join(f"- {q}" for q in previous),
            )),
        ])

        new_questions = parse_llm_json(
            response.content,
            fallback=follow_ups,
            expect_array=True,
        )

        logger.info("Supervisor re-planned %d follow-up questions", len(new_questions))
        return {
            "sub_questions": new_questions,
            "iterations": iterations + 1,
            "follow_up_queries": [],  # consumed
            "web_results": [],  # reset for fresh pass
            "paper_results": [],  # reset for fresh pass
            "critique": {},  # reset
            "status": "planning",
        }

    return {"status": "planning"}
