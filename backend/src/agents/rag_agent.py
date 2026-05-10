"""
agents/rag_agent.py
===================
RAG Agent — embeds the user query and retrieves the top-k most relevant
SystemVerilog examples from the FAISS knowledge base.

No LLM call is made here; this agent is purely vector-search based.
"""

from __future__ import annotations

from sentence_transformers import SentenceTransformer

from ..classifier import RTLClassifier
from ..retriever import MODEL_NAME, load_index, build_faiss_index, save_index, load_dataset, ROOT_DIR
from .state import PipelineState


class RAGAgent:
    """
    Responsible for:
      1. Classifying the input to select the right dataset.
      2. Loading or building the FAISS index on demand.
      3. Embedding the query and retrieving top-k examples.
    """

    def __init__(self, top_k: int = 3):
        self.top_k = top_k
        print(f"[RAGAgent] Loading embedding model ({MODEL_NAME})...")
        self.embed_model = SentenceTransformer(MODEL_NAME)
        self._index_cache: dict[str, tuple] = {}
        print("[RAGAgent] Ready.")

    # ──────────────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────────────

    def run(self, state: PipelineState) -> PipelineState:
        """Execute the full retrieval step and populate state fields."""
        print(f"\n[RAGAgent] Running (input_type={state.input_type})...")

        # 1. Select dataset
        if state.input_type == "rtl":
            state.target_dataset = RTLClassifier.classify(state.content)
        else:
            state.target_dataset = "VERT_withRAG.json"
        print(f"[RAGAgent] Target dataset: {state.target_dataset}")

        # 2. Load / build index
        index, records = self._get_or_build_index(state.target_dataset)

        # 3. Retrieve
        from ..retriever import retrieve
        state.retrieved_examples = retrieve(
            query_rtl=state.content,
            model=self.embed_model,
            index=index,
            records=records,
            top_k=self.top_k,
            filter_synchronous=state.synchronous_filter,
        )
        print(f"[RAGAgent] Retrieved {len(state.retrieved_examples)} examples.")
        return state

    def get_embed_model(self) -> SentenceTransformer:
        """Return the embed model (shared with pipeline for efficiency)."""
        return self.embed_model

    def preload_index(self, dataset_json_name: str) -> None:
        """Pre-warm the index cache at startup."""
        self._get_or_build_index(dataset_json_name)

    # ──────────────────────────────────────────────────────────────────────────
    # Private helpers
    # ──────────────────────────────────────────────────────────────────────────

    def _get_or_build_index(self, dataset_json_name: str) -> tuple:
        dataset_name = dataset_json_name.replace(".json", "")
        if dataset_name in self._index_cache:
            return self._index_cache[dataset_name]

        try:
            index, records = load_index(dataset_name)
            print(f"[RAGAgent] Loaded cached index: {dataset_name} ({index.ntotal} vectors)")
        except FileNotFoundError:
            print(f"[RAGAgent] Cache miss — building FAISS index for '{dataset_name}'...")
            dataset_path = (
                ROOT_DIR / "data" / "VERT" / "Supplimental_datasets" / dataset_json_name
            )
            records = load_dataset(dataset_path)
            index = build_faiss_index(records, self.embed_model)
            save_index(index, records, dataset_name)
            print(f"[RAGAgent] Built and cached '{dataset_name}'.")

        self._index_cache[dataset_name] = (index, records)
        return index, records
