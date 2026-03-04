"""Tests for db.py — CRUD operations with isolated temp database."""

from db import create_job, get_job, update_job, count_active_jobs


class TestCreateAndGetJob:
    def test_create_returns_uuid(self):
        job_id = create_job("test topic", "quick")
        assert isinstance(job_id, str)
        assert len(job_id) == 36  # UUID format

    def test_get_returns_job_data(self):
        job_id = create_job("test topic", "deep")
        job = get_job(job_id)
        assert job is not None
        assert job["topic"] == "test topic"
        assert job["depth"] == "deep"
        assert job["status"] == "pending"

    def test_get_nonexistent_returns_none(self):
        assert get_job("nonexistent-id") is None


class TestUpdateJob:
    def test_update_status(self):
        job_id = create_job("topic", "quick")
        update_job(job_id, status="running")
        job = get_job(job_id)
        assert job["status"] == "running"

    def test_update_report(self):
        job_id = create_job("topic", "quick")
        update_job(job_id, report="# My Report", status="done", duration_seconds=10.5)
        job = get_job(job_id)
        assert job["report"] == "# My Report"
        assert job["status"] == "done"
        assert job["duration_seconds"] == 10.5
        assert job["finished_at"] is not None

    def test_update_state_json(self):
        job_id = create_job("topic", "quick")
        state = {"iterations": 2, "web_results": [{"url": "test"}]}
        update_job(job_id, state_json=state)
        job = get_job(job_id)
        assert job["state_json"]["iterations"] == 2
        assert len(job["state_json"]["web_results"]) == 1


class TestCountActiveJobs:
    def test_counts_pending_and_running(self):
        create_job("topic1", "quick")  # pending
        j2 = create_job("topic2", "quick")
        update_job(j2, status="running")
        j3 = create_job("topic3", "quick")
        update_job(j3, status="done")  # should not count
        assert count_active_jobs() == 2

    def test_zero_when_all_done(self):
        j1 = create_job("topic", "quick")
        update_job(j1, status="done")
        assert count_active_jobs() == 0
