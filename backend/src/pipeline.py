"""
pipeline.py
===========
Thin facade over the multi-agent OrchestratorAgent.

Preserves the original SVAGeneratorPipeline public interface so that
any existing callers (api.py, scripts, tests) continue to work unchanged.
All heavy logic has moved into the agents/ package.
"""

from __future__ import annotations

import os
import sys

from dotenv import load_dotenv
from ollama import Client

from .agents import (
    PipelineState,
    RAGAgent,
    GeneratorAgent,
    LintCriticAgent,
    OrchestratorAgent,
    SummarizerAgent,
)

load_dotenv()

OLLAMA_MODEL = "qwen3-coder-next"


class SVAGeneratorPipeline:
    """
    End-to-End multi-agent pipeline facade for SVA generation.

    Initialises all agents once and reuses them across requests.
    """

    def __init__(self, top_k: int = 3):
        print("[INIT] Setting up the VeriGen Multi-Agent Pipeline...")

        api_key = os.environ.get("OLLAMA_API_KEY")
        if not api_key:
            sys.exit(
                "[ERROR] OLLAMA_API_KEY environment variable is not set.\n"
                "Please add it to your .env file or export it."
            )

        client = Client(
            host="https://ollama.com",
            headers={"Authorization": f"Bearer {api_key}"},
        )

        # Instantiate agents
        self._rag = RAGAgent(top_k=top_k)
        self._generator = GeneratorAgent(client=client, model_name=OLLAMA_MODEL)
        self._lint_critic = LintCriticAgent()   # deterministic — no LLM needed
        self._summarizer = SummarizerAgent(client=client, model_name=OLLAMA_MODEL)

        self._client = client
        print("[INIT] Multi-agent pipeline ready.\n")

    # ── Index pre-loading (kept for API startup compatibility) ─────────────────

    def get_or_build_index(self, dataset_json_name: str) -> tuple:
        """Pre-warm the FAISS index cache (used by api.py at startup)."""
        return self._rag._get_or_build_index(dataset_json_name)

    # ── Primary entry point ────────────────────────────────────────────────────

    def generate_assertions(
        self,
        input_type: str,
        content: str,
        clock_hint: str | None = None,
        synchronous_filter: str | None = None,
        event_callback=None,
    ) -> dict:
        state = PipelineState(
            input_type=input_type,
            content=content,
            clock_hint=clock_hint,
            synchronous_filter=synchronous_filter,
        )

        orchestrator = OrchestratorAgent(
            rag_agent=self._rag,
            generator_agent=self._generator,
            lint_critic=self._lint_critic,
            summarizer_agent=self._summarizer,
            event_callback=event_callback,
        )

        state = orchestrator.run(state)

        return {
            "assertions":  state.assertions_text,
            "explanation": state.explanation_text,
            "summary":     state.summary,
            "lint_clean":  state._lint_clean,   # internal — not forwarded to SSE
            "attempts":    state.attempt,        # internal — not forwarded to SSE
        }
