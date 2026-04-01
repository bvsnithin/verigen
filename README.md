# VERIGEN: Verification Assertion Generator

VERIGEN is a Retrieval-Augmented Generation (RAG) application that takes SystemVerilog RTL code as input and automatically generates SystemVerilog Assertions (SVAs).

It leverages the [VERT Dataset](https://github.com/AnandMenon12/VERT) (containing 20,000 RTL/SVA pairs) and a sophisticated CoT reasoning pipeline to analyze logic schemas and generate high-quality verifications. To match the backend's power, VeriGen now features a premium, responsive glassmorphism React frontend.

---

## Architecture

VeriGen is structured as a monorepo consisting of two main parts:

1. **`backend/` (FastAPI + Python)**
   * **Vector Database:** Manages a local FAISS semantic search index.
   * **LLM Integration:** Connects to local or cloud LLMs for AI generation.
   * **Streaming API:** Exposes a `/generate_assertions/stream` endpoint using Server-Sent Events (SSE) to emit real-time pipeline status to the client.
   * **Zero-Latency Startup:** Loads the FAISS index into memory at application startup to eliminate cold-start latency.

2. **`frontend/` (React + Vite + Tailwind CSS)**
   * **Professional UI:** Designed with a clean, typography-driven black-and-white aesthetic (Funnel Display & Inter fonts).
   * **Dual-Mode Input:** Accepts both SystemVerilog RTL syntax or plain English structural descriptions.
   * **Live Progress Tracker:** Visualizes the backend's internal pipeline stages (Classify → Retrieve → Prompt → Generate) via real-time SSE updates.
   * **Rich Output:** Formats the LLM output using Markdown, complete with syntax-highlighted JetBrains Mono code blocks and clean separation of SVAs and explanations.

---

## Quick Start

You will need **two terminal windows** to run this application: one for the backend API, and one for the frontend UI.

### Prerequisites

* Python 3.10+
* Node.js 18+ and `npm`
* [Ollama](https://ollama.com) configured, or an appropriate API Key set in `.env`.

### 1. Build the Search Index & Start the Backend

Open your first terminal:

```bash
cd backend

# Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate

# Install the dependencies
pip install -r requirements.txt

# (One-time only) Build the FAISS cache from the VERT dataset
python scripts/build_index.py

# Start the FastAPI server
python api.py
```
*The backend API will run on **http://localhost:8000**.*

### 2. Start the Frontend UI

Open your second terminal:

```bash
cd frontend

# Install Node dependencies
npm install

# Start the Vite development server
npm run dev
```
*The frontend interface will run on **http://localhost:5173**.*

---

## Project Structure

```text
verigen/
├── backend/                 # Python FastAPI Backend
│   ├── api.py               # Main FastAPI Application & Endpoint
│   ├── src/                 # Core logic (Pipeline, Classifier, Retriever, Prompts)
│   ├── data/                # VERT Dataset & FAISS Vector Indexes
│   ├── scripts/             # Maintenance scripts (Index building, Dataset exploration)
│   ├── requirements.txt     # Python Dependencies
│   └── .env                 # API Keys
│
├── frontend/                # React Vite Frontend
│   ├── src/                 # React Components, Hooks, and App Logic
│   ├── public/              # Static Assets
│   ├── package.json         # Node Dependencies
│   ├── tailwind.config.js   # Tailwind Theme Configuration
│   └── vite.config.js       # Vite Build Configuration
│
└── README.md                # This Documentation
```

---

## How it Works

VeriGen utilizes an **Agentic Pipeline** for optimal generation accuracy:

1. **Classifying the Request**: The backend determines if the input code is Synchronous or Asynchronous, identifying critical edge case signals (e.g., `reset`, `enable`).
2. **Context Retrieval**: Utilizing a pre-built FAISS vector index, VeriGen embeds your query using `sentence-transformers` and retrieves the most semantically similar RTL/SVA pairs from the VERT database.
3. **Chain-of-Thought (CoT)**: The retrieved examples are injected into a dynamic prompt. The LLM is forced to analyze branching and timing constraints *before* writing any code.
4. **Streaming Execution**: The pipeline stages stream status events back to the frontend using an asynchronous FastAPI generator.
5. **Post-Processing**: The frontend strips internal reasoning tokens (like `<analysis>...</analysis>`) and cleanly renders the final assertions and descriptions.