# VERIGEN: Verification Assertion Generator

VERIGEN is a Retrieval-Augmented Generation (RAG) application that takes SystemVerilog RTL code as input and automatically generates SystemVerilog Assertions (SVAs).

It uses the [VERT Dataset](https://github.com/AnandMenon12/VERT), a collection of 20,000 RTL code snippets paired with hand-crafted assertions.

---

## What This Does

You paste in a block of RTL (like an `if/else` or `case` block), and the system:

1. Finds the most similar RTL examples from the dataset
2. Uses those examples as context for an LLM
3. Generates correct and complete SVA assertions for your code

---

## Quick Start

### 1. Prerequisites
- Python 3.10+
- [Ollama](https://ollama.com) installed and running.
- An Ollama API Key (if using cloud models).

### 2. Setup
```bash
# Clone the repository
git clone https://github.com/bvsnithin/verigen.git
cd verigen

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Setup API Key
cp .env.example .env
# Edit .env and paste your OLLAMA_API_KEY
```

### 3. Generate Assertions
Run the main pipeline demo:
```bash
python main.py
```

---

## Project Structure

Verified and organized for modularity:

```text
verigen/
├── data/                    # All project data and search indexes
│   ├── VERT/                # Source RTL/SVA dataset
│   └── retrieval/           # Cached FAISS vector indexes
├── src/                     # Core library logic
│   ├── retriever.py         # FAISS management and search
│   ├── prompt_builder.py    # Few-shot prompt engineering
│   ├── classifier.py        # RTL structural analysis
│   └── pipeline.py          # Unified RAG generation engine
├── scripts/                 # Utility and maintenance scripts
│   ├── build_index.py       # One-time FAISS index builder
│   └── explore_dataset.py   # Dataset analysis tool
├── main.py                  # Primary application entry point
├── .env                     # Environment variables (API keys)
└── requirements.txt         # Project dependencies
```

---

## How it Works

VeriGen uses a multi-stage **agentic pipeline** to ensure high-quality SVA generation:

1.  **Structural Classification**: The `RTLClassifier` analyzes your input code to determine timing (synchronous/asynchronous) and branching logic (`if`, `else`, `case`).
2.  **Targeted Retrieval**: Instead of searching a massive database, we dynamically select the best **supplemental dataset** matching your RTL structure and retrieve the top-3 most similar examples using FAISS.
3.  **Chain-of-Thought (CoT) Reasoning**: We inject few-shot examples into the LLM (`kimi-k2.5`) and demand a structured `<analysis>` block before any code is written. The model must explain the timing, conditions, and branches it identified.
4.  **Structured Output**: Every response contains:
    *   **Assertions**: Formatted SystemVerilog property blocks.
    *   **Explanation**: A clear breakdown of what is being checked.
    *   **Edge Cases**: Verification of resets, default states, and mutual exclusivity.

---

## Maintenance Scripts

### Build Search Indexes
If you add new data or want to refresh the cache:
```bash
python scripts/build_index.py
```

### Dataset Exploration
To see samples and statistics of the underlying VERT dataset:
```bash
python scripts/explore_dataset.py
```

---

## Dataset Reference
The system is built on the [VERT Dataset](https://github.com/AnandMenon12/VERT), containing 20,000 RTL/SVA pairs across synchronous and asynchronous domains.