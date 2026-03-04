"""
LangGraph StateGraph — Orchestrates the research pipeline.

Builds the supervisor → web_researcher → paper_reader → critic → synthesizer
graph with conditional edges implementing the routing logic from the PRD.
"""

from __future__ import annotations

from langgraph.graph import StateGraph, END

from config import MAX_ITERATIONS, QUALITY_THRESHOLD
from state import ResearchState
from agents.supervisor import supervisor_node
from agents.web_researcher import web_researcher_node
from agents.paper_reader import paper_reader_node
from agents.critic import critic_node
from agents.synthesizer import synthesizer_node


def supervisor_router(state: ResearchState) -> str:
    """Conditional edge: decides which node to visit next."""
    if not state.get("web_results"):
        return "web_researcher"
    if not state.get("paper_results"):
        return "paper_reader"
    if state.get("depth") == "quick":
        return "synthesizer"  # skip critic in quick mode
    if not state.get("critique"):
        return "critic"
    if (
        state.get("critique", {}).get("quality_score", 10) < QUALITY_THRESHOLD
        and state.get("iterations", 0) < MAX_ITERATIONS
    ):
        return "supervisor"  # loop back with follow_up_queries
    return "synthesizer"


def build_graph() -> StateGraph:
    """Construct and compile the research pipeline graph."""

    graph = StateGraph(ResearchState)

    # ── Add nodes ──────────────────────────────────────────────────────
    graph.add_node("supervisor", supervisor_node)
    graph.add_node("web_researcher", web_researcher_node)
    graph.add_node("paper_reader", paper_reader_node)
    graph.add_node("critic", critic_node)
    graph.add_node("synthesizer", synthesizer_node)

    # ── Entry point ────────────────────────────────────────────────────
    graph.set_entry_point("supervisor")

    # ── Conditional edges from supervisor ──────────────────────────────
    graph.add_conditional_edges(
        "supervisor",
        supervisor_router,
        {
            "web_researcher": "web_researcher",
            "paper_reader": "paper_reader",
            "critic": "critic",
            "synthesizer": "synthesizer",
            "supervisor": "supervisor",
        },
    )

    # ── Sequential edges for specialist agents ─────────────────────────
    graph.add_edge("web_researcher", "paper_reader")
    graph.add_edge("paper_reader", "critic")

    # ── Critic routes back through the supervisor router ───────────────
    graph.add_conditional_edges(
        "critic",
        supervisor_router,
        {
            "supervisor": "supervisor",
            "synthesizer": "synthesizer",
            "web_researcher": "web_researcher",
            "paper_reader": "paper_reader",
            "critic": "critic",
        },
    )

    # ── Synthesizer → done ─────────────────────────────────────────────
    graph.add_edge("synthesizer", END)

    return graph.compile()
