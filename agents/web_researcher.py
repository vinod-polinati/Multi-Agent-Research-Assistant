"""
Web Researcher Agent — Searches the web using Tavily for each sub-question.

Responsibilities:
  • Iterate over sub_questions, call Tavily search (top results per query).
  • Append structured snippets with source URLs to web_results.
  • Retry transient failures with exponential backoff.
  • Log errors to the errors list on per-query failures.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime

from dotenv import load_dotenv
from tavily import TavilyClient
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from config import (
    MAX_WEB_RESULTS_PER_QUERY,
    TAVILY_RECENCY_DAYS,
    RETRY_ATTEMPTS,
    RETRY_MIN_WAIT,
    RETRY_MAX_WAIT,
)
from state import ResearchState

load_dotenv()
logger = logging.getLogger(__name__)


def _make_search_fn(client: TavilyClient):
    """Create a retryable search function bound to the client."""

    @retry(
        stop=stop_after_attempt(RETRY_ATTEMPTS),
        wait=wait_exponential(min=RETRY_MIN_WAIT, max=RETRY_MAX_WAIT),
        retry=retry_if_exception_type((ConnectionError, TimeoutError, OSError)),
        reraise=True,
    )
    def _search(query: str, **kwargs) -> dict:
        return client.search(query=query, **kwargs)

    return _search


def web_researcher_node(state: ResearchState) -> dict:
    """LangGraph node: searches the web for each sub-question via Tavily."""

    client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
    search = _make_search_fn(client)

    sub_questions = state.get("sub_questions", [])
    web_results: list[dict] = []
    errors: list[str] = list(state.get("errors", []))

    current_year = datetime.now().strftime("%Y")

    for i, question in enumerate(sub_questions):
        try:
            # Append year to query to bias toward recent results
            recency_query = f"{question} {current_year}"
            logger.info("Web search [%d/%d]: %s", i + 1, len(sub_questions), recency_query)
            response = search(
                query=recency_query,
                search_depth="advanced",
                max_results=MAX_WEB_RESULTS_PER_QUERY,
                include_answer=False,
                days=TAVILY_RECENCY_DAYS,
            )

            for result in response.get("results", []):
                web_results.append({
                    "url": result.get("url", ""),
                    "title": result.get("title", ""),
                    "snippet": result.get("content", "")[:1000],
                    "relevance_score": result.get("score", 0.0),
                    "query": question,
                })

        except Exception as e:
            error_msg = f"Tavily search failed for query '{question}': {e}"
            logger.warning(error_msg)
            errors.append(error_msg)

    logger.info("Web researcher collected %d results", len(web_results))
    return {
        "web_results": web_results,
        "errors": errors,
        "status": "web_research",
    }
