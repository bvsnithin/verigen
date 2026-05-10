"""
agents/lint_critic_agent.py
===========================
Lint Critic Agent — runs Verilator on the generated assertions to detect
real syntax and structural errors, replacing the flaky LLM scorer.

⚠️  This agent is INTERNAL ONLY.
    Results are stored in private PipelineState fields (_critique, _passed,
    _lint_errors, _lint_clean) and must NEVER be sent to the user directly.

Workflow:
  1. Extract SV code from the generated assertions block.
  2. Wrap it in a throwaway module so Verilator has a parseable top.
  3. Write to a temp .sv file.
  4. Run: verilator --lint-only --sv --bbox-unsup <file>
     --bbox-unsup: treats unsupported SVA constructs as black boxes
                   instead of hard errors, so valid properties aren't
                   flagged just because Verilator can't simulate them.
  5. Parse stderr for %Error lines.
  6. Clean up the temp file.
  7. Populate state._passed / state._critique for the orchestrator.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path

from .state import PipelineState

# ── Constants ─────────────────────────────────────────────────────────────────

VERILATOR_BIN = shutil.which("verilator") or "verilator"

# Verilator flags:
#   --lint-only     : just lint, don't compile
#   --sv            : treat input as SystemVerilog
#   --bbox-unsup    : black-box unsupported constructs
#   --no-timing     : disable timing-related warnings
#   --Wno-UNDRIVEN  : suppress 'signal has no driver' (expected for wrapper)
#   --Wno-UNUSED    : suppress 'signal is not used'
VERILATOR_FLAGS = [
    "--lint-only", "--sv", "--bbox-unsup", "--no-timing",
    "--Wno-UNDRIVEN", "--Wno-UNUSED",
]

# Error types to IGNORE — these are false-positives caused by the throwaway
# module wrapper not declaring all DUT signals that SVA properties reference.
_IGNORED_ERROR_PATTERNS = [
    "Can't find definition of variable",
    "Can't find definition of task/function",
    "Object not found",
    "Exiting due to",        # summary line — we already have the real errors
]

# Wrap the extracted SVA in a minimal module so Verilator has a valid top
_MODULE_TEMPLATE = """\
// Auto-generated lint wrapper — VeriGen internal
`timescale 1ns/1ps
module _verigen_lint_check(
    input logic clk,
    input logic rst_n
);
{body}
endmodule
"""

# ── Helpers ────────────────────────────────────────────────────────────────────

def _extract_sv_code(assertions_text: str) -> str:
    """
    Pull the raw SV code out of the generated assertions block.

    Handles both:
      - ```systemverilog … ``` fenced blocks
      - Plain text (returned as-is)
    """
    # Prefer fenced systemverilog block
    match = re.search(
        r"```(?:systemverilog|sv|verilog)\s*([\s\S]*?)```",
        assertions_text,
        re.IGNORECASE,
    )
    if match:
        return match.group(1).strip()

    # Fall back: strip any remaining markdown fences generically
    stripped = re.sub(r"```[a-zA-Z]*\n?", "", assertions_text)
    stripped = stripped.replace("```", "")
    return stripped.strip()


def _parse_errors(stderr: str) -> list[str]:
    """
    Return %Error lines, excluding known false-positives from the wrapper module.

    False-positives arise because SVA properties reference DUT signals that
    don't exist in the throwaway _verigen_lint_check module — we only care
    about genuine syntax / structural errors.
    """
    errors = []
    for line in stderr.splitlines():
        line = line.strip()
        if not line.startswith("%Error"):
            continue
        if any(pat in line for pat in _IGNORED_ERROR_PATTERNS):
            continue
        errors.append(line)
    return errors


def _run_verilator(sv_code: str) -> tuple[bool, list[str]]:
    """
    Write sv_code to a temp file, run Verilator lint, return (clean, errors).

    clean  = True  → no %Error lines found
    errors = list of %Error strings (empty when clean)
    """
    tmp_path = Path(tempfile.gettempdir()) / f"verigen_{uuid.uuid4().hex}.sv"
    try:
        wrapped = _MODULE_TEMPLATE.format(body=sv_code)
        tmp_path.write_text(wrapped, encoding="utf-8")

        result = subprocess.run(
            [VERILATOR_BIN] + VERILATOR_FLAGS + [str(tmp_path)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        errors = _parse_errors(result.stderr)
        return (len(errors) == 0), errors

    except subprocess.TimeoutExpired:
        return False, ["%Error: Verilator lint timed out after 30s"]
    except FileNotFoundError:
        return False, [f"%Error: Verilator binary not found at '{VERILATOR_BIN}'"]
    finally:
        tmp_path.unlink(missing_ok=True)


# ── Agent ─────────────────────────────────────────────────────────────────────

class LintCriticAgent:
    """
    Deterministic critic: passes iff Verilator reports zero %Error lines.

    Unlike the LLM-based critic, this never hallucinates — if the SVA
    compiles cleanly under Verilator's linter the assertions are considered
    structurally valid.
    """

    def __init__(self):
        print(f"[LintCriticAgent] Ready (verilator={VERILATOR_BIN}).")

    # ──────────────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────────────

    def run(self, state: PipelineState) -> PipelineState:
        """Lint the generated assertions and populate internal state fields."""
        print(f"\n[LintCriticAgent] Linting attempt {state.attempt}...")

        sv_code = _extract_sv_code(state.assertions_text)

        if not sv_code.strip():
            # Generator produced no extractable code — treat as error
            print("[LintCriticAgent] No SV code found in assertions output.")
            state._lint_errors = ["%Error: No SystemVerilog code block found in generator output"]
            state._lint_clean = False
            state._passed = False
            state._critique = "\n".join(state._lint_errors)
            return state

        clean, errors = _run_verilator(sv_code)
        state._lint_errors = errors
        state._lint_clean = clean
        state._passed = clean

        if clean:
            print("[LintCriticAgent] ✓ Lint clean — no errors.")
            state._critique = ""
        else:
            print(f"[LintCriticAgent] ✗ {len(errors)} error(s) found:")
            for e in errors:
                print(f"   {e}")
            # Build a terse error block to feed back to the generator
            state._critique = (
                "Verilator lint reported the following errors in your generated assertions:\n\n"
                + "\n".join(errors)
                + "\n\nFix all errors above before regenerating."
            )

        return state
