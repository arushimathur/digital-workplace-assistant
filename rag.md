# Understanding `rag.py` in Simple Language

The purpose of `rag.py` is to **load the vector database created by `ingest.py`, retrieve the most relevant document chunks for a user's question, and use an LLM (Llama 3.2) to generate an answer based on those retrieved documents.**

This process is called **Retrieval-Augmented Generation (RAG)**.

---

# Step 1: Replace the Default SQLite Library

```python
__import__("pysqlite3")
import sys
sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")
```

These lines replace Python's default `sqlite3` library with `pysqlite3`.

### Why?

ChromaDB stores its vector database using SQLite. On some systems, the default SQLite version is too old. Using `pysqlite3` ensures ChromaDB works correctly.

---

# Step 2: Import Required Libraries

```python
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_ollama import OllamaLLM
from langchain.chains import RetrievalQA
```

These libraries provide the main components of the RAG pipeline.

### HuggingFaceEmbeddings

Loads the same embedding model used during ingestion.

Its job is to convert the user's question into a vector so it can be compared with stored document vectors.

---

### Chroma

Loads the existing vector database (`chroma_db`) created by `ingest.py`.

---

### OllamaLLM

Connects to a locally running Llama model using Ollama.

```python
llm = OllamaLLM(model="llama3.2")
```

This model generates the final answer.

---

### RetrievalQA

This is a ready-made LangChain chain that combines:

* Document retrieval
* LLM prompting
* Answer generation

into one workflow.

---

# Step 3: Configuration

```python
CHROMA_DIR = "chroma_db"
EMBED_MODEL = "all-MiniLM-L6-v2"
```

These settings match the ones used in `ingest.py`.

* `CHROMA_DIR` points to the saved vector database.
* `EMBED_MODEL` specifies the embedding model used to encode the query.

Using the same embedding model is important because both document chunks and user queries must be represented in the same vector space for similarity search to work correctly.

---

# Step 4: Define the RAG Pipeline

```python
def load_rag_chain():
```

This function creates and returns the complete Retrieval-Augmented Generation pipeline.

---

## Load the Embedding Model

```python
embeddings = HuggingFaceEmbeddings(model_name=EMBED_MODEL)
```

When the user asks a question, this model converts the question into a vector.

Example:

Question:

```
How many annual leaves do employees get?
```

↓

Embedding Model

↓

Vector

```
[0.21, -0.55, 0.82, ...]
```

---

## Load the Vector Database

```python
vectorstore = Chroma(
    persist_directory=CHROMA_DIR,
    embedding_function=embeddings
)
```

This opens the existing Chroma database instead of creating a new one.

The database already contains:

* Document chunks
* Their embeddings

created during the ingestion process.

---

## Create a Retriever

```python
retriever = vectorstore.as_retriever(
    search_kwargs={"k": 3}
)
```

A retriever searches the vector database.

Here,

```python
k = 3
```

means:

> Return the **3 most relevant document chunks** for each user question.

Example:

User asks:

```
How many annual leaves do employees get?
```

Retriever returns:

* Chunk 12
* Chunk 15
* Chunk 17

These are the three chunks most similar to the question.

---

## Load the LLM

```python
llm = OllamaLLM(model="llama3.2")
```

This loads the Llama 3.2 model running locally through Ollama.

The LLM does **not** search the documents itself. Instead, it receives the retrieved document chunks as context and generates an answer based on them.

---

## Create the RetrievalQA Chain

```python
chain = RetrievalQA.from_chain_type(
    llm=llm,
    retriever=retriever,
    return_source_documents=True,
)
```

This connects all the components into one pipeline.

The workflow is:

1. User asks a question.
2. Convert the question into an embedding.
3. Search Chroma for the top 3 matching chunks.
4. Send those chunks to Llama 3.2.
5. Llama generates an answer using the retrieved context.
6. Return both the answer and the source documents.

---

# Step 5: Return the Chain

```python
return chain
```

The function returns the fully configured RAG pipeline so it can be used elsewhere.

---

# Step 6: Run the Program

```python
if __name__ == "__main__":
```

This block runs only when the file is executed directly.

First, it loads the RAG chain:

```python
chain = load_rag_chain()
```

---

# Step 7: Define Sample Questions

```python
questions = [
    "How many days of annual leave do employees get?",
    "What should I do if I suspect a security breach?",
    "Can I install software on my work laptop?",
]
```

These are example questions used to test the system.

---

# Step 8: Ask Each Question

```python
for q in questions:
```

The program loops through each question one at a time.

---

## Print the Question

```python
print(f"\nQ: {q}")
```

Example output:

```
Q: How many days of annual leave do employees get?
```

---

## Query the RAG Chain

```python
result = chain.invoke({"query": q})
```

This triggers the entire RAG process:

```
User Question
       │
       ▼
Embedding Model
       │
       ▼
Vector Search (Chroma)
       │
       ▼
Top 3 Relevant Chunks
       │
       ▼
Llama 3.2
       │
       ▼
Generated Answer
```

The result is a dictionary containing:

* `result["result"]` → the generated answer
* `result["source_documents"]` → the retrieved document chunks

---

## Print the Answer

```python
print(f"A: {result['result']}")
```

Example:

```
A: Employees receive 20 days of annual leave each year.
```

---

## Print the Source Files

```python
print(
    f"Sources: {[d.metadata.get('source', '') for d in result['source_documents']]}"
)
```

This displays which document(s) were used to answer the question.

Example:

```
Sources:
['docs/hr_policy.txt']
```

Showing the source documents makes the answer more transparent and easier to verify.

---

# Overall Workflow

```
User Question
      │
      ▼
Convert Question to Embedding
      │
      ▼
Search Chroma Vector Database
      │
      ▼
Retrieve Top 3 Relevant Chunks
      │
      ▼
Send Chunks + Question to Llama 3.2
      │
      ▼
Generate Final Answer
      │
      ▼
Display Answer + Source Documents
```

# Summary

`rag.py` loads the vector database created by `ingest.py`, converts the user's question into an embedding, retrieves the three most relevant document chunks from ChromaDB, sends those chunks to the Llama 3.2 model through Ollama, generates an answer based on the retrieved information, and finally displays both the answer and the source documents used to produce it.

