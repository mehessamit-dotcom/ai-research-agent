"""
AI Research Agent — FastAPI Application
Main entry point: serves the API, WebSocket, and frontend.
"""

from __future__ import annotations

import asyncio
import json
import sys
import uuid
from pathlib import Path

# Add project root to sys.path to allow running as `python src/main.py`
sys.path.append(str(Path(__file__).resolve().parent.parent))

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger

from src.core.config import settings
from src.models.schemas import AgentEvent, ResearchRequest, ResearchResponse, ResearchStatus
from src.pipeline import ResearchPipeline

# ─── App Setup ────────────────────────────────────────────

app = FastAPI(
    title="AI Research Agent",
    description="Multi-Agent AI Research System",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve frontend static files
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

# Store active WebSocket connections per research_id
active_connections: dict[str, list[WebSocket]] = {}

# Store research results
research_results: dict[str, dict] = {}


# ─── WebSocket Management ────────────────────────────────

async def emit_event(event: AgentEvent):
    """Broadcast an agent event to all connected WebSocket clients for that research."""
    research_id = event.research_id
    if research_id in active_connections:
        message = event.model_dump_json()
        disconnected = []
        for ws in active_connections[research_id]:
            try:
                await ws.send_text(message)
            except Exception:
                disconnected.append(ws)
        for ws in disconnected:
            active_connections[research_id].remove(ws)

    # Also log to console
    logger.info(f"[{event.agent.value}] {event.title}: {event.content[:100]}")


# ─── Routes ──────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    """Serve the frontend UI."""
    index_path = FRONTEND_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return HTMLResponse("<h1>AI Research Agent API</h1><p>Frontend not found.</p>")


@app.post("/api/research", response_model=ResearchResponse)
async def start_research(request: ResearchRequest):
    """Start a new research job."""
    research_id = str(uuid.uuid4())

    response = ResearchResponse(
        research_id=research_id,
        topic=request.topic,
        status=ResearchStatus.INITIALIZING,
        message="Research job started. Connect via WebSocket to receive updates.",
    )

    # Run research in background
    asyncio.create_task(
        run_research_pipeline(research_id, request.topic, request.custom_instructions or "")
    )

    return response


@app.get("/api/research/{research_id}")
async def get_research_status(research_id: str):
    """Get the current status of a research job."""
    if research_id in research_results:
        return research_results[research_id]
    return {"status": "unknown", "research_id": research_id}


@app.get("/api/report/{research_id}")
async def get_report(research_id: str):
    """Get the generated report file."""
    if research_id in research_results:
        filepath = research_results[research_id].get("filepath")
        if filepath and Path(filepath).exists():
            return FileResponse(filepath, media_type="text/html")
    return {"error": "Report not found"}


@app.websocket("/ws/{research_id}")
async def websocket_endpoint(websocket: WebSocket, research_id: str):
    """WebSocket endpoint for real-time research updates."""
    await websocket.accept()

    if research_id not in active_connections:
        active_connections[research_id] = []
    active_connections[research_id].append(websocket)

    logger.info(f"WebSocket connected for research: {research_id}")

    try:
        while True:
            # Keep connection alive, handle any client messages
            data = await websocket.receive_text()
            # Client can send ping/pong or commands
            if data == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
    except WebSocketDisconnect:
        if research_id in active_connections:
            active_connections[research_id].remove(websocket)
            if not active_connections[research_id]:
                del active_connections[research_id]
        logger.info(f"WebSocket disconnected for research: {research_id}")


# ─── Background Pipeline ─────────────────────────────────

async def run_research_pipeline(research_id: str, topic: str, custom_instructions: str):
    """Run the research pipeline in the background."""
    try:
        pipeline = ResearchPipeline(emit_event=emit_event)
        report = await pipeline.run(
            topic=topic,
            custom_instructions=custom_instructions,
            research_id=research_id,
        )

        research_results[research_id] = {
            "status": "completed",
            "research_id": research_id,
            "topic": topic,
            "report": report.model_dump(),
            "filepath": None,
        }

        # Try to find the report file
        output_dir = Path(settings.REPORT_OUTPUT_DIR)
        if output_dir.exists():
            for f in sorted(output_dir.glob("*.html"), reverse=True):
                research_results[research_id]["filepath"] = str(f)
                break

    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        research_results[research_id] = {
            "status": "failed",
            "research_id": research_id,
            "error": str(e),
        }
        await emit_event(AgentEvent(
            research_id=research_id,
            agent="orchestrator",
            event_type="error",
            title="Pipeline Failed",
            content=str(e),
        ))


# ─── Entry Point ─────────────────────────────────────────

def start():
    """Start the server."""
    logger.info("🚀 Starting AI Research Agent...")
    logger.info(f"   LLM Provider: {settings.LLM_PROVIDER}")
    logger.info(f"   Server: http://localhost:{settings.PORT}")
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)


if __name__ == "__main__":
    start()
