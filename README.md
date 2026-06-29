# Digital Workplace Assistant

A production-style RAG + Agentic AI system that answers employee questions about HR and IT policies — built to demonstrate GenAI platform engineering skills.

## Architecture

```
User Question
      │
      ▼
 ┌──────────┐     ┌─────────────────────────────────────────┐
 │ Streamlit│────▶│             Two Modes                   │
 │   UI     │     │                                         │
 └──────────┘     │  RAG Mode          Agent Mode           │
                  │  ─────────         ──────────           │
                  │  Query             ReAct Loop           │
                  │    │               Thought →            │
                  │    ▼               Action →             │
                  │  Retriever         Observation →        │
                  │    │               Repeat               │
                  │    ▼                    │               │
                  │  ChromaDB          Tools:               │
                  │  (vectors)         - DocSearch          │
                  │    │               - Calculator         │
                  │    ▼                    │               │
                  │  Llama 3.2 ◀───────────┘               │
                  │  (via Ollama)                           │
                  └─────────────────────────────────────────┘

Ingestion Pipeline (offline):
  docs/*.txt → TextLoader → RecursiveCharacterTextSplitter
             → HuggingFace Embeddings (all-MiniLM-L6-v2)
             → ChromaDB (persisted locally)
```

## Tech Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| LLM | Llama 3.2 via Ollama | Local inference — no API cost |
| Embeddings | all-MiniLM-L6-v2 (HuggingFace) | Semantic similarity |
| Vector Store | ChromaDB | Fast document retrieval |
| Orchestration | LangChain | RAG chain + ReAct agent |
| UI | Streamlit | Chat interface |

## How to Run

**Prerequisites:** Python 3.9+, [Ollama](https://ollama.com) installed

```bash
# 1. Pull the LLM
ollama pull llama3.2

# 2. Install dependencies
pip install -r requirements.txt

# 3. Ingest documents into ChromaDB
python ingest.py

# 4. Launch the app
streamlit run app.py
```

The app runs at `http://localhost:8501`.

To test the RAG chain or ReAct agent directly (terminal output with reasoning steps):

```bash
python rag.py      # RetrievalQA chain
python agent.py    # ReAct agent — prints Thought/Action/Observation loop
```

## Project Structure

```
digital-workplace-assistant/
├── docs/               # Source documents (HR + IT policy)
├── chroma_db/          # Persisted vector embeddings (auto-created)
├── ingest.py           # Document → embeddings → ChromaDB
├── rag.py              # RetrievalQA chain
├── agent.py            # ReAct agent with DocSearch + Calculator tools
├── app.py              # Streamlit UI
└── requirements.txt
```

## How This Maps to GenAI Platform Engineering

| Concept | This Project | Production Scale |
|---------|-------------|-----------------|
| **Transformer Architecture** | Llama 3.2 + MiniLM are both Transformers (encoder for embeddings, decoder for generation) | Same architecture, larger models (GPT-4, Claude) |
| **Neural Architecture** | Attention mechanism enables semantic search and coherent generation | Multi-head attention, positional encoding |
| **Hosting LLM Models** | Ollama serves Llama 3.2 locally via REST API | vLLM / TGI on GPU clusters; model quantization (GGUF) |
| **Agentic Architecture** | ReAct loop: Reason → Act (tool call) → Observe → Repeat | Multi-agent orchestration, tool registries, guardrails |
| **Fine-Tuning LLMs** | RAG used instead — updates knowledge without retraining | LoRA/QLoRA for domain adaptation when RAG isn't enough |

## RAG vs Fine-Tuning — Design Decision

This project uses **RAG** rather than fine-tuning because:

- **Knowledge changes frequently** — HR/IT policies update quarterly; retraining is expensive
- **Source attribution matters** — RAG shows exactly which document answered the question
- **No labeled data** — fine-tuning requires thousands of (question, answer) pairs

**When fine-tuning wins:** teaching the model a new *style* (formal tone, specific format) or *behavior* (domain-specific reasoning) that doesn't change with data updates. Technique: **LoRA** (Low-Rank Adaptation) — freezes base model weights, trains small adapter matrices (~1% of parameters).

## Sample Questions to Try

**RAG mode:**
- "How many days of annual leave do employees get?"
- "What is the password policy?"
- "Can I install software on my work laptop?"

**Agent mode (combines reasoning + tools):**
- "If I get 20 leave days per year, how many is that per month?"
- "What should I do if I find a phishing email, and how quickly must I report it?"
- "How many sick days do I get, and what's that as a percentage of working days in a year?"

--------------------




