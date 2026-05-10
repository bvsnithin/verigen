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
  GET    /history                     — list of past generations (newest first)
  DELETE /history/{id}               — remove a history entry
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

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from fastapi.middleware.cors import CORSMiddleware

from src.pipeline import SVAGeneratorPipeline
from src.guardrails import check_input_domain

# ── Global state ───────────────────────────────────────────────────────────────

sva_pipeline: SVAGeneratorPipeline | None = None

# In-memory history — list of dicts, newest first
_history: list[dict] = []
MAX_HISTORY = 50


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
        "Multi-agent backend: NeMo Guardrails → RAG → Generator → Verilator Lint → Summarizer. "
        "Includes session history."
    ),
    version="2.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ],
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
    content: str           # full user input
    assertions: str
    explanation: str
    summary: str
    lint_clean: bool       # True if final output passed Verilator lint
    attempts: int          # how many generation attempts were needed


# ── SSE helpers ────────────────────────────────────────────────────────────────

def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


# ── History helpers ────────────────────────────────────────────────────────────

def _save_to_history(request: AssertionRequest, result: dict) -> None:
    """Prepend a new entry to the in-memory history, capping at MAX_HISTORY."""
    entry = {
        "id":              str(uuid.uuid4()),
        "timestamp":       datetime.now(timezone.utc).isoformat(),
        "input_type":      request.input_type,
        "content":         request.content,
        "assertions":      result["assertions"],
        "explanation":     result["explanation"],
        "summary":         result["summary"],
        "lint_clean":      result.get("lint_clean", False),
        "attempts":        result.get("attempts", 1),
    }
    _history.insert(0, entry)
    if len(_history) > MAX_HISTORY:
        _history.pop()


# ── Streaming endpoint ─────────────────────────────────────────────────────────

@app.post("/generate_assertions/stream")
async def generate_assertions_stream(request: AssertionRequest):
    """
    Streaming SSE endpoint.
    Emits agent_event frames per agent, then a 'result' frame on completion.
    Saves the result to history automatically.
    """
    if sva_pipeline is None:
        raise HTTPException(status_code=500, detail="Pipeline not initialised.")

    allowed, rejection_msg = await check_input_domain(request.content)
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
                    input_type=request.input_type,
                    content=request.content,
                    clock_hint=request.clock_hint,
                    synchronous_filter=request.synchronous_filter,
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
                if request.input_type == "rtl"
                else "📚 Loading knowledge base…"
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
                    # Save to history (non-blocking — already in async context)
                    _save_to_history(request, data)
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
async def generate_assertions_endpoint(request: AssertionRequest):
    """Synchronous (non-streaming) endpoint — kept for backwards compatibility."""
    if sva_pipeline is None:
        raise HTTPException(status_code=500, detail="Pipeline not initialised.")
    allowed, rejection_msg = await check_input_domain(request.content)
    if not allowed:
        raise HTTPException(status_code=422, detail=rejection_msg)
    try:
        result = sva_pipeline.generate_assertions(
            input_type=request.input_type,
            content=request.content,
            clock_hint=request.clock_hint,
            synchronous_filter=request.synchronous_filter,
        )
        _save_to_history(request, result)
        return AssertionResponse(
            assertions=result["assertions"],
            explanation=result["explanation"],
            summary=result["summary"],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")


# ── History endpoints ──────────────────────────────────────────────────────────

@app.get("/history", response_model=list[HistoryEntry])
def get_history():
    """Return all history entries, newest first."""
    return _history


@app.delete("/history/{entry_id}")
def delete_history_entry(entry_id: str):
    """Remove a single history entry by ID."""
    global _history
    before = len(_history)
    _history = [e for e in _history if e["id"] != entry_id]
    if len(_history) == before:
        raise HTTPException(status_code=404, detail=f"History entry '{entry_id}' not found.")
    return {"deleted": entry_id}


@app.delete("/history")
def clear_history():
    """Remove all history entries."""
    global _history
    count = len(_history)
    _history = []
    return {"cleared": count}


# ── Health check ───────────────────────────────────────────────────────────────

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "pipeline_ready": sva_pipeline is not None,
        "history_count": len(_history),
        "version": "2.2.0",
    }


if __name__ == "__main__":
    import uvicorn
    # reload=False in production — use `uvicorn api:app --reload` only when developing
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=False)
