"""
api.py
======
FastAPI backend for VeriGen — multi-agent SVA generation.

SSE event types on /generate_assertions/stream:
  status       { message }
  agent_event  { agent, status, detail }
  result       { assertions, explanation, summary }
  error        { message }

REST endpoints:
  POST   /generate_assertions/stream  — streaming SSE generation
  POST   /generate_assertions         — legacy synchronous
  GET    /history                     — session-scoped history (newest first)
  DELETE /history/{id}               — remove a history entry (session-scoped)
  GET    /health
"""

import os
import json
import uuid
import asyncio
import threading
import queue
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from fastapi.middleware.cors import CORSMiddleware

from src.pipeline import SVAGeneratorPipeline
from src.guardrails import check_input_domain

# ── Global state ───────────────────────────────────────────────────────────────

sva_pipeline: SVAGeneratorPipeline | None = None

# Session-scoped history — keyed by session ID, newest first per session
_history: dict[str, list[dict]] = {}
MAX_HISTORY_PER_SESSION = 50


@asynccontextmanager
async def lifespan(app: FastAPI):
    global sva_pipeline
    print("[API] Starting up — initialising the multi-agent pipeline...")
    try:
        sva_pipeline = SVAGeneratorPipeline(top_k=3)
        print("[API] Pre-loading primary FAISS index (VERT_withRAG)...")
        sva_pipeline.get_or_build_index("VERT_withRAG.json")
        print("[API] Pipeline ready.")
    except Exception as e:
        print(f"[API] Error during startup: {e}")
    yield
    print("[API] Shutting down...")


app = FastAPI(
    title="VeriGen SVA Backend",
    description=(
        "Multi-agent backend: RAG → Generator → Verilator Lint → Summarizer. "
        "Session-scoped history."
    ),
    version="2.3.0",
    lifespan=lifespan,
)

_frontend_url = os.environ.get("FRONTEND_URL", "")
_allowed_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
]
if _frontend_url:
    _allowed_origins.append(_frontend_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Pydantic models ────────────────────────────────────────────────────────────

class AssertionRequest(BaseModel):
    input_type: str = "rtl"
    content: str
    clock_hint: Optional[str] = None
    synchronous_filter: Optional[str] = None


class AssertionResponse(BaseModel):
    assertions: str
    explanation: str
    summary: str


class HistoryEntry(BaseModel):
    id: str
    timestamp: str
    input_type: str
    content: str
    assertions: str
    explanation: str
    summary: str
    lint_clean: bool
    attempts: int


# ── Helpers ────────────────────────────────────────────────────────────────────

def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def _get_session_id(request: Request) -> str:
    return request.headers.get("X-Session-ID", "anonymous")


def _save_to_history(session_id: str, request: AssertionRequest, result: dict) -> None:
    entry = {
        "id":          str(uuid.uuid4()),
        "timestamp":   datetime.now(timezone.utc).isoformat(),
        "input_type":  request.input_type,
        "content":     request.content,
        "assertions":  result["assertions"],
        "explanation": result["explanation"],
        "summary":     result["summary"],
        "lint_clean":  result.get("lint_clean", False),
        "attempts":    result.get("attempts", 1),
    }
    session = _history.setdefault(session_id, [])
    session.insert(0, entry)
    if len(session) > MAX_HISTORY_PER_SESSION:
        session.pop()


# ── Streaming endpoint ─────────────────────────────────────────────────────────

@app.post("/generate_assertions/stream")
async def generate_assertions_stream(request: Request, body: AssertionRequest):
    if sva_pipeline is None:
        raise HTTPException(status_code=500, detail="Pipeline not initialised.")

    session_id = _get_session_id(request)

    allowed, rejection_msg = await check_input_domain(body.content)
    if not allowed:
        async def _blocked():
            yield _sse("error", {"message": rejection_msg})
        return StreamingResponse(
            _blocked(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    async def event_generator():
        evt_queue: queue.Queue = queue.Queue()
        SENTINEL = object()

        def callback(event_name: str, data: dict):
            evt_queue.put(_sse(event_name, data))

        def run_pipeline():
            try:
                result = sva_pipeline.generate_assertions(
                    input_type=body.input_type,
                    content=body.content,
                    clock_hint=body.clock_hint,
                    synchronous_filter=body.synchronous_filter,
                    event_callback=callback,
                )
                evt_queue.put(("result", result))
            except Exception as exc:
                evt_queue.put(("error", {"message": str(exc)}))
            finally:
                evt_queue.put(SENTINEL)

        yield _sse("status", {
            "message": (
                "🔍 Classifying RTL and loading knowledge base…"
                if body.input_type == "rtl"
                else "Loading knowledge base…"
            )
        })

        loop = asyncio.get_event_loop()
        thread = threading.Thread(target=run_pipeline, daemon=True)
        thread.start()

        while True:
            try:
                item = await loop.run_in_executor(None, evt_queue.get, True, 0.05)
            except queue.Empty:
                await asyncio.sleep(0)
                continue

            if item is SENTINEL:
                break

            if isinstance(item, str):
                yield item
            elif isinstance(item, tuple):
                event_name, data = item
                if event_name == "result":
                    _save_to_history(session_id, body, data)
                    yield _sse("result", {
                        "assertions":  data["assertions"],
                        "explanation": data["explanation"],
                        "summary":     data["summary"],
                    })
                else:
                    yield _sse("error", data)

        thread.join(timeout=5)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── Legacy synchronous endpoint ────────────────────────────────────────────────

@app.post("/generate_assertions", response_model=AssertionResponse)
async def generate_assertions_endpoint(request: Request, body: AssertionRequest):
    if sva_pipeline is None:
        raise HTTPException(status_code=500, detail="Pipeline not initialised.")
    allowed, rejection_msg = await check_input_domain(body.content)
    if not allowed:
        raise HTTPException(status_code=422, detail=rejection_msg)
    try:
        result = sva_pipeline.generate_assertions(
            input_type=body.input_type,
            content=body.content,
            clock_hint=body.clock_hint,
            synchronous_filter=body.synchronous_filter,
        )
        _save_to_history(_get_session_id(request), body, result)
        return AssertionResponse(
            assertions=result["assertions"],
            explanation=result["explanation"],
            summary=result["summary"],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")


# ── History endpoints ──────────────────────────────────────────────────────────

@app.get("/history", response_model=list[HistoryEntry])
def get_history(request: Request):
    session_id = _get_session_id(request)
    return _history.get(session_id, [])


@app.delete("/history/{entry_id}")
def delete_history_entry(entry_id: str, request: Request):
    session_id = _get_session_id(request)
    session = _history.get(session_id, [])
    before = len(session)
    _history[session_id] = [e for e in session if e["id"] != entry_id]
    if len(_history[session_id]) == before:
        raise HTTPException(status_code=404, detail=f"History entry '{entry_id}' not found.")
    return {"deleted": entry_id}


@app.delete("/history")
def clear_history(request: Request):
    session_id = _get_session_id(request)
    count = len(_history.pop(session_id, []))
    return {"cleared": count}


# ── Health check ───────────────────────────────────────────────────────────────

@app.get("/health")
def health_check():
    total = sum(len(v) for v in _history.values())
    return {
        "status": "healthy",
        "pipeline_ready": sva_pipeline is not None,
        "history_count": total,
        "version": "2.3.0",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=False)
