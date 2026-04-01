"""
build_index.py
==============
One-time script to build and cache the FAISS retrieval index.

Run this once before using prompt_builder.py or the web app.
The index is saved to retrieval/ and loaded from cache on subsequent runs.

Usage:
    source venv/bin/activate
    python build_index.py
"""

import sys
from pathlib import Path
from sentence_transformers import SentenceTransformer

# Add the project root to sys.path so we can import from src
ROOT_DIR = Path(__file__).parent.parent
sys.path.append(str(ROOT_DIR))

from src.retriever import (
    MODEL_NAME,
    build_faiss_index,
    index_is_cached,
    load_dataset,
    load_index,
    retrieve,
    save_index,
)


def print_results(query: str, results: list[dict]) -> None:
    """Pretty-print retrieved RTL/assertion pairs."""
    print("\n" + "=" * 70)
    print("  QUERY RTL:")
    print("=" * 70)
    print(query)

    for r in results:
        print()
        print(f"  RESULT #{r['rank']}  |  Score: {r['score']:.4f}  |  "
              f"Synchronous: {r['Synchronous']}  |  Clock: {r['Clock']}")
        print("-" * 70)
        print("RTL Code:")
        print(r["Code"])
        print()
        print("Ground-Truth Assertions:")
        for prop in r["Assertion"].strip().split("endproperty"):
            prop = prop.strip()
            if prop:
                print(f"  {prop} endproperty")
    print()


def main():
    print(f"\n[1/3] Loading embedding model: {MODEL_NAME} ...")
    model = SentenceTransformer(MODEL_NAME)
    print(f"  Embedding dimension: {model.get_sentence_embedding_dimension()}")

    DATASET_NAME = "VERT_withRAG"

    if index_is_cached(DATASET_NAME):
        print(f"\n[2/3] Cache found for '{DATASET_NAME}'. Loading index from disk ...")
        index, records = load_index(DATASET_NAME)
        print(f"  Loaded {index.ntotal:,} vectors.")
    else:
        print(f"\n[2/3] No cache found for '{DATASET_NAME}'. Building FAISS index ...")
        records = load_dataset()
        print(f"  Dataset: {len(records):,} records")
        index = build_faiss_index(records, model)
        save_index(index, records, DATASET_NAME)
        print(f"  Saved to retrieval/{DATASET_NAME}.index")

    print(f"\n[3/3] Index ready: {index.ntotal:,} vectors. Running demo queries ...\n")

    # Demo query A: combinational if/else
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

    # Demo query B: synchronous case statement
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

    print("Done. To query programmatically:")
    print("  from src.retriever import retrieve, load_index")


if __name__ == "__main__":
    main()
