"""
agents/orchestrator_agent.py
============================
Orchestrator Agent — manages the multi-agent retry/refinement loop.

Workflow:
    1. RAGAgent         → retrieve context from knowledge base
    2. GeneratorAgent   → generate assertions (LLM call, attempt N)
    3. LintCriticAgent  → run Verilator lint (deterministic, no LLM)
       ├── lint errors  → inject errors into next GeneratorAgent call → retry
       └── lint clean   → SummarizerAgent → done

SSE events emitted (via event_callback):
    agent_event  { agent, status, detail }
      status values: "running" | "done" | "retrying"

The event_callback is optional; when None the orchestrator works fine
(useful for the legacy synchronous endpoint).
"""

from __future__ import annotations

from typing import Callable

from .state import PipelineState
from .rag_agent import RAGAgent
from .generator_agent import GeneratorAgent
from .lint_critic_agent import LintCriticAgent
from .summarizer_agent import SummarizerAgent

MAX_RETRIES = 3  # maximum total generation attempts


class OrchestratorAgent:
    """
    Drives the full multi-agent pipeline.

    Args:
        rag_agent:        Initialised RAGAgent instance.
        generator_agent:  Initialised GeneratorAgent instance.
        lint_critic:      Initialised LintCriticAgent instance.
        summarizer_agent: Initialised SummarizerAgent instance.
        event_callback:   Optional callable(event_name: str, data: dict)
                          used by the FastAPI SSE layer to push progress events.
    """

    def __init__(
        self,
        rag_agent: RAGAgent,
        generator_agent: GeneratorAgent,
        lint_critic: LintCriticAgent,
        summarizer_agent: SummarizerAgent,
        event_callback: Callable[[str, dict], None] | None = None,
    ):
        self.rag = rag_agent
        self.generator = generator_agent
        self.critic = lint_critic
        self.summarizer = summarizer_agent
        self._emit = event_callback or (lambda evt, data: None)
        print("[OrchestratorAgent] Ready.")

    # ──────────────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────────────

    def run(self, state: PipelineState) -> PipelineState:
        """Execute the full pipeline and return the completed state."""
        print("\n[OrchestratorAgent] Starting pipeline...")

        # ── Step 1: RAG ───────────────────────────────────────────────────────
        self._emit("agent_event", {
            "agent": "rag",
            "status": "running",
            "detail": "Embedding query and retrieving context…",
        })
        state = self.rag.run(state)
        self._emit("agent_event", {
            "agent": "rag",
            "status": "done",
            "detail": f"Retrieved {len(state.retrieved_examples)} examples.",
        })

        # ── Steps 2-3: Generate → Lint loop ───────────────────────────────────
        for _attempt in range(MAX_RETRIES):
            # Generator
            self._emit("agent_event", {
                "agent": "generator",
                "status": "running",
                "detail": (
                    "Generating assertions…"
                    if _attempt == 0
                    else f"Fixing lint errors (attempt {_attempt + 1} of {MAX_RETRIES})…"
                ),
            })
            state = self.generator.run(state)
            self._emit("agent_event", {
                "agent": "generator",
                "status": "done",
                "detail": "Assertions generated.",
            })

            # Lint Critic — deterministic, no LLM
            self._emit("agent_event", {
                "agent": "critic",
                "status": "running",
                "detail": "Running Verilator lint check…",
            })
            state = self.critic.run(state)

            if state._passed:
                self._emit("agent_event", {
                    "agent": "critic",
                    "status": "done",
                    "detail": "Lint check passed — no errors.",
                })
                break
            else:
                if _attempt == MAX_RETRIES - 1:
                    # Exhausted retries — proceed with best-effort output
                    self._emit("agent_event", {
                        "agent": "critic",
                        "status": "done",
                        "detail": "Lint check complete (max retries reached).",
                    })
                else:
                    self._emit("agent_event", {
                        "agent": "critic",
                        "status": "retrying",
                        "detail": (
                            f"{len(state._lint_errors)} lint error(s) found — "
                            "sending feedback to generator…"
                        ),
                    })

        # ── Step 4: Summarise ─────────────────────────────────────────────────
        self._emit("agent_event", {
            "agent": "summarizer",
            "status": "running",
            "detail": "Generating summary…",
        })
        state = self.summarizer.run(state)
        self._emit("agent_event", {
            "agent": "summarizer",
            "status": "done",
            "detail": "Summary ready.",
        })

        print("[OrchestratorAgent] Pipeline complete.")
        return state
