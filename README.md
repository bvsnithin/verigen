# VERIGEN: Verification Assertion Generator

VERIGEN is a Retrieval-Augmented Generation (RAG) application that takes SystemVerilog RTL code as input and automatically generates SystemVerilog Assertions (SVAs).

It leverages the [VERT Dataset](https://github.com/AnandMenon12/VERT) (containing 20,000 RTL/SVA pairs) and a sophisticated CoT reasoning pipeline to analyze logic schemas and generate high-quality verifications. To match the backend's power, VeriGen now features a premium, responsive glassmorphism React frontend.

---

## Architecture

VeriGen is structured as a monorepo consisting of two main parts:

1. **`backend/` (FastAPI + RAG Pipeline)**
   * Manages the retrieval index (FAISS), embedded datasets, and local/cloud LLMs.
   * Exposes a `/generate_assertions` POST endpoint.

2. **`frontend/` (React + Vite + Tailwind CSS)**
   * A premium web interface with smooth Framer Motion animations.
   * Allows dual-mode input (RTL syntax or clean Natural Language specs).

---

## Quick Start

You will need **two terminal windows** to run this application: one for the backend API, and one for the frontend UI.

### Prerequisites

* Python 3.10+
* Node.js 18+ and `npm`
* [Ollama](https://ollama.com) installed and running locally, or an appropriate API Key set.

### 1. Start the Backend API

Open your first terminal and navigate to the project directory:

```bash
cd backend

# Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate

# Install the dependencies
pip install -r requirements.txt

# Configure your Environment Variables
cp .env.example .env
# Open .env and add your OLLAMA_API_KEY (if needed)

# Start the FastAPI server
python api.py
```
*The backend API will run on **http://localhost:8000/generate_assertions**.*

### 2. Start the Frontend UI

Open your second terminal and navigate to the project directory:

```bash
cd frontend

# Install Node dependencies
npm install

# Start the Vite development server
npm run dev
```
*The frontend interface will run on **http://localhost:5173**. Open this URL in your browser to use VeriGen.*

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

1. **Classifying the Request**: Determining if the input code is Synchronous or Asynchronous, identifying edge case signals (`reset`, `enable`).
2. **Context Retrieval**: Leveraging a FAISS semantic search index, VeriGen cross-references your RTL against the closest matching examples in the VERT database.
3. **Chain-of-Thought (CoT)**: Using strict few-shot prompting, the model analyzes branching and timing constraints *before* writing any code.
4. **Structured SVA Output**: Generating robust assertion properties complemented by a plain-language explanation.

---

## Maintenance & Dataset Scripts

The `backend/scripts/` directory includes tools for maintaining the RAG search indexes:

* **Build the Search Index** (if dataset changes):
  ```bash
  cd backend
  python scripts/build_index.py
  ```
* **Explore the Dataset**:
  ```bash
  cd backend
  python scripts/explore_dataset.py
  ```