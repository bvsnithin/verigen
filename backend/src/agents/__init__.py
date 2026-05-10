"""
agents/
=======
VeriGen multi-agent package.

Agents:
    RAGAgent          — embeds the query and retrieves context from FAISS
    GeneratorAgent    — generates SystemVerilog assertions via LLM
    CriticAgent       — internally evaluates assertion quality (score not exposed)
    OrchestratorAgent — drives the retry/refinement loop and emits SSE events
    SummarizerAgent   — produces a clean final summary for the user
"""

from .state import PipelineState
from .rag_agent import RAGAgent
from .generator_agent import GeneratorAgent
from .critic_agent import CriticAgent          # kept for reference
from .lint_critic_agent import LintCriticAgent  # active critic
from .orchestrator_agent import OrchestratorAgent
from .summarizer_agent import SummarizerAgent

__all__ = [
    "PipelineState",
    "RAGAgent",
    "GeneratorAgent",
    "CriticAgent",
    "LintCriticAgent",
    "OrchestratorAgent",
    "SummarizerAgent",
]
