import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

from src.pipeline import SVAGeneratorPipeline

# We initialize the pipeline globally so it's loaded once and reused across requests.
# It holds the sentence-transformer model and the connection to Ollama.
sva_pipeline = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global sva_pipeline
    print("[API] Starting up...")
    print("[API] Initializing the RAG SVA Pipeline. This may take a moment to load models...")
    try:
        sva_pipeline = SVAGeneratorPipeline(top_k=3)
        print("[API] Pipeline initialized successfully.")
    except Exception as e:
        print(f"[API] Error initializing pipeline: {e}")
        # Not exiting here so the server can still start and show 500s 
        # for debugging if OLLAMA_API_KEY is missing, etc.
    
    yield
    print("[API] Shutting down...")

app = FastAPI(
    title="VeriGen SVA RAG Backend",
    description="Backend API for automatically generating SystemVerilog Assertions using RAG and LLMs.",
    version="1.0.0",
    lifespan=lifespan
)

# --- Pydantic Models for Request and Response Validation ---

class AssertionRequest(BaseModel):
    input_type: str = "rtl"
    content: str
    clock_hint: Optional[str] = None
    synchronous_filter: Optional[str] = None

class AssertionResponse(BaseModel):
    assertions: str
    explanation: str

@app.post("/generate_assertions", response_model=AssertionResponse)
def generate_assertions_endpoint(request: AssertionRequest):
    """
    Generate SystemVerilog Assertions (SVA) from RTL description.
    Provides RAG-guided Chain of Thought explanations leading up to the final SVA code.
    """
    if sva_pipeline is None:
        raise HTTPException(
            status_code=500, 
            detail="Pipeline not initialized. Check server logs (e.g. missing OLLAMA_API_KEY)."
        )

    try:
        # Running the synchronous pipeline text generation.
        # FastAPI handles sync endpoints in a threadpool so it won't block the async event loop.
        raw_output = sva_pipeline.generate_assertions(
            input_type=request.input_type,
            content=request.content,
            clock_hint=request.clock_hint,
            synchronous_filter=request.synchronous_filter,
            stream=False
        )
        
        # Parse the raw output to separate assertions and explanation
        assertions_text = raw_output
        explanation_text = "See assertions for details."
        
        if "1. Assertions" in raw_output and "2. Explanation" in raw_output:
            parts = raw_output.split("2. Explanation", 1)
            assertions_text = parts[0].strip()
            explanation_text = ("2. Explanation\n" + parts[1]).strip()
        elif "```systemverilog" in raw_output:
            # Fallback if the headings are missing but code blocks are present
            parts = raw_output.split("```systemverilog", 1)
            if "```" in parts[1]:
                code_parts = parts[1].split("```", 1)
                assertions_text = "```systemverilog\n" + code_parts[0] + "```"
                explanation_text = parts[0].strip() + "\n" + code_parts[1].strip()

        return AssertionResponse(
            assertions=assertions_text, 
            explanation=explanation_text
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")

# Add a simple health check payload for debugging/availability
@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "pipeline_ready": sva_pipeline is not None
    }

if __name__ == "__main__":
    import uvicorn
    # To run this script directly: python api.py
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
