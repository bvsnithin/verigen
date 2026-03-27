"""
llm_generator.py
================
Step 4 – Connect to an LLM and generate SystemVerilog Assertions (SVA).

Pipeline:
    User RTL  -->  retriever (top-k similar examples)  -->  build_prompt()
                                                                  |
                                                         Ollama cloud API
                                                         (kimi-k2.5 model)
                                                                  |
                                                         SVA property blocks

Usage:
    export OLLAMA_API_KEY=your_api_key
    source venv/bin/activate
    python llm_generator.py
"""

import os
import sys

from dotenv import load_dotenv
from ollama import Client
from sentence_transformers import SentenceTransformer

from retriever import MODEL_NAME, load_index, retrieve
from prompt_builder import SYSTEM_PROMPT, build_prompt

# Load environment variables from .env file
load_dotenv()

# ─────────────────────────────────────────────────────────────
# OLLAMA CLIENT SETUP
# ─────────────────────────────────────────────────────────────

OLLAMA_MODEL = "kimi-k2.5"

def get_client() -> Client:
    """Create and return an authenticated Ollama cloud client."""
    api_key = os.environ.get("OLLAMA_API_KEY")
    if not api_key:
        sys.exit(
            "[ERROR] OLLAMA_API_KEY environment variable is not set.\n"
            "Run: export OLLAMA_API_KEY=your_api_key"
        )
    return Client(
        host="https://ollama.com",
        headers={"Authorization": f"Bearer {api_key}"},
    )


# ─────────────────────────────────────────────────────────────
# CORE GENERATION FUNCTION
# ─────────────────────────────────────────────────────────────

def generate_assertions(
    rtl_code: str,
    top_k: int = 3,
    clock_hint: str | None = None,
    synchronous: str | None = None,
) -> str:
    """
    Full pipeline: retrieve examples --> build prompt --> call LLM --> return SVA.

    Args:
        rtl_code:    The RTL snippet to generate assertions for.
        top_k:       Number of RAG examples to inject as few-shot context.
        clock_hint:  Optional clock string, e.g. "posedge clk".
        synchronous: Filter for retrieval — "True", "False", or None (no filter).

    Returns:
        The raw SVA property blocks produced by the LLM.
    """
    # 1. Load embedding model + FAISS index
    print("[1/4] Loading embedding model and FAISS index ...")
    embed_model = SentenceTransformer(MODEL_NAME)
    index, records = load_index()
    print(f"      Index ready — {index.ntotal:,} vectors.\n")

    # 2. Retrieve similar examples
    print(f"[2/4] Retrieving top-{top_k} similar examples ...")
    examples = retrieve(rtl_code, embed_model, index, records,
                        top_k=top_k, filter_synchronous=synchronous)
    print(f"      Retrieved {len(examples)} example(s).\n")

    # 3. Build prompt
    print("[3/4] Building prompt ...")
    prompt = build_prompt(rtl_code, examples, clock_hint=clock_hint)
    print(f"      Prompt length: {len(prompt):,} chars.\n")

    # 4. Call LLM
    print(f"[4/4] Calling Ollama cloud model '{OLLAMA_MODEL}' (streaming) ...\n")
    client = get_client()

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": prompt},
    ]

    output_parts = []
    for part in client.chat(OLLAMA_MODEL, messages=messages, stream=True):
        chunk = part["message"]["content"]
        print(chunk, end="", flush=True)
        output_parts.append(chunk)

    print()  # newline after streamed output
    return "".join(output_parts)


# ─────────────────────────────────────────────────────────────
# DEMO
# ─────────────────────────────────────────────────────────────

DEMO_RTL_ASYNC = """\
if ( enable && data_valid ) begin
    output_reg = input_data;
    if ( mode_select == 2'b01 ) begin
        result = input_data + offset;
    end
    else begin
        result = input_data;
    end
end
else begin
    output_reg = 0;
end\
"""

DEMO_RTL_SYNC = """\
case ( state_reg )
   2'b00 : begin
     next_state <= IDLE;
     count <= 0;
   end
   2'b01 : begin
     next_state <= ACTIVE;
     count <= count + 1;
   end
   default : begin
     next_state <= ERROR;
   end
endcase\
"""


def run_demo():
    bar = "=" * 70

    # ── Demo A: Asynchronous if/else ─────────────────────────
    print(f"\n{bar}")
    print("  DEMO A — Asynchronous if/else RTL")
    print(bar)
    print("RTL Input:\n")
    print(DEMO_RTL_ASYNC)
    print(f"\n{bar}")
    print("  Generated SVA Assertions:")
    print(bar)

    assertions_async = generate_assertions(
        rtl_code=DEMO_RTL_ASYNC,
        top_k=3,
        synchronous="False",        # prefer async examples
    )

    print(f"\n{bar}\n")

    # ── Demo B: Synchronous case statement ────────────────────
    print(f"{bar}")
    print("  DEMO B — Synchronous case statement RTL")
    print(bar)
    print("RTL Input:\n")
    print(DEMO_RTL_SYNC)
    print(f"\n{bar}")
    print("  Generated SVA Assertions:")
    print(bar)

    assertions_sync = generate_assertions(
        rtl_code=DEMO_RTL_SYNC,
        top_k=3,
        clock_hint="posedge clk",
        synchronous="True",         # prefer sync examples
    )

    print(f"\n{bar}\n")
    print("Done.")


if __name__ == "__main__":
    run_demo()
