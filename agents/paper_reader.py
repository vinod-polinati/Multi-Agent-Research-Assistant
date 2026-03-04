"""
Paper Reader Agent — Queries ArXiv and extracts paper summaries.

Responsibilities:
  • Query ArXiv API for each sub-question (top papers each).
  • Filter out papers that are not relevant to the research topic.
  • Download PDFs, extract text via PyMuPDF.
  • Summarise methodology and key findings with Groq.
  • Retry transient failures with exponential backoff.
  • Append structured results to paper_results.
"""

from __future__ import annotations

import logging
import tempfile

import arxiv
import fitz  # PyMuPDF
from langchain_core.messages import SystemMessage, HumanMessage
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from config import (
    LLM_TEMPERATURE_ANALYSIS,
    MAX_ARXIV_RESULTS_PER_QUERY,
    RETRY_ATTEMPTS,
    RETRY_MIN_WAIT,
    RETRY_MAX_WAIT,
)
from state import ResearchState
from utils import get_llm, parse_llm_json

logger = logging.getLogger(__name__)

SUMMARIZE_PROMPT = """You are an academic paper summarisation expert.
Given the following extracted text from a research paper, provide:
1. A concise summary (2-3 sentences)
2. Key findings as a JSON array of strings

Paper title: {title}

Extracted text (first 3000 chars):
{text}

Return your response in this exact JSON format:
{{"summary": "...", "key_findings": ["finding1", "finding2", ...]}}"""


# ── Relevance filtering ──────────────────────────────────────────────

# ArXiv categories relevant to AI/ML/NLP research
_AI_CATEGORIES = {
    "cs.CL", "cs.AI", "cs.LG", "cs.CV", "cs.IR", "cs.NE",
    "cs.MA", "cs.HC", "stat.ML", "eess.AS",
}


def _is_relevant(paper: arxiv.Result, topic: str, threshold: float = 0.25) -> bool:
    """Check if an ArXiv paper is relevant to the research topic.

    Uses two signals:
      1. Category match — does the paper belong to AI/ML categories?
      2. Keyword overlap — do topic keywords appear in the title/abstract?

    Returns True if the paper passes either check.
    """
    import re

    # Extract clean words, ignoring common stop words
    stop_words = {
        "the", "and", "for", "with", "from", "that", "this", "these", "those", 
        "are", "was", "were", "has", "have", "had", "recent", "advances", "in", 
        "of", "to", "an", "on", "at", "by", "how", "what", "which", "about"
    }
    
    topic_words = set(re.findall(r'\b[a-z0-9]+\b', topic.lower()))
    topic_words = {w for w in topic_words if w not in stop_words and len(w) > 2}
    
    # Expand plurals (e.g., llms -> llm)
    expanded_words = set(topic_words)
    for w in topic_words:
        if w.endswith("s") and len(w) > 3:
            expanded_words.add(w[:-1])
            
    if not expanded_words:
        return True  # Can't properly filter empty semantic topics
        
    text = f"{paper.title} {paper.summary}".lower()
    
    # Count matches using word boundaries
    matches = sum(1 for w in expanded_words if re.search(rf'\b{re.escape(w)}\b', text))

    # Check category overlap
    paper_categories = {cat for cat in (paper.categories or [])}
    if paper_categories & _AI_CATEGORIES:
        # Paper is in an AI category — only require 1 keyword match
        if matches >= 1:
            return True

    # For non-AI papers, require stronger keyword match
    # Calculate ratio relative to the original number of meaningful topic words
    return (matches / len(topic_words)) >= threshold


# ── PDF extraction ────────────────────────────────────────────────────

def _extract_pdf_text(pdf_path: str, max_chars: int = 3000) -> str:
    """Extract text from a PDF using PyMuPDF."""
    try:
        doc = fitz.open(pdf_path)
        text = ""
        for page in doc:
            text += page.get_text()
            if len(text) >= max_chars:
                break
        doc.close()
        return text[:max_chars]
    except Exception as e:
        logger.warning("PDF extraction failed: %s", e)
        return ""


# ── Retry wrapper ─────────────────────────────────────────────────────

@retry(
    stop=stop_after_attempt(RETRY_ATTEMPTS),
    wait=wait_exponential(min=RETRY_MIN_WAIT, max=RETRY_MAX_WAIT),
    retry=retry_if_exception_type((ConnectionError, TimeoutError, OSError)),
    reraise=True,
)
def _download_pdf(result: arxiv.Result, dirpath: str) -> str:
    """Download a paper PDF with retry on transient network errors."""
    return result.download_pdf(dirpath=dirpath)


# ── Main node ─────────────────────────────────────────────────────────

def paper_reader_node(state: ResearchState) -> dict:
    """LangGraph node: searches ArXiv, downloads papers, and summarises them."""

    llm = get_llm(temperature=LLM_TEMPERATURE_ANALYSIS)
    sub_questions = state.get("sub_questions", [])
    topic = state.get("topic", "")
    paper_results: list[dict] = []
    errors: list[str] = list(state.get("errors", []))

    arxiv_client = arxiv.Client()

    for i, question in enumerate(sub_questions):
        try:
            logger.info("ArXiv search [%d/%d]: %s", i + 1, len(sub_questions), question)

            search = arxiv.Search(
                query=question,
                max_results=MAX_ARXIV_RESULTS_PER_QUERY * 2,  # fetch extra to allow filtering
                sort_by=arxiv.SortCriterion.SubmittedDate,
                sort_order=arxiv.SortOrder.Descending,
            )

            relevant_count = 0
            for result in arxiv_client.results(search):
                # ── Relevance filter ──────────────────────────────
                if not _is_relevant(result, topic):
                    logger.debug(
                        "Skipping irrelevant paper: %s (categories: %s)",
                        result.title,
                        result.categories,
                    )
                    continue

                if relevant_count >= MAX_ARXIV_RESULTS_PER_QUERY:
                    break
                relevant_count += 1

                paper_entry = {
                    "arxiv_id": result.entry_id,
                    "title": result.title,
                    "published": result.published.strftime("%Y-%m-%d") if result.published else "",
                    "categories": result.categories or [],
                    "summary": "",
                    "key_findings": [],
                }

                # Try to download and extract PDF text
                try:
                    with tempfile.TemporaryDirectory() as tmp_dir:
                        pdf_path = _download_pdf(result, dirpath=tmp_dir)
                        extracted_text = _extract_pdf_text(pdf_path)

                        if extracted_text:
                            response = llm.invoke([
                                SystemMessage(content="You are an academic research summariser."),
                                HumanMessage(content=SUMMARIZE_PROMPT.format(
                                    title=result.title,
                                    text=extracted_text,
                                )),
                            ])

                            parsed = parse_llm_json(response.content)
                            paper_entry["summary"] = parsed.get("summary", result.summary[:500])
                            paper_entry["key_findings"] = parsed.get("key_findings", [])
                        else:
                            paper_entry["summary"] = result.summary[:500]
                            paper_entry["key_findings"] = []

                except Exception as e:
                    logger.warning("PDF download/extract failed for %s: %s", result.title, e)
                    paper_entry["summary"] = result.summary[:500]
                    paper_entry["key_findings"] = []

                paper_results.append(paper_entry)

        except Exception as e:
            error_msg = f"ArXiv search failed for query '{question}': {e}"
            logger.warning(error_msg)
            errors.append(error_msg)

    logger.info("Paper reader collected %d relevant results", len(paper_results))
    return {
        "paper_results": paper_results,
        "errors": errors,
        "status": "paper_research",
    }
