"""
retriever.py
============
Shared retrieval module.

Provides functions for loading, building, and querying the FAISS index.
Designed to be imported by other scripts (prompt_builder, app, etc.)
without containing any main() logic.
"""

import json
import pickle
import time
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

# ─────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────
BASE_DIR     = Path(__file__).parent
DATASET_PATH = BASE_DIR / "VERT" / "Supplimental_datasets" / "VERT_withRAG.json"
INDEX_PATH   = BASE_DIR / "retrieval" / "faiss.index"
META_PATH    = BASE_DIR / "retrieval" / "metadata.pkl"
MODEL_NAME   = "all-MiniLM-L6-v2"


# ─────────────────────────────────────────────────────────────
# DATASET
# ─────────────────────────────────────────────────────────────
def load_dataset(path: Path = DATASET_PATH) -> list[dict]:
    """Load a JSONL file into a list of record dicts."""
    records = []
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


# ─────────────────────────────────────────────────────────────
# INDEX: BUILD + SAVE
# ─────────────────────────────────────────────────────────────
def build_faiss_index(
    records: list[dict],
    model: SentenceTransformer,
) -> faiss.IndexFlatIP:
    """
    Encode all Code snippets and return a FAISS cosine-similarity index.

    Uses L2-normalised embeddings + IndexFlatIP so that inner product
    equals cosine similarity. Exact search (no approximation).
    """
    codes = [r["Code"] for r in records]
    print(f"  Encoding {len(codes):,} RTL snippets ...")
    t0 = time.time()
    embeddings = model.encode(
        codes,
        batch_size=256,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )
    print(f"  Encoded in {time.time() - t0:.1f}s  |  shape: {embeddings.shape}")
    dim   = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings.astype(np.float32))
    return index


def save_index(index: faiss.IndexFlatIP, records: list[dict]) -> None:
    """Persist FAISS index and record metadata to disk."""
    INDEX_PATH.parent.mkdir(exist_ok=True)
    faiss.write_index(index, str(INDEX_PATH))
    with open(META_PATH, "wb") as f:
        pickle.dump(records, f)


# ─────────────────────────────────────────────────────────────
# INDEX: LOAD FROM CACHE
# ─────────────────────────────────────────────────────────────
def load_index() -> tuple[faiss.IndexFlatIP, list[dict]]:
    """Load the pre-built FAISS index and metadata from disk."""
    if not INDEX_PATH.exists() or not META_PATH.exists():
        raise FileNotFoundError(
            "FAISS index not found. Run `python build_index.py` first."
        )
    index = faiss.read_index(str(INDEX_PATH))
    with open(META_PATH, "rb") as f:
        records = pickle.load(f)
    return index, records


def index_is_cached() -> bool:
    """Return True if a pre-built index exists on disk."""
    return INDEX_PATH.exists() and META_PATH.exists()


# ─────────────────────────────────────────────────────────────
# RETRIEVE
# ─────────────────────────────────────────────────────────────
def retrieve(
    query_rtl: str,
    model: SentenceTransformer,
    index: faiss.IndexFlatIP,
    records: list[dict],
    top_k: int = 5,
    filter_synchronous: str | None = None,
) -> list[dict]:
    """
    Find the top-k most similar RTL examples to query_rtl.

    Args:
        query_rtl:          Raw SystemVerilog RTL string to search for.
        model:              Loaded SentenceTransformer model.
        index:              FAISS index containing all embeddings.
        records:            Original dataset records (parallel to index).
        top_k:              Number of results to return.
        filter_synchronous: Optional "True" or "False" to restrict results
                            to synchronous or asynchronous examples only.
                            Pass None to return both.

    Returns:
        List of dicts, each with: Code, Assertion, Synchronous, Clock,
        rank (1-indexed), score (cosine similarity 0-1).
    """
    query_vec = model.encode(
        [query_rtl],
        normalize_embeddings=True,
        convert_to_numpy=True,
    ).astype(np.float32)

    # Retrieve more candidates when filtering so we still get top_k after
    fetch_k = top_k * 4 if filter_synchronous else top_k
    scores, indices = index.search(query_vec, fetch_k)

    results = []
    rank = 1
    for score, idx in zip(scores[0], indices[0]):
        rec = records[idx]
        if filter_synchronous and rec["Synchronous"] != filter_synchronous:
            continue
        results.append({**rec, "rank": rank, "score": float(score)})
        rank += 1
        if len(results) == top_k:
            break

    return results
