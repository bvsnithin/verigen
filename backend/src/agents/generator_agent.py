"""
agents/generator_agent.py
=========================
Generator Agent — builds a prompt from the spec + RAG context and calls
the LLM to produce SystemVerilog assertions.

On retry iterations (attempt > 0), the critic's internal feedback is
injected as an additional assistant-prefixed message so the LLM can
self-correct without the critique ever being surfaced to the user.
"""

from __future__ import annotations

from ollama import Client

from ..prompt_builder import (
    SYSTEM_PROMPT,
    NL_SYSTEM_PROMPT,
    build_prompt,
    build_nl_prompt,
)
from .state import PipelineState

# ── Output parsing helpers ─────────────────────────────────────────────────────

def _parse_output(raw: str) -> tuple[str, str]:
    """Split raw LLM output into (assertions_text, explanation_text)."""
    assertions_text = raw
    explanation_text = ""

    if "## Explanation" in raw:
        parts = raw.split("## Explanation", 1)
        assertions_part = parts[0].strip()
        # Strip the "1. Assertions" label — just show the code block
        if assertions_part.startswith("1. Assertions"):
            assertions_part = assertions_part[len("1. Assertions"):].strip()
        assertions_text = assertions_part
        explanation_text = ("## Explanation\n" + parts[1]).strip()
    elif "2. Explanation" in raw:
        # Legacy format fallback
        parts = raw.split("2. Explanation", 1)
        assertions_part = parts[0].strip()
        if assertions_part.startswith("1. Assertions"):
            assertions_part = assertions_part[len("1. Assertions"):].strip()
        assertions_text = assertions_part
        explanation_text = parts[1].strip()
    elif "```systemverilog" in raw:
        parts = raw.split("```systemverilog", 1)
        if "```" in parts[1]:
            code_parts = parts[1].split("```", 1)
            assertions_text = "```systemverilog\n" + code_parts[0] + "```"
            explanation_text = (parts[0].strip() + "\n" + code_parts[1].strip()).strip()

    return assertions_text, explanation_text


class GeneratorAgent:
    """
    Responsible for:
      1. Building a prompt (RTL or NL) from the spec + retrieved examples.
      2. Optionally injecting critic feedback on retries (internal use only).
      3. Calling the LLM and parsing the assertions + explanation.
    """

    def __init__(self, client: Client, model_name: str):
        self.client = client
        self.model_name = model_name
        print(f"[GeneratorAgent] Ready (model={model_name}).")

    # ──────────────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────────────

    def run(self, state: PipelineState) -> PipelineState:
        """Build prompt, call LLM, parse output into state."""
        state.attempt += 1
        print(f"\n[GeneratorAgent] Attempt {state.attempt} (input_type={state.input_type})...")

        messages = self._build_messages(state)

        print("[GeneratorAgent] Calling LLM...")
        response = self.client.chat(self.model_name, messages=messages, stream=False)
        raw = response["message"]["content"]

        state.raw_assertions = raw
        state.assertions_text, state.explanation_text = _parse_output(raw)
        print(f"[GeneratorAgent] Done ({len(raw)} chars).")
        return state

    # ──────────────────────────────────────────────────────────────────────────
    # Private helpers
    # ──────────────────────────────────────────────────────────────────────────

    def _build_messages(self, state: PipelineState) -> list[dict]:
        """Construct the messages list, injecting critic feedback on retries."""
        if state.input_type == "rtl":
            system = SYSTEM_PROMPT
            user_prompt = build_prompt(
                query_rtl=state.content,
                retrieved_examples=state.retrieved_examples,
                clock_hint=state.clock_hint,
            )
        else:
            system = NL_SYSTEM_PROMPT
            user_prompt = build_nl_prompt(
                query_nl=state.content,
                retrieved_examples=state.retrieved_examples,
                clock_hint=state.clock_hint,
            )

        messages: list[dict] = [
            {"role": "system",    "content": system},
            {"role": "user",      "content": user_prompt},
        ]

        # On retry: inject critique as the previous (failed) assistant turn
        # followed by a correction request — this stays entirely server-side.
        if state.attempt > 1 and state._critique:
            messages.append({
                "role": "assistant",
                "content": state.raw_assertions,  # previous output
            })
            messages.append({
                "role": "user",
                "content": (
                    "Your previous assertions had the following issues:\n\n"
                    f"{state._critique}\n\n"
                    "Please fix all issues and regenerate the complete assertion block, "
                    "following the same output format as before."
                ),
            })

        return messages
