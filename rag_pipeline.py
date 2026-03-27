"""
rag_pipeline.py
===============
Step 5 – The full end-to-end RAG pipeline for SystemVerilog Assertion generation.

Combines the embedding model, vector database, prompt builder, and 
cloud LLM connection into a single, efficient, unified interface. 
By maintaining these components in a stateful class, we avoid 
reloading models and indexes on every query.

Usage:
    from rag_pipeline import SVAGeneratorPipeline
    pipeline = SVAGeneratorPipeline()
    sva = pipeline.generate_assertions(my_rtl_code)
"""

import os
import sys

from dotenv import load_dotenv
from ollama import Client
from sentence_transformers import SentenceTransformer

from retriever import MODEL_NAME, load_index, retrieve
from prompt_builder import SYSTEM_PROMPT, build_prompt

# Ensure environment variables are loaded
load_dotenv()

OLLAMA_MODEL = "kimi-k2.5"

class RTLClassifier:
    """Classifies RTL structurally to pick the best RAG dataset."""
    @staticmethod
    def classify(rtl: str) -> str:
        has_sync = "posedge" in rtl or "negedge" in rtl or "<=" in rtl
        has_if = "if " in rtl or "if(" in rtl
        has_else = "else" in rtl
        has_case = "case" in rtl
        
        if has_case:
            base = "casedataset-if" if has_if else "casedataset-!if"
        else:
            base = "ifdataset-else" if has_else else "ifdataset-!else"
            
        suffix = "-synch.json" if has_sync else ".json"
        return base + suffix


class SVAGeneratorPipeline:
    """
    End-to-End RAG Pipeline for SVA Generation.
    
    Holds in memory:
      - The local sentence-transformer embedding model
      - Dict of local FAISS vector indexes & dataset records
      - The Ollama cloud API client
    """

    def __init__(self, top_k: int = 3):
        """Initializes heavy components once (models, API client). Indexes loaded on demand."""
        print("[INIT] Setting up the SVA RAG Pipeline...")
        self.top_k = top_k

        # 1. Setup Local Embedding Model
        print(f"       Loading embedding model ({MODEL_NAME})...")
        self.embed_model = SentenceTransformer(MODEL_NAME)
        self.indexes = {}

        # 2. Setup Cloud LLM Client
        print(f"       Initializing Ollama connection for '{OLLAMA_MODEL}'...")
        api_key = os.environ.get("OLLAMA_API_KEY")
        if not api_key:
            sys.exit(
                "[ERROR] OLLAMA_API_KEY environment variable is not set.\n"
                "Please add it to your .env file or export it."
            )
        self.client = Client(
            host="https://ollama.com",
            headers={"Authorization": f"Bearer {api_key}"},
        )
        print("[INIT] Pipeline ready.\n")

    def get_or_build_index(self, dataset_json_name: str) -> tuple:
        """Dynamically loads or builds a FAISS index for a specific supplemental dataset."""
        dataset_name = dataset_json_name.replace(".json", "")
        if dataset_name in self.indexes:
            return self.indexes[dataset_name]
            
        try:
            index, records = load_index(dataset_name)
            print(f"       [RAG] Loaded cached subset DB: {dataset_name} ({index.ntotal} vectors)")
        except FileNotFoundError:
            print(f"       [RAG] Cache miss. Building FAISS index for '{dataset_name}' on-the-fly...")
            from retriever import BASE_DIR, build_faiss_index, save_index, load_dataset
            dataset_path = BASE_DIR / "VERT" / "Supplimental_datasets" / dataset_json_name
            records = load_dataset(dataset_path)
            index = build_faiss_index(records, self.embed_model)
            save_index(index, records, dataset_name)
            print(f"       [RAG] Built and cached '{dataset_name}'!")
            
        self.indexes[dataset_name] = (index, records)
        return index, records

    def generate_assertions(
        self,
        rtl_code: str,
        clock_hint: str | None = None,
        synchronous_filter: str | None = None,
        stream: bool = True
    ) -> str:
        """
        Executes the full RAG pipeline for a given piece of RTL.
        """
        
        # Step 1: Classification & Index Access
        target_dataset = RTLClassifier.classify(rtl_code)
        print(f"\n[PIPELINE] Classified RTL -> Target Dataset: {target_dataset}")
        
        index, records = self.get_or_build_index(target_dataset)
        
        # Step 2: Retrieval
        print("[PIPELINE] Retrieving similar examples...")
        examples = retrieve(
            query_rtl=rtl_code,
            model=self.embed_model,
            index=index,
            records=records,
            top_k=self.top_k,
            filter_synchronous=synchronous_filter
        )

        # Step 3: Prompt Building
        print("[PIPELINE] Building CoT reasoning prompt...")
        prompt = build_prompt(
            query_rtl=rtl_code,
            retrieved_examples=examples,
            clock_hint=clock_hint
        )

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": prompt},
        ]

        # Step 4: Call LLM
        print("[PIPELINE] Calling LLM...\n")
        output_chunks = []
        if stream:
            for part in self.client.chat(OLLAMA_MODEL, messages=messages, stream=True):
                chunk = part["message"]["content"]
                print(chunk, end="", flush=True)
                output_chunks.append(chunk)
            print() # flush newline
        else:
            response = self.client.chat(OLLAMA_MODEL, messages=messages, stream=False)
            output = response["message"]["content"]
            output_chunks.append(output)

        return "".join(output_chunks)


# ─────────────────────────────────────────────────────────────
# PIPELINE DEMO / TEST
# ─────────────────────────────────────────────────────────────

def run_demo():
    print("==================================================================")
    print("  STEP 5: END-TO-END RAG PIPELINE DEMO")
    print("==================================================================")
    
    # Initialize only once!
    pipeline = SVAGeneratorPipeline(top_k=3)

    query_rtl = """\
always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
        valid_out <= 1'b0;
        data_out  <= 8'h00;
    end else if (enable) begin
        valid_out <= 1'b1;
        data_out  <= data_in + offset;
    end else begin
        valid_out <= 1'b0;
    end
end\
"""

    print("RTL REQUEST:\n")
    print(query_rtl)
    print("\n------------------------------------------------------------------")
    print("GENERATING SVA (streaming)...\n")
    
    # Execute query
    assertions = pipeline.generate_assertions(
        rtl_code=query_rtl,
        clock_hint="posedge clk",
        synchronous_filter="True" 
    )

    print("\n==================================================================")


if __name__ == "__main__":
    run_demo()
