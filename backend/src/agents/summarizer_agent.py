"""
agents/summarizer_agent.py
==========================
Summarizer Agent — distills the final assertion output into a concise,
user-friendly markdown summary covering:

  • What the assertions verify
  • Timing model (synchronous / combinational)
  • Key properties and edge cases
  • Any notable coverage gaps (if evident from the assertions themselves)

The critic's score and critique are intentionally NOT passed to this
prompt — the summary is written purely from the user's perspective.
"""

from __future__ import annotations

from ollama import Client

from .state import PipelineState

# ── Summarizer system prompt ──────────────────────────────────────────────────

_SUMMARIZER_SYSTEM = """\
You are a hardware verification documentation assistant.

Given a SystemVerilog specification and the generated SystemVerilog Assertions (SVA),
write a concise, friendly markdown summary for the engineer who submitted the request.

The summary MUST include these sections (use the exact headers):

## Overview
One or two sentences describing what the assertions verify.

## Timing Model
State whether the design is synchronous or combinational and name the clock if present.

## Properties at a Glance
A bullet list — one bullet per `property … endproperty` block — naming the property
and briefly (≤10 words) stating what it checks.

## Edge Cases Covered
Bullet list of edge cases explicitly handled (e.g., reset, default assignment,
mutual exclusion of branches).

Keep the entire summary under 300 words.  Use plain, professional language.
Do NOT include the raw SVA code — just the human-readable description.
"""


def _build_summarizer_prompt(state: PipelineState) -> str:
    spec_label = "RTL Code" if state.input_type == "rtl" else "Natural Language Specification"
    return (
        f"## {spec_label}\n\n"
        f"```\n{state.content.strip()}\n```\n\n"
        f"## Generated Assertions\n\n"
        f"{state.assertions_text.strip()}\n\n"
        "Write the summary now."
    )


class SummarizerAgent:
    """Generates a concise, user-facing markdown summary of the final results."""

    def __init__(self, client: Client, model_name: str):
        self.client = client
        self.model_name = model_name
        print(f"[SummarizerAgent] Ready (model={model_name}).")

    # ──────────────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────────────

    def run(self, state: PipelineState) -> PipelineState:
        """Call the LLM summarizer and store the result in state.summary."""
        print("\n[SummarizerAgent] Generating summary...")

        messages = [
            {"role": "system", "content": _SUMMARIZER_SYSTEM},
            {"role": "user",   "content": _build_summarizer_prompt(state)},
        ]

        try:
            response = self.client.chat(self.model_name, messages=messages, stream=False)
            state.summary = response["message"]["content"].strip()
            print(f"[SummarizerAgent] Done ({len(state.summary)} chars).")
        except Exception as exc:
            print(f"[SummarizerAgent] LLM call failed: {exc}. Summary will be empty.")
            state.summary = ""

        return state
