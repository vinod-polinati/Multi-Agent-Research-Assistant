"""
SQLite storage layer for job state persistence.

Tables:
  jobs — stores research job metadata, status, and final reports.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).parent / "research.db"


@contextmanager
def _get_conn():
    """Context manager for safe connection handling.

    Yields a connection that auto-commits on success and always closes.
    """
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    """Create the jobs table if it doesn't exist."""
    with _get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id          TEXT PRIMARY KEY,
                topic       TEXT NOT NULL,
                depth       TEXT NOT NULL DEFAULT 'quick',
                status      TEXT NOT NULL DEFAULT 'pending',
                state_json  TEXT,
                report      TEXT,
                created_at  TEXT NOT NULL,
                finished_at TEXT,
                duration_seconds REAL
            )
        """)


def create_job(topic: str, depth: str) -> str:
    """Insert a new job and return its UUID."""
    job_id = str(uuid.uuid4())
    with _get_conn() as conn:
        conn.execute(
            "INSERT INTO jobs (id, topic, depth, status, created_at) VALUES (?, ?, ?, 'pending', ?)",
            (job_id, topic, depth, datetime.now(timezone.utc).isoformat()),
        )
    return job_id


def update_job(
    job_id: str,
    *,
    status: str | None = None,
    state_json: dict | None = None,
    report: str | None = None,
    duration_seconds: float | None = None,
) -> None:
    """Update one or more fields on an existing job."""
    updates: list[str] = []
    params: list = []

    if status is not None:
        updates.append("status = ?")
        params.append(status)
    if state_json is not None:
        updates.append("state_json = ?")
        params.append(json.dumps(state_json, default=str))
    if report is not None:
        updates.append("report = ?")
        params.append(report)
    if duration_seconds is not None:
        updates.append("duration_seconds = ?")
        params.append(duration_seconds)
        updates.append("finished_at = ?")
        params.append(datetime.now(timezone.utc).isoformat())

    if updates:
        params.append(job_id)
        with _get_conn() as conn:
            conn.execute(f"UPDATE jobs SET {', '.join(updates)} WHERE id = ?", params)


def get_job(job_id: str) -> dict | None:
    """Retrieve a job by ID. Returns None if not found."""
    with _get_conn() as conn:
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    if row is None:
        return None
    result = dict(row)
    if result.get("state_json"):
        result["state_json"] = json.loads(result["state_json"])
    return result


def count_active_jobs() -> int:
    """Count jobs that are currently running."""
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT COUNT(*) as cnt FROM jobs WHERE status IN ('pending', 'running', 'planning', 'web_research', 'paper_research', 'critiquing', 'synthesizing')"
        ).fetchone()
    return row["cnt"] if row else 0
