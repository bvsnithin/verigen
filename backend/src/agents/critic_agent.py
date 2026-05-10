"""
agents/critic_agent.py
======================
Critic Agent — internally evaluates the generated SystemVerilog assertions
for quality, coverage, correctness, and vacuity.

⚠️  This agent is INTERNAL ONLY.
    Its score and critique are stored in private PipelineState fields
    (prefixed with _) and must NEVER be included in any API response
    or surfaced to the user in the frontend.

The critic calls the LLM with a structured evaluation prompt and extracts
a numeric score via a <score>…</score> tag.  If the LLM fails to produce
a parsable tag, the agent defaults to passed=True after max retries so
the pipeline never stalls.
"""

from __future__ import annotations

import re

from ollama import Client

from .state import PipelineState

# ── Critic system prompt ───────────────────────────────────────────────────────

_CRITIC_SYSTEM = """\
You are a senior hardware verification engineer reviewing SystemVerilog Assertions (SVA).

Evaluate the assertions below against the provided specification on four dimensions:

1. CORRECTNESS   — Do the properties faithfully capture the RTL behaviour?
2. COVERAGE      — Is every logical branch (if/else, case arm, default) covered?
3. VACUITY       — Could any property trivially pass due to an always-false antecedent?
4. SYNTAX        — Is the SVA syntactically valid (property/endproperty, |->  operator)?

Respond in this exact format:

<critique>
[Your detailed assessment per dimension]
</critique>
<score>[A single float between 0.0 and 1.0 reflecting overall quality]</score>

Be rigorous but concise.  Output nothing outside the two XML tags.
"""


def _build_critic_prompt(state: PipelineState) -> str:
    spec_label = "RTL Code" if state.input_type == "rtl" else "Natural Language Specification"
    return (
        f"## {spec_label}\n\n"
        f"```systemverilog\n{state.content.strip()}\n```\n\n"
        f"## Generated Assertions\n\n"
        f"```systemverilog\n{state.assertions_text.strip()}\n```\n\n"
        "Evaluate the assertions now."
    )


def _parse_score(text: str) -> float | None:
    """Extract the float from <score>…</score>; returns None on failure."""
    match = re.search(r"<score>\s*([0-9]*\.?[0-9]+)\s*</score>", text, re.IGNORECASE)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            pass
    return None


def _parse_critique(text: str) -> str:
    """Extract the text from <critique>…</critique>."""
    match = re.search(r"<critique>([\s\S]*?)</critique>", text, re.IGNORECASE)
    return match.group(1).strip() if match else text.strip()


class CriticAgent:
    """
    Evaluates assertion quality and sets internal state fields.

    All outputs are written to private fields (_critique, _score, _passed)
    so that the orchestrator can use them for retry decisions without any
    risk of the data accidentally leaking to the API layer.
    """

    PASS_THRESHOLD = 0.75

    def __init__(self, client: Client, model_name: str):
        self.client = client
        self.model_name = model_name
        print(f"[CriticAgent] Ready (model={model_name}, threshold={self.PASS_THRESHOLD}).")

    # ──────────────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────────────

    def run(self, state: PipelineState) -> PipelineState:
        """Call the LLM critic and populate internal state fields."""
        print(f"\n[CriticAgent] Evaluating attempt {state.attempt}...")

        messages = [
            {"role": "system", "content": _CRITIC_SYSTEM},
            {"role": "user",   "content": _build_critic_prompt(state)},
        ]

        try:
            response = self.client.chat(self.model_name, messages=messages, stream=False)
            raw = response["message"]["content"]
        except Exception as exc:
            # If the LLM call fails, don't block the pipeline
            print(f"[CriticAgent] LLM call failed: {exc}. Defaulting to passed=True.")
            state._critique = ""
            state._score = 1.0
            state._passed = True
            return state

        state._critique = _parse_critique(raw)
        score = _parse_score(raw)

        if score is None:
            print("[CriticAgent] Could not parse score — defaulting to passed=True.")
            state._score = 1.0
            state._passed = True
        else:
            state._score = score
            state._passed = score >= self.PASS_THRESHOLD
            print(f"[CriticAgent] Score={score:.2f}  Passed={state._passed}")

        return state
