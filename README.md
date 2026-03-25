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

## Project Structure

```
verigen/
├── venv/                   # Python virtual environment (not committed)
├── requirements.txt        # Python dependencies
├── README.md
│
├── explore_dataset.py      # Load and inspect VERT_withRAG.json
├── build_index.py          # Build FAISS vector index for retrieval
│
├── retrieval/              # Auto-generated (not committed)
│   ├── faiss.index         # Embedded vector index
│   └── metadata.pkl        # Record metadata cache
│
└── VERT/                   # Dataset directory
    ├── VERT/
    │   └── VERT.json
    └── Supplimental_datasets/
        ├── VERT_withRAG.json
        ├── ifdataset-else.json
        ├── ifdataset-!else.json
        ├── casedataset-if.json
        └── ...
```

---

## Setup

```bash
# 1. Clone the repo
git clone <your-repo-url>
cd verigen

# 2. Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate     # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt
```

---

## Usage

### Explore the dataset

```bash
python explore_dataset.py
```

Prints dataset stats and 5 sample RTL/assertion pairs so you can understand the data.

### Build the retrieval index

```bash
python build_index.py
```

Embeds all 20,000 RTL snippets using `sentence-transformers` and saves a FAISS index to `retrieval/`. This runs once and takes about 90 seconds. After that, results are instant.

---

## Progress

| Step | Description | Status |
|------|-------------|--------|
| 1 | Load and explore VERT_withRAG.json | Done |
| 2 | Build FAISS retrieval index with sentence-transformers | Done |
| 3 | LLM prompt layer with retrieved few-shot examples | Next |
| 4 | Web application UI | Planned |
| 5 | Fine-tuning / evaluation | Planned |

---

## Dataset

The VERT dataset contains:

- 20,000 total records (10,000 synchronous, 10,000 asynchronous)
- Each record has: RTL code, ground-truth SVA assertions, synchronous flag, clock edge
- Covers `if/else`, `case`, nested logic, and timing-aware patterns
- Sourced from the paper: [VERT: A SystemVerilog Assertion Dataset to Improve Hardware Verification with LLMs](https://github.com/AnandMenon12/VERT)

---

## Dependencies

- `sentence-transformers` for embedding RTL code
- `faiss-cpu` for fast vector similarity search
- `numpy`, `tqdm` for data handling and progress display