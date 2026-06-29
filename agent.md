# Understanding `agent.py` in Simple Language

This script builds an **AI Agent** using LangChain. Unlike `rag.py`, which always retrieves documents before answering, this agent can **decide which tool to use** based on the user's question.

For example:

* If the user asks about HR policies → use **DocSearch**.
* If the user asks a math question → use the **Calculator**.
* The agent chooses the correct tool automatically.

---

# Step 1: Replace SQLite

```python
__import__("pysqlite3")
import sys
sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")
```

These lines replace Python's default SQLite library with `pysqlite3`.

### Why?

ChromaDB stores vectors using SQLite. Some systems have an older SQLite version, so `pysqlite3` ensures compatibility.

---

# Step 2: Import Required Libraries

```python
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_ollama import OllamaLLM
from langchain.tools import Tool
from langchain.agents import AgentType, initialize_agent
```

These libraries provide the main components:

* **HuggingFaceEmbeddings** – Converts text into embeddings.
* **Chroma** – Loads the vector database.
* **OllamaLLM** – Connects to the local Llama 3.2 model.
* **Tool** – Creates tools the agent can use.
* **initialize_agent** – Builds the AI agent.

---

# Step 3: Configuration

```python
CHROMA_DIR = "chroma_db"
EMBED_MODEL = "all-MiniLM-L6-v2"
```

These values match those used in `ingest.py`.

* `CHROMA_DIR` → Location of the vector database.
* `EMBED_MODEL` → Embedding model used for document search.

---

# Step 4: Build the Agent

```python
def build_agent():
```

This function creates and returns the complete AI agent.

---

## Load the Embedding Model

```python
embeddings = HuggingFaceEmbeddings(model_name=EMBED_MODEL)
```

This converts user questions into vectors so they can be compared with stored document vectors.

---

## Load ChromaDB

```python
vectorstore = Chroma(
    persist_directory=CHROMA_DIR,
    embedding_function=embeddings
)
```

This loads the vector database created during ingestion.

---

## Create a Retriever

```python
retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
```

The retriever searches the database and returns the **3 most relevant document chunks**.

---

# Step 5: Create the DocSearch Tool

```python
def doc_search(query: str) -> str:
```

This function searches company documents.

### Step 1

```python
docs = retriever.invoke(query)
```

The retriever searches ChromaDB.

Example:

Question:

```
How many annual leave days do employees get?
```

↓

Returns

* Chunk 1
* Chunk 2
* Chunk 3

---

### Step 2

```python
if not docs:
    return "No relevant documents found."
```

If nothing matches, return a message.

---

### Step 3

```python
return "\n\n".join(
    f"[Source: {d.metadata.get('source', 'unknown')}]\n{d.page_content}"
    for d in docs
)
```

This combines all retrieved chunks into one string.

Example:

```
[Source: hr_policy.txt]

Employees receive 20 days of annual leave.

[Source: handbook.txt]

Unused leave may be carried forward.
```

The agent can now read these documents before answering.

---

# Step 6: Create the Calculator Tool

```python
def calculator(expression: str) -> str:
```

This tool evaluates arithmetic expressions.

Example:

Input:

```
25 * 12
```

Output:

```
300
```

---

### Clean the Input

```python
clean = expression.strip().strip("'\"")
```

Removes spaces and surrounding quotes.

Example:

```
"25 * 12"
```

becomes

```
25 * 12
```

---

### Evaluate the Expression

```python
result = eval(clean, {"__builtins__": {}})
```

`eval()` calculates the expression.

Examples:

```
365 / 7
```

↓

```
52.14
```

```
20 / 12
```

↓

```
1.67
```

The empty `__builtins__` dictionary disables access to Python's built-in functions, making the evaluation safer by allowing only basic arithmetic expressions.

---

### Handle Errors

```python
except Exception as e:
    return f"Error evaluating expression: {e}"
```

If the expression is invalid, the tool returns an error message instead of crashing.

---

# Step 7: Register the Tools

```python
tools = [
```

The agent is given two tools.

---

## Tool 1

```python
Tool(
    name="DocSearch",
    func=doc_search,
)
```

Purpose:

Search HR and IT policy documents.

Use cases:

* Leave policy
* Benefits
* IT security
* Work laptops

---

## Tool 2

```python
Tool(
    name="Calculator",
    func=calculator,
)
```

Purpose:

Perform arithmetic calculations.

Example:

```
20 / 12
```

↓

```
1.67
```

---

# Step 8: Load the LLM

```python
llm = OllamaLLM(model="llama3.2")
```

This loads the local Llama 3.2 model through Ollama.

Unlike `rag.py`, this model can decide **which tool to use** before generating the answer.

---

# Step 9: Initialize the Agent

```python
agent = initialize_agent(
    tools=tools,
    llm=llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True,
    handle_parsing_errors=True,
    max_iterations=5,
)
```

This creates the AI agent.

### Important Parameters

**tools**

The list of tools available to the agent.

---

**llm**

The language model that controls the reasoning process.

---

**AgentType.ZERO_SHOT_REACT_DESCRIPTION**

This tells the agent to:

1. Read the user's question.
2. Read the description of each tool.
3. Decide which tool is most appropriate.
4. Use the selected tool.
5. Generate the final answer.

The term **Zero-Shot** means the agent has not been trained specifically for these tools. Instead, it relies on the tool descriptions to decide how to use them.

---

**verbose=True**

Prints the agent's reasoning process.

Example:

```
Thought:
I should search the HR policy.

Action:
DocSearch

Observation:
Employees receive 20 annual leave days.

Final Answer:
Employees receive 20 annual leave days.
```

---

**handle_parsing_errors=True**

If the LLM produces an incorrectly formatted response, the agent will try to recover instead of failing immediately.

---

**max_iterations=5**

Limits the reasoning process to at most five steps before stopping.

---

# Step 10: Return the Agent

```python
return agent
```

The fully configured AI agent is returned.

---

# Step 11: Run the Program

```python
if __name__ == "__main__":
```

When the file is run directly, the agent is created.

```python
agent = build_agent()
```

---

# Step 12: Example Questions

```python
questions = [
    "How many days of annual leave do employees get?",
    "If I get 20 annual leave days per year, how many days is that per month?",
    "What should I do if I suspect a security breach?",
]
```

These sample questions demonstrate different tool choices.

---

# Step 13: Ask Each Question

```python
for q in questions:
```

The program processes each question one by one.

---

## Invoke the Agent

```python
result = agent.invoke({"input": q})
```

This starts the agent's reasoning process.

### Example 1

Question:

```
How many annual leave days do employees get?
```

Agent:

```
Question
    ↓
DocSearch
    ↓
Retrieve HR Policy
    ↓
Llama Reads Policy
    ↓
Final Answer
```

---

### Example 2

Question:

```
If I get 20 annual leave days per year, how many days is that per month?
```

Agent:

```
Question
    ↓
DocSearch → Finds 20 days/year
    ↓
Calculator → 20 / 12
    ↓
Llama Explains Result
```

---

### Example 3

Question:

```
What should I do if I suspect a security breach?
```

Agent:

```
Question
    ↓
DocSearch
    ↓
Retrieve IT Security Policy
    ↓
Llama Generates Answer
```

---

# Print the Final Answer

```python
print(f"\nFinal Answer: {result['output']}")
```

Only the final response is displayed to the user.

---

# Overall Workflow

```
                User Question
                      │
                      ▼
              Llama 3.2 Agent
                      │
        ┌─────────────┴─────────────┐
        │                           │
        ▼                           ▼
   DocSearch Tool            Calculator Tool
        │                           │
        ▼                           ▼
 Search ChromaDB             Evaluate Expression
        │                           │
        └─────────────┬─────────────┘
                      ▼
               Llama 3.2 Reads Results
                      ▼
              Generate Final Answer
                      ▼
               Display to the User
```

# Difference Between `rag.py` and `agent.py`

| `rag.py`                                     | `agent.py`                                                                      |
| -------------------------------------------- | ------------------------------------------------------------------------------- |
| Always retrieves documents before answering. | Chooses whether it needs to retrieve documents, calculate, or use another tool. |
| Uses a fixed RetrievalQA pipeline.           | Uses an intelligent agent that selects tools dynamically.                       |
| Good for document question answering.        | Good for multi-step reasoning and tool usage.                                   |
| Limited to retrieval-based responses.        | Can combine retrieval, calculations, and other tools before answering.          |

# Summary

`agent.py` creates an intelligent AI agent that uses Llama 3.2 together with multiple tools. The agent first analyzes the user's question, decides whether it should search company documents or perform a calculation, executes the appropriate tool, and then uses the tool's output to generate a final, natural-language answer. Unlike a standard RAG pipeline, this agent can reason about which tool to use, making it more flexible and capable of handling a wider variety of tasks.
