"""
STEP 1: Load and Explore VERT_withRAG.json
==========================================
This script loads the VERT_withRAG dataset, prints sample records,
and explains the structure of each field.
"""

import json
from pathlib import Path

# ─────────────────────────────────────────────
# 1. LOAD THE DATASET
# ─────────────────────────────────────────────
DATASET_PATH = Path(__file__).parent / "VERT" / "Supplimental_datasets" / "VERT_withRAG.json"

print("Loading VERT_withRAG.json ...")

records = []
with open(DATASET_PATH, "r") as f:
    for line in f:
        line = line.strip()
        if line:
            records.append(json.loads(line))

print(f"✅ Loaded {len(records):,} records\n")

# ─────────────────────────────────────────────
# 2. DATASET OVERVIEW
# ─────────────────────────────────────────────
print("=" * 60)
print("DATASET OVERVIEW")
print("=" * 60)
print(f"  Total samples  : {len(records):,}")
print(f"  Fields per record: {list(records[0].keys())}")

sync_count  = sum(1 for r in records if r.get("Synchronous") == "True")
async_count = sum(1 for r in records if r.get("Synchronous") == "False")
print(f"  Synchronous    : {sync_count:,}  ({sync_count/len(records)*100:.1f}%)")
print(f"  Asynchronous   : {async_count:,}  ({async_count/len(records)*100:.1f}%)")

clocks = [r["Clock"] for r in records if r.get("Clock")]
unique_clocks = set(clocks)
print(f"  Unique clocks  : {len(unique_clocks)} (e.g. {list(unique_clocks)[:3]})")

# ─────────────────────────────────────────────
# 3. FIELD EXPLANATIONS
# ─────────────────────────────────────────────
print()
print("=" * 60)
print("FIELD DESCRIPTIONS")
print("=" * 60)
print("""
  Code        → SystemVerilog RTL snippet (input to the model).
                Contains if/else, case statements, signal assignments.
                This is what we give the LLM to generate assertions for.

  Assertion   → One or more SVA property blocks (ground truth / target).
                Uses the |-> (implication) operator to express conditions.
                Multiple properties cover every branch of the RTL logic.

  Synchronous → "True"  = assertions are clock-gated (timing-aware).
                "False" = combinational / purely logical assertions.

  Clock       → The clock edge used in @(posedge / negedge ...) 
                Only present when Synchronous == "True", else null.
""")

# ─────────────────────────────────────────────
# 4. PRINT 5 SAMPLES
# ─────────────────────────────────────────────
# Pick 2 async + 2 sync + 1 case-based for variety
async_samples = [r for r in records if r["Synchronous"] == "False"][:2]
sync_samples  = [r for r in records if r["Synchronous"] == "True"][:3]
five_samples  = async_samples + sync_samples

for i, sample in enumerate(five_samples, 1):
    print("=" * 60)
    print(f"  SAMPLE #{i}  [Synchronous={sample['Synchronous']}, Clock={sample['Clock']}]")
    print("=" * 60)
    print("📄 RTL Code:")
    print(sample["Code"])
    print()
    print("✅ Assertions:")
    # Pretty-print each assertion property on its own line
    for prop in sample["Assertion"].strip().split("endproperty"):
        prop = prop.strip()
        if prop:
            print(f"  {prop} endproperty")
    print()

# ─────────────────────────────────────────────
# 5. IDENTIFY FIELDS USEFUL FOR RAG RETRIEVAL
# ─────────────────────────────────────────────
print("=" * 60)
print("FIELDS USEFUL FOR RAG RETRIEVAL")
print("=" * 60)
print("""
  PRIMARY (embed these for retrieval):
  ──────────────────────────────────────
  • Code       → Embed as the "query document".
                 When a user provides RTL, retrieve similar Code snippets.

  • Assertion  → The "answer" to retrieve alongside matching Code.

  METADATA FILTERS (use to narrow retrieval):
  ──────────────────────────────────────────
  • Synchronous → Filter by "True"/"False" based on user's RTL type.
  • Clock        → Match clock domain if the user's design specifies one.

  RAG STRATEGY:
  ─────────────
  1. Embed every Code snippet → store in a vector index (e.g. FAISS/ChromaDB).
  2. At query time: embed user's RTL → find top-k similar Code snippets.
  3. Retrieve paired Assertions → inject as few-shot examples into the prompt.
  4. Filter by Synchronous/Clock to ensure timing-compatible examples.
""")

print("✅ Step 1 complete — dataset fully explored.\n")
