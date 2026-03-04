"""
FastAPI application — endpoints for the Multi-Agent Research Assistant.

Endpoints:
  POST /research              → start a research job
  GET  /research/{id}/stream  → SSE status events
  GET  /research/{id}/report  → retrieve completed report
  POST /research/{id}/export  → download report as .md file
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sse_starlette.sse import EventSourceResponse

from config import MAX_TOPIC_LENGTH, MAX_CONCURRENT_JOBS, RATE_LIMIT
from db import init_db, create_job, update_job, get_job, count_active_jobs
from graph import build_graph
from utils import sanitize_input

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

REPORTS_DIR = Path(__file__).parent / "reports"
REPORTS_DIR.mkdir(exist_ok=True)

# ── In-memory event queues per job (for SSE) ───────────────────────────
_job_events: dict[str, asyncio.Queue] = {}

# ── Rate limiting ─────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    init_db()
    # Compile graph once and reuse across all requests
    app.state.compiled_graph = build_graph()
    logger.info("Research graph compiled and ready")
    yield


app = FastAPI(
    title="Multi-Agent Research Assistant",
    version="2.0.0",
    lifespan=lifespan,
)
app.state.limiter = limiter


# ── Rate limit error handler ─────────────────────────────────────────
@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded. Please try again later."},
    )


# ── Request / Response models ─────────────────────────────────────────
class ResearchRequest(BaseModel):
    topic: str
    depth: str = "quick"  # "quick" | "deep"


class JobCreatedResponse(BaseModel):
    job_id: str


# ── Background runner ─────────────────────────────────────────────────
STATUS_MESSAGES = {
    "planning": ("🧠 Planning research strategy...", 10),
    "web_research": ("🔍 Searching the web...", 35),
    "paper_research": ("📄 Reading academic papers...", 60),
    "critiquing": ("🔎 Evaluating research quality...", 80),
    "synthesizing": ("✍️ Writing the report...", 90),
    "done": ("✅ Report complete!", 100),
    "failed": ("❌ Research failed.", 100),
}


async def _run_research(job_id: str, topic: str, depth: str, compiled_graph) -> None:
    """Run the LangGraph pipeline in the background and push SSE events."""
    queue = _job_events.setdefault(job_id, asyncio.Queue())
    start_time = time.time()

    try:
        initial_state = {
            "topic": topic,
            "depth": depth,
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

        update_job(job_id, status="running")

        last_status = None
        final_state = None

        # Stream through graph steps
        for step in compiled_graph.stream(initial_state):
            # Each step is a dict of {node_name: state_update}
            for node_name, state_update in step.items():
                current_status = state_update.get("status", last_status)
                if current_status and current_status != last_status:
                    msg, progress = STATUS_MESSAGES.get(
                        current_status,
                        (f"Working ({current_status})...", 50),
                    )
                    event = {
                        "status": current_status,
                        "message": msg,
                        "progress": progress,
                        "node": node_name,
                    }
                    await queue.put(event)
                    update_job(job_id, status=current_status)
                    last_status = current_status
                final_state = state_update

        # ── Done ───────────────────────────────────────────────────────
        duration = time.time() - start_time
        report = final_state.get("final_report", "") if final_state else ""

        update_job(
            job_id,
            status="done",
            report=report,
            state_json=final_state,
            duration_seconds=duration,
        )

        await queue.put({
            "status": "done",
            "message": "✅ Report complete!",
            "progress": 100,
        })

    except Exception as e:
        duration = time.time() - start_time
        logger.exception("Research job %s failed", job_id)
        update_job(job_id, status="failed", duration_seconds=duration)
        await queue.put({
            "status": "failed",
            "message": f"❌ Error: {e}",
            "progress": 100,
        })


# ── Endpoints ─────────────────────────────────────────────────────────
@app.post("/research", response_model=JobCreatedResponse)
@limiter.limit(RATE_LIMIT)
async def start_research(req: ResearchRequest, request: Request):
    """Create a research job, start the pipeline in the background."""
    if req.depth not in ("quick", "deep"):
        raise HTTPException(status_code=400, detail="depth must be 'quick' or 'deep'")

    # Sanitize and validate topic
    topic = sanitize_input(req.topic, max_length=MAX_TOPIC_LENGTH)
    if not topic:
        raise HTTPException(status_code=400, detail="topic must not be empty")

    # Check concurrent job limit
    active = count_active_jobs()
    if active >= MAX_CONCURRENT_JOBS:
        raise HTTPException(
            status_code=429,
            detail=f"Too many concurrent jobs ({active}/{MAX_CONCURRENT_JOBS}). Please try again later.",
        )

    job_id = create_job(topic, req.depth)
    _job_events[job_id] = asyncio.Queue()

    # Use graph compiled once at startup
    compiled_graph = request.app.state.compiled_graph
    asyncio.create_task(_run_research(job_id, topic, req.depth, compiled_graph))
    logger.info("Started research job %s: topic=%r depth=%s", job_id, topic, req.depth)
    return {"job_id": job_id}


@app.get("/research/{job_id}/stream")
async def stream_events(job_id: str):
    """SSE endpoint — streams agent status events in real time."""
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    queue = _job_events.setdefault(job_id, asyncio.Queue())

    async def event_generator():
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=120)
                yield {"event": "status", "data": json.dumps(event)}
                if event.get("status") in ("done", "failed"):
                    break
            except asyncio.TimeoutError:
                yield {"event": "ping", "data": "keepalive"}

    return EventSourceResponse(event_generator())


@app.get("/research/{job_id}/report")
async def get_report(job_id: str):
    """Return the completed report or 202 if still in progress."""
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job["status"] not in ("done", "failed"):
        return JSONResponse(
            status_code=202,
            content={"status": job["status"], "message": "Research in progress"},
        )

    state = job.get("state_json") or {}
    return {
        "markdown": job.get("report", ""),
        "metadata": {
            "topic": job["topic"],
            "depth": job["depth"],
            "iterations": state.get("iterations", 1),
            "sources_count": len(state.get("web_results", [])) + len(state.get("paper_results", [])),
            "errors": state.get("errors", []),
            "duration_seconds": job.get("duration_seconds"),
        },
    }


@app.post("/research/{job_id}/export")
async def export_report(job_id: str):
    """Download the report as a .md file."""
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job["status"] != "done" or not job.get("report"):
        raise HTTPException(status_code=400, detail="Report not ready")

    filename = f"report_{job_id[:8]}.md"
    filepath = REPORTS_DIR / filename
    filepath.write_text(job["report"], encoding="utf-8")

    return FileResponse(
        path=str(filepath),
        filename=filename,
        media_type="text/markdown",
    )


# ── Serve frontend ────────────────────────────────────────────────────
app.mount("/", StaticFiles(directory="static", html=True), name="static")
