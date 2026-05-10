"""
agents/state.py
===============
Shared pipeline state passed between all agents.

Every agent receives a PipelineState, mutates its own fields,
and returns the updated state.  This keeps agents decoupled —
they never call each other directly.
"""

from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class PipelineState:
    # ── Inputs (set by caller) ─────────────────────────────────────────────────
    input_type: str                    # "rtl" | "natural_language"
    content: str                       # user RTL code or NL spec
    clock_hint: str | None = None
    synchronous_filter: str | None = None

    # ── RAG Agent outputs ─────────────────────────────────────────────────────
    target_dataset: str = ""
    retrieved_examples: list[dict] = field(default_factory=list)

    # ── Generator Agent outputs ───────────────────────────────────────────────
    raw_assertions: str = ""           # full LLM output (assertions + explanation)
    assertions_text: str = ""          # parsed assertions block
    explanation_text: str = ""         # parsed explanation block
    attempt: int = 0                   # current retry attempt (0-indexed)

    # ── Lint Critic Agent outputs (internal — never sent to the user) ──────────
    _critique: str = ""                # error text fed back to generator (private)
    _lint_errors: list = None          # raw Verilator %Error lines (private)
    _lint_clean: bool = False          # True = no Verilator errors (private)
    _passed: bool = False              # True when lint is clean (private)

    def __post_init__(self):
        if self._lint_errors is None:
            object.__setattr__(self, '_lint_errors', [])

    # ── Summarizer Agent output ───────────────────────────────────────────────
    summary: str = ""                  # clean markdown summary for the user
