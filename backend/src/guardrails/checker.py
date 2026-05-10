from __future__ import annotations

from pathlib import Path
from typing import Any, List, Optional

from langchain_core.language_models.llms import BaseLLM
from langchain_core.outputs import Generation, LLMResult
from nemoguardrails import LLMRails, RailsConfig

from .actions import check_input_domain

_CONFIG_DIR = Path(__file__).parent / "config"
_PASS_MARKER = "__GUARDRAIL_PASSED__"


class _PassThroughLLM(BaseLLM):
    """
    Trivial LLM for NeMo Guardrails' internal flow execution.
    Returns a pass-through marker without any API call.
    When input is not blocked by a rail, this is what NeMo calls — the marker
    tells our checker that the input cleared the guardrail.
    """

    @property
    def _llm_type(self) -> str:
        return "verigen-pass-through"

    def _generate(
        self,
        prompts: List[str],
        stop: Optional[List[str]] = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> LLMResult:
        return LLMResult(generations=[[Generation(text=_PASS_MARKER)] for _ in prompts])

    async def _agenerate(
        self,
        prompts: List[str],
        stop: Optional[List[str]] = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> LLMResult:
        return LLMResult(generations=[[Generation(text=_PASS_MARKER)] for _ in prompts])


class InputGuardrail:
    """
    Validates that user input is related to RTL code or hardware design.
    Wraps NeMo Guardrails to enforce the domain policy defined in rails.co.
    """

    def __init__(self):
        config = RailsConfig.from_path(str(_CONFIG_DIR))
        self._rails = LLMRails(config, llm=_PassThroughLLM())
        self._rails.register_action(check_input_domain, name="check_input_domain")
        print("[InputGuardrail] Ready.")

    async def check(self, user_input: str) -> tuple[bool, str]:
        """
        Returns (allowed, rejection_message).
        allowed=True means the input passed the guardrail — proceed with pipeline.
        allowed=False means the input was blocked — return rejection_message to user.
        """
        try:
            response = await self._rails.generate_async(
                messages=[{"role": "user", "content": user_input}]
            )
            content = (
                response.get("content", "")
                if isinstance(response, dict)
                else str(response or "")
            )
            if _PASS_MARKER in content:
                return True, ""
            if content.strip():
                return False, content.strip()
            # Empty response — input passed with no bot message
            return True, ""
        except Exception as e:
            print(f"[InputGuardrail] Check failed (fail-open): {e}")
            return True, ""
