import os
import json
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from fastapi.middleware.cors import CORSMiddleware

from src.pipeline import SVAGeneratorPipeline

# We initialize the pipeline globally so it's loaded once and reused across requests.
sva_pipeline = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global sva_pipeline
    print("[API] Starting up...")
    print("[API] Initializing the RAG SVA Pipeline. This may take a moment to load models...")
    try:
        sva_pipeline = SVAGeneratorPipeline(top_k=3)

        # Pre-load the primary NL dataset index into memory at startup
        # so the first user request doesn't pay the 60s build cost.
        print("[API] Pre-loading primary FAISS index (VERT_withRAG)...")
        sva_pipeline.get_or_build_index("VERT_withRAG.json")
        print("[API] Pipeline initialized successfully.")
    except Exception as e:
        print(f"[API] Error initializing pipeline: {e}")

    yield
    print("[API] Shutting down...")

app = FastAPI(
    title="VeriGen SVA RAG Backend",
    description="Backend API for automatically generating SystemVerilog Assertions using RAG and LLMs.",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Pydantic Models ---

class AssertionRequest(BaseModel):
    input_type: str = "rtl"
    content: str
    clock_hint: Optional[str] = None
    synchronous_filter: Optional[str] = None

class AssertionResponse(BaseModel):
    assertions: str
    explanation: str


def _sse_event(event: str, data: dict) -> str:
    """Format a Server-Sent Events message."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@app.post("/generate_assertions/stream")
async def generate_assertions_stream(request: AssertionRequest):
    """
    Streaming endpoint that emits SSE status events during generation,
    followed by a final 'result' event with the completed assertion output.
    """
    if sva_pipeline is None:
        raise HTTPException(
            status_code=500,
            detail="Pipeline not initialized. Check server logs.",
        )

    async def event_generator():
        try:
            # -- Status: Classifying / Loading Index --
            if request.input_type == "rtl":
                yield _sse_event("status", {"message": "🔍 Classifying RTL and loading knowledge base..."})
            else:
                yield _sse_event("status", {"message": "📚 Loading knowledge base..."})

            # Give the event loop a tick so the SSE is flushed before the blocking call
            await asyncio.sleep(0)

            # Run the blocking index lookup in a thread so we don't block the event loop
            loop = asyncio.get_event_loop()
            if request.input_type == "rtl":
                from src.classifier import RTLClassifier
                target_dataset = await loop.run_in_executor(
                    None, RTLClassifier.classify, request.content
                )
                await loop.run_in_executor(
                    None, sva_pipeline.get_or_build_index, target_dataset
                )
            else:
                target_dataset = "VERT_withRAG.json"
                await loop.run_in_executor(
                    None, sva_pipeline.get_or_build_index, target_dataset
                )

            # -- Status: Retrieving similar examples --
            yield _sse_event("status", {"message": "🔎 Retrieving similar examples from the knowledge base..."})
            await asyncio.sleep(0)

            # -- Status: Building prompt --
            yield _sse_event("status", {"message": "🧠 Building reasoning prompt..."})
            await asyncio.sleep(0)

            # -- Status: Calling LLM --
            yield _sse_event("status", {"message": "✨ Generating assertions with AI (this may take a moment)..."})
            await asyncio.sleep(0)

            # Run the full (blocking) pipeline in a thread
            raw_output = await loop.run_in_executor(
                None,
                lambda: sva_pipeline.generate_assertions(
                    input_type=request.input_type,
                    content=request.content,
                    clock_hint=request.clock_hint,
                    synchronous_filter=request.synchronous_filter,
                    stream=False,
                ),
            )

            # -- Parse the output --
            assertions_text = raw_output
            explanation_text = ""

            if "1. Assertions" in raw_output and "2. Explanation" in raw_output:
                parts = raw_output.split("2. Explanation", 1)
                assertions_text = parts[0].strip()
                explanation_text = ("2. Explanation\n" + parts[1]).strip()
            elif "```systemverilog" in raw_output:
                parts = raw_output.split("```systemverilog", 1)
                if "```" in parts[1]:
                    code_parts = parts[1].split("```", 1)
                    assertions_text = "```systemverilog\n" + code_parts[0] + "```"
                    explanation_text = (parts[0].strip() + "\n" + code_parts[1].strip()).strip()

            # -- Final result event --
            yield _sse_event("result", {
                "assertions": assertions_text,
                "explanation": explanation_text,
            })

        except Exception as e:
            yield _sse_event("error", {"message": f"Generation failed: {str(e)}"})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/generate_assertions", response_model=AssertionResponse)
def generate_assertions_endpoint(request: AssertionRequest):
    """
    (Legacy) Synchronous endpoint — kept for backwards compatibility.
    Prefer /generate_assertions/stream for the live-status UI experience.
    """
    if sva_pipeline is None:
        raise HTTPException(
            status_code=500,
            detail="Pipeline not initialized. Check server logs (e.g. missing OLLAMA_API_KEY).",
        )

    try:
        raw_output = sva_pipeline.generate_assertions(
            input_type=request.input_type,
            content=request.content,
            clock_hint=request.clock_hint,
            synchronous_filter=request.synchronous_filter,
            stream=False,
        )

        assertions_text = raw_output
        explanation_text = "See assertions for details."

        if "1. Assertions" in raw_output and "2. Explanation" in raw_output:
            parts = raw_output.split("2. Explanation", 1)
            assertions_text = parts[0].strip()
            explanation_text = ("2. Explanation\n" + parts[1]).strip()
        elif "```systemverilog" in raw_output:
            parts = raw_output.split("```systemverilog", 1)
            if "```" in parts[1]:
                code_parts = parts[1].split("```", 1)
                assertions_text = "```systemverilog\n" + code_parts[0] + "```"
                explanation_text = parts[0].strip() + "\n" + code_parts[1].strip()

        return AssertionResponse(assertions=assertions_text, explanation=explanation_text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "pipeline_ready": sva_pipeline is not None,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
