"""Tests for agent modules — paper relevance filtering and node contracts."""

from __future__ import annotations

from unittest.mock import MagicMock

from agents.paper_reader import _is_relevant


class TestPaperRelevanceFilter:
    """Tests for the _is_relevant() function that filters arXiv papers."""

    def _make_paper(self, title: str, summary: str, categories: list[str]) -> MagicMock:
        """Create a mock arxiv.Result."""
        paper = MagicMock()
        paper.title = title
        paper.summary = summary
        paper.categories = categories
        return paper

    def test_relevant_ai_paper(self):
        paper = self._make_paper(
            title="Improving LLM Alignment via Steering Vectors",
            summary="We introduce a new method for aligning large language models...",
            categories=["cs.CL", "cs.AI"],
        )
        assert _is_relevant(paper, "Recent advances in LLMs") is True

    def test_irrelevant_astronomy_paper(self):
        paper = self._make_paper(
            title="TESS Planet Occurrence Rates",
            summary="We present a systematic search for planets around M dwarfs...",
            categories=["astro-ph.EP"],
        )
        assert _is_relevant(paper, "Recent advances in LLMs") is False

    def test_irrelevant_3d_reconstruction(self):
        paper = self._make_paper(
            title="VGG-T3: Offline Feed-Forward 3D Reconstruction",
            summary="We present a scalable 3D reconstruction model...",
            categories=["cs.CV"],
        )
        assert _is_relevant(paper, "Recent advances in LLMs") is False

    def test_medical_llm_paper_relevant(self):
        paper = self._make_paper(
            title="MediX-R1: Medical Multimodal LLM",
            summary="An RL framework for medical multimodal large language models...",
            categories=["cs.CL", "cs.CV"],
        )
        assert _is_relevant(paper, "Recent advances in LLMs") is True

    def test_cs_cv_but_mentions_llm(self):
        """A CV paper that genuinely discusses LLMs should pass."""
        paper = self._make_paper(
            title="Vision-Language Models for LLM-driven Reasoning",
            summary="We explore how large language models can be integrated...",
            categories=["cs.CV"],
        )
        # Even in cs.CV, keyword overlap with "LLMs" should make it relevant
        assert _is_relevant(paper, "Recent advances in LLMs") is True

    def test_empty_topic_passes_everything(self):
        """If topic has no meaningful keywords, don't filter anything."""
        paper = self._make_paper(
            title="Random Paper",
            summary="Random content...",
            categories=["math.CO"],
        )
        # Very short keywords get filtered out, so effectively no filtering
        assert _is_relevant(paper, "AI") is True

    def test_stat_ml_paper_relevant(self):
        paper = self._make_paper(
            title="Efficient Fine-tuning of LLMs",
            summary="Methods for efficient training of large language models...",
            categories=["stat.ML"],
        )
        assert _is_relevant(paper, "LLM training efficiency") is True
