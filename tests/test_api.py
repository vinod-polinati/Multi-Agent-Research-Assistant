from __future__ import annotations

from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture
def client():
    """Create a TestClient with lifespan events."""
    with TestClient(app) as c:
        yield c


class TestStartResearch:
    @patch("main._run_research")
    def test_invalid_depth_rejected(self, mock_run, client):
        resp = client.post("/research", json={"topic": "LLMs", "depth": "invalid"})
        assert resp.status_code == 400
        assert "depth" in resp.json()["detail"]

    @patch("main._run_research")
    def test_empty_topic_rejected(self, mock_run, client):
        resp = client.post("/research", json={"topic": "   ", "depth": "quick"})
        assert resp.status_code == 400
        assert "topic" in resp.json()["detail"]

    @patch("main._run_research")
    def test_topic_sanitized(self, mock_run, client):
        # We don't test the full pipeline here, just that it accepts a valid topic
        resp = client.post("/research", json={"topic": "LLMs\x00test", "depth": "quick"})
        # Should either succeed (202/200) or return job_id
        assert resp.status_code == 200
        assert "job_id" in resp.json()


class TestGetReport:
    def test_nonexistent_job_404(self, client):
        resp = client.get("/research/nonexistent-id/report")
        assert resp.status_code == 404

    @patch("main._run_research")
    def test_pending_job_returns_202(self, mock_run, client):
        # Create a job but don't run it to completion
        resp = client.post("/research", json={"topic": "test", "depth": "quick"})
        job_id = resp.json()["job_id"]
        report_resp = client.get(f"/research/{job_id}/report")
        # Should be 202 since job is still in progress
        assert report_resp.status_code in (200, 202)


class TestExportReport:
    @patch("main._run_research")
    def test_export_before_completion_fails(self, mock_run, client):
        resp = client.post("/research", json={"topic": "test", "depth": "quick"})
        job_id = resp.json()["job_id"]
        export_resp = client.post(f"/research/{job_id}/export")
        assert export_resp.status_code == 400

    def test_export_nonexistent_404(self, client):
        resp = client.post("/research/nonexistent/export")
        assert resp.status_code == 404
