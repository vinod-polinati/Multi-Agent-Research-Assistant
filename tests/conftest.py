"""
Shared test fixtures for the Multi-Agent Research Assistant test suite.
"""

from __future__ import annotations

import os
import sys
import pytest

# Ensure the project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import init_db, DB_PATH


@pytest.fixture(autouse=True)
def _use_temp_db(tmp_path, monkeypatch):
    """Use a temp SQLite database for every test."""
    test_db = tmp_path / "test_research.db"
    import db
    monkeypatch.setattr(db, "DB_PATH", test_db)
    init_db()
    yield


@pytest.fixture
def sample_state_empty():
    """A ResearchState at the beginning — no data yet."""
    return {
        "topic": "Recent advances in LLMs",
        "depth": "quick",
        "sub_questions": [],
        "web_results": [],
        "paper_results": [],
        "critique": {},
        "follow_up_queries": [],
        "iterations": 0,
        "errors": [],
        "final_report": "",
        "status": "planning",
    }


@pytest.fixture
def sample_state_with_results():
    """A ResearchState with pre-populated research data."""
    return {
        "topic": "Recent advances in LLMs",
        "depth": "deep",
        "sub_questions": [
            "What are the latest LLM releases in 2026?",
            "How have hallucination rates improved?",
        ],
        "web_results": [
            {
                "url": "https://example.com/llm-2026",
                "title": "LLM Advances 2026",
                "snippet": "GPT-5 and Claude 4 represent major improvements...",
                "relevance_score": 0.95,
                "query": "What are the latest LLM releases in 2026?",
            }
        ],
        "paper_results": [
            {
                "arxiv_id": "http://arxiv.org/abs/2601.12345v1",
                "title": "Reducing LLM Hallucination via Steering",
                "published": "2026-01-15",
                "categories": ["cs.CL", "cs.AI"],
                "summary": "A novel approach to reduce hallucination...",
                "key_findings": ["90% reduction in factual errors"],
            }
        ],
        "critique": {
            "quality_score": 7,
            "gaps": ["Missing coverage of open-source models"],
            "contradictions": [],
        },
        "follow_up_queries": ["open source LLMs 2026 latest"],
        "iterations": 1,
        "errors": [],
        "final_report": "",
        "status": "critiquing",
    }
