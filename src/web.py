"""
FastAPI web server for N.O.V.A (Navaneed's Operational Virtual Assistant).

Provides:
- POST /api/chat — send a message, get a response
- POST /api/new — start a new conversation thread
- GET /api/history — get conversation history for a thread
- GET / — serve the chat UI
"""

import asyncio
import json
import os
import uuid
from functools import partial

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from langchain_core.messages import AIMessage, HumanMessage
from pydantic import BaseModel

from src.agent import graph
from src.analytics.queries import (
    get_overview_stats,
    get_topic_breakdown,
    get_method_effectiveness,
    get_progress_over_time,
    get_streak,
    get_weak_topics,
)
from src.analytics.bandit import thompson_select, get_rankings
from src.always_on.scheduler import (
    hub, start_scheduler, stop_scheduler, get_settings, update_settings,
)
from src.always_on.profiler import get_teaching_instructions, analyze_learning_style

app = FastAPI(title="N.O.V.A", version="4.0")

# Allow all origins for local dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str
    thread_id: str = ""


class NewThreadRequest(BaseModel):
    thread_id: str = ""


@app.post("/api/chat")
async def chat(req: ChatRequest):
    """Send a message and get a response."""
    thread_id = req.thread_id or str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    try:
        # Run the synchronous graph.invoke in a thread pool to avoid blocking
        # FastAPI's async event loop (LLM calls can take seconds).
        result = await asyncio.get_event_loop().run_in_executor(
            None,
            partial(
                graph.invoke,
                {"messages": [HumanMessage(content=req.message)]},
                config=config,
            ),
        )
        reply = result["messages"][-1]
        return JSONResponse({
            "response": reply.content,
            "thread_id": thread_id,
        })
    except Exception as e:
        return JSONResponse(
            {"error": str(e), "thread_id": thread_id},
            status_code=500,
        )


@app.post("/api/new")
async def new_thread(req: NewThreadRequest):
    """Start a new conversation thread."""
    thread_id = req.thread_id or str(uuid.uuid4())
    return JSONResponse({"thread_id": thread_id})


@app.get("/api/history")
async def get_history(thread_id: str):
    """Get conversation history for a thread."""
    config = {"configurable": {"thread_id": thread_id}}
    try:
        states = await asyncio.get_event_loop().run_in_executor(
            None,
            partial(list, graph.get_state_history(config)),
        )
        messages = []
        for state in states:
            for msg in state.values.get("messages", []):
                if isinstance(msg, HumanMessage):
                    messages.append({"role": "user", "content": msg.content})
                elif isinstance(msg, AIMessage) and msg.content:
                    messages.append({"role": "assistant", "content": msg.content})
        messages.reverse()
        return JSONResponse({"messages": messages, "thread_id": thread_id})
    except Exception as e:
        return JSONResponse({"messages": [], "thread_id": thread_id, "error": str(e)})


# ── Analytics API ─────────────────────────────────────────────────

@app.get("/api/analytics/overview")
async def analytics_overview(days: int = 30):
    return JSONResponse(get_overview_stats(days))


@app.get("/api/analytics/topics")
async def analytics_topics(days: int = 30):
    return JSONResponse(get_topic_breakdown(days))


@app.get("/api/analytics/methods")
async def analytics_methods(days: int = 30):
    return JSONResponse(get_method_effectiveness(days))


@app.get("/api/analytics/progress")
async def analytics_progress(days: int = 30):
    return JSONResponse(get_progress_over_time(days))


@app.get("/api/analytics/streak")
async def analytics_streak():
    return JSONResponse(get_streak())


@app.get("/api/analytics/weak-topics")
async def analytics_weak_topics():
    return JSONResponse(get_weak_topics(10))


@app.get("/api/analytics/bandit/rankings")
async def bandit_rankings(topic: str = ""):
    return JSONResponse(get_rankings(topic=topic or None))


@app.get("/api/analytics/bandit/suggest")
async def bandit_suggest(topic: str = ""):
    return JSONResponse(thompson_select(topic=topic or None, n=3))


# ── PWA / Static Assets ─────────────────────────────────────────

@app.get("/manifest.json")
async def pwa_manifest():
    manifest = {
        "name": "N.O.V.A Assistant",
        "short_name": "N.O.V.A",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#0a0a0f",
        "theme_color": "#00d4ff",
        "description": "Personal AI assistant for studying, coding, and building projects.",
        "icons": [
            {"src": "/icon-192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "/icon-512.png", "sizes": "512x512", "type": "image/png"}
        ]
    }
    return JSONResponse(manifest)


@app.get("/sw.js", response_class=HTMLResponse)
async def service_worker():
    sw_path = os.path.join(os.path.dirname(__file__), "web", "sw.js")
    if os.path.exists(sw_path):
        with open(sw_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read(), media_type="application/javascript")
    return HTMLResponse(content="// no service worker", media_type="application/javascript")


@app.get("/icon-192.png")
@app.get("/icon-512.png")
async def pwa_icon():
    from fastapi.responses import FileResponse
    # Generate a simple SVG-based icon if PNG doesn't exist
    icon_path = os.path.join(os.path.dirname(__file__), "web", "icon-192.png")
    if os.path.exists(icon_path):
        return FileResponse(icon_path)
    # Fallback: serve the SVG
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="192" height="192" viewBox="0 0 192 192">'
        '<rect width="192" height="192" rx="32" fill="#0a0a0f"/>'
        '<circle cx="96" cy="70" r="30" fill="#00d4ff" opacity="0.9"/>'
        '<rect x="46" y="115" width="100" height="12" rx="6" fill="#00d4ff" opacity="0.6"/>'
        '<rect x="56" y="135" width="80" height="8" rx="4" fill="#00d4ff" opacity="0.3"/>'
        '</svg>'
    )
    from fastapi.responses import Response
    return Response(content=svg, media_type="image/svg+xml")


@app.on_event("startup")
async def startup():
    start_scheduler()
    analyze_learning_style()  # Pre-compute learning profile


@app.on_event("shutdown")
async def shutdown():
    stop_scheduler()


# ── SSE Notification Stream ────────────────────────────────────

@app.get("/api/notifications")
async def notification_stream():
    """Server-Sent Events stream for proactive notifications."""
    async def event_generator():
        async for notification in hub.subscribe():
            yield f"data: {json.dumps(notification)}\n\n"
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/settings")
async def get_user_settings():
    return JSONResponse(get_settings())


class SettingsUpdate(BaseModel):
    always_on: bool | None = None
    voice_lock_enabled: bool | None = None
    tts_enabled: bool | None = None
    reminder_interval_min: int | None = None
    quiet_hours_start: int | None = None
    quiet_hours_end: int | None = None
    preferred_name: str | None = None


@app.post("/api/settings")
async def update_user_settings(req: SettingsUpdate):
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    update_settings(updates)
    return JSONResponse({"ok": True, "settings": get_settings()})


@app.get("/api/learning-profile")
async def learning_profile():
    from src.always_on.profiler import analyze_learning_style as _analyze
    return JSONResponse(_analyze())


# ── Serve the chat UI ──────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def index():
    """Serve the chat interface."""
    html_path = os.path.join(os.path.dirname(__file__), "web", "index.html")
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>N.O.V.A</h1><p>UI not found.</p>")


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    """Serve the analytics dashboard."""
    html_path = os.path.join(os.path.dirname(__file__), "web", "dashboard.html")
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>Dashboard</h1><p>Not found.</p>")


def run_server(host: str = "0.0.0.0", port: int = 8000):
    """Run the web server."""
    import uvicorn
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_server()
