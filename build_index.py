"""
STEP 2: Build a Retrieval System
==================================
Uses sentence-transformers to embed RTL Code snippets from VERT_withRAG.json,
stores them in a FAISS index, and retrieves the top-k most similar examples
for any new RTL input.

Architecture:
  VERT_withRAG.json  →  SentenceTransformer  →  FAISS Index
                                                      ↑
                        Query RTL  ─────────────── top-k retrieve
"""

import json
import time
import pickle
import numpy as np
import faiss
from pathlib import Path
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

# ─────────────────────────────────────────────────────────────
# PATHS
# ─────────────────────────────────────────────────────────────
BASE_DIR     = Path(__file__).parent
DATASET_PATH = BASE_DIR / "VERT" / "Supplimental_datasets" / "VERT_withRAG.json"
INDEX_PATH   = BASE_DIR / "retrieval" / "faiss.index"
META_PATH    = BASE_DIR / "retrieval" / "metadata.pkl"

# Create output directory
INDEX_PATH.parent.mkdir(exist_ok=True)


# ─────────────────────────────────────────────────────────────
# 1. LOAD DATASET
# ─────────────────────────────────────────────────────────────
def load_dataset(path: Path) -> list[dict]:
    """Load a JSONL file into a list of dicts."""
    records = []
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


# ─────────────────────────────────────────────────────────────
# 2. BUILD FAISS INDEX (run once, then cached to disk)
# ─────────────────────────────────────────────────────────────
def build_index(records: list[dict], model: SentenceTransformer) -> faiss.IndexFlatIP:
    """
    Embed all Code snippets and build a FAISS inner-product (cosine) index.

    Steps:
      1. Extract every `Code` field as a list of strings.
      2. Batch-encode with SentenceTransformer → float32 numpy array.
      3. L2-normalise vectors so inner product == cosine similarity.
      4. Add to a FAISS IndexFlatIP (exact nearest-neighbor, no compression).
    """
    print(f"  Extracting {len(records):,} code snippets ...")
    codes = [r["Code"] for r in records]

    print("  Encoding with SentenceTransformer (this may take a few minutes) ...")
    t0 = time.time()
    embeddings = model.encode(
        codes,
        batch_size=256,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True,   # cosine similarity via inner product
    )
    print(f"  Done in {time.time()-t0:.1f}s. Embedding shape: {embeddings.shape}")

    # Build FAISS index (Inner Product = cosine sim after L2-norm)
    dim   = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings.astype(np.float32))
    print(f"  FAISS index built: {index.ntotal:,} vectors, dim={dim}")
    return index


def save_index(index: faiss.IndexFlatIP, records: list[dict]) -> None:
    """Save FAISS index + record metadata to disk."""
    faiss.write_index(index, str(INDEX_PATH))
    with open(META_PATH, "wb") as f:
        pickle.dump(records, f)
    print(f"  Saved index → {INDEX_PATH}")
    print(f"  Saved metadata → {META_PATH}")


def load_cached_index() -> tuple[faiss.IndexFlatIP, list[dict]]:
    """Load previously saved index and metadata from disk."""
    print("  Loading cached FAISS index ...")
    index   = faiss.read_index(str(INDEX_PATH))
    with open(META_PATH, "rb") as f:
        records = pickle.load(f)
    print(f"  Loaded {index.ntotal:,} vectors from cache.")
    return index, records


# ─────────────────────────────────────────────────────────────
# 3. RETRIEVE TOP-K SIMILAR EXAMPLES
# ─────────────────────────────────────────────────────────────
def retrieve(
    query_rtl: str,
    model: SentenceTransformer,
    index: faiss.IndexFlatIP,
    records: list[dict],
    top_k: int = 5,
) -> list[dict]:
    """
    Given a raw RTL string, return the top-k most similar dataset records.

    Each returned record contains:
      - rank         : 1-indexed result rank
      - score        : cosine similarity score (0.0 – 1.0)
      - Code         : the matched RTL snippet
      - Assertion    : the matched ground-truth SVA
      - Synchronous  : "True" / "False"
      - Clock        : clock edge or null
    """
    # Embed the query (normalise for cosine similarity)
    query_vec = model.encode(
        [query_rtl],
        normalize_embeddings=True,
        convert_to_numpy=True,
    ).astype(np.float32)

    # Search
    scores, indices = index.search(query_vec, top_k)

    results = []
    for rank, (score, idx) in enumerate(zip(scores[0], indices[0]), start=1):
        rec = records[idx].copy()
        rec["rank"]  = rank
        rec["score"] = float(score)
        results.append(rec)
    return results


# ─────────────────────────────────────────────────────────────
# 4. PRETTY PRINT RESULTS
# ─────────────────────────────────────────────────────────────
def print_results(query: str, results: list[dict]) -> None:
    print("\n" + "═" * 70)
    print("  QUERY RTL:")
    print("═" * 70)
    print(query)

    for r in results:
        print()
        print(f"{'─'*70}")
        print(f"  RESULT #{r['rank']}  |  Score: {r['score']:.4f}  |  "
              f"Synchronous: {r['Synchronous']}  |  Clock: {r['Clock']}")
        print(f"{'─'*70}")
        print("📄 Similar RTL Code:")
        print(r["Code"])
        print()
        print("✅ Ground-Truth Assertions:")
        # Print each property on its own line
        for prop in r["Assertion"].strip().split("endproperty"):
            prop = prop.strip()
            if prop:
                print(f"  {prop} endproperty")
    print()


# ─────────────────────────────────────────────────────────────
# 5. MAIN
# ─────────────────────────────────────────────────────────────
def main():
    # ── Load embedding model ──────────────────────────────────
    # 'all-MiniLM-L6-v2' is small (80MB), fast, and great for code similarity.
    MODEL_NAME = "all-MiniLM-L6-v2"
    print(f"\n[1/4] Loading embedding model: {MODEL_NAME} ...")
    model = SentenceTransformer(MODEL_NAME)
    print(f"  Embedding dimension: {model.get_sentence_embedding_dimension()}")

    # ── Build or load index ───────────────────────────────────
    if INDEX_PATH.exists() and META_PATH.exists():
        print("\n[2/4] Cache found — skipping embedding step.")
        index, records = load_cached_index()
    else:
        print("\n[2/4] Building FAISS index (first run only) ...")
        records = load_dataset(DATASET_PATH)
        print(f"  Loaded {len(records):,} records.")
        index = build_index(records, model)
        save_index(index, records)

    print(f"\n[3/4] Index ready: {index.ntotal:,} vectors indexed.\n")

    # ── Demo queries ──────────────────────────────────────────
    print("[4/4] Running example retrievals ...\n")

    # ── Query A: combinational if/else (asynchronous) ─────────
    query_a = """
if ( enable && data_valid ) begin
    output_reg = input_data;
    if ( mode_select == 2'b01 ) begin
        result = input_data + offset;
    end
    else begin
        result = input_data;
    end
end
else begin
    output_reg = 0;
end
""".strip()

    results_a = retrieve(query_a, model, index, records, top_k=3)
    print_results(query_a, results_a)

    # ── Query B: synchronous case statement ───────────────────
    query_b = """
case ( state_reg )
   2'b00 : begin
     next_state <= IDLE;
     count <= 0;
   end
   2'b01 : begin
     next_state <= ACTIVE;
     count <= count + 1;
   end
   default : begin
     next_state <= ERROR;
   end
endcase
""".strip()

    results_b = retrieve(query_b, model, index, records, top_k=3)
    print_results(query_b, results_b)

    print("✅ Step 2 complete — retrieval system working!\n")
    print("To use in your own code:")
    print("  results = retrieve(your_rtl, model, index, records, top_k=5)")


if __name__ == "__main__":
    main()
