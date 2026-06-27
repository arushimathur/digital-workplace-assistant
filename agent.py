__import__("pysqlite3")
import sys
sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")

from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_ollama import OllamaLLM
from langchain.tools import Tool
from langchain.agents import AgentType, initialize_agent

CHROMA_DIR = "chroma_db"
EMBED_MODEL = "all-MiniLM-L6-v2"


def build_agent():
    embeddings = HuggingFaceEmbeddings(model_name=EMBED_MODEL)
    vectorstore = Chroma(persist_directory=CHROMA_DIR, embedding_function=embeddings)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

    def doc_search(query: str) -> str:
        docs = retriever.invoke(query)
        if not docs:
            return "No relevant documents found."
        return "\n\n".join(
            f"[Source: {d.metadata.get('source', 'unknown')}]\n{d.page_content}"
            for d in docs
        )

    def calculator(expression: str) -> str:
        try:
            clean = expression.strip().strip("'\"")
            result = eval(clean, {"__builtins__": {}})  # noqa: S307
            return str(result)
        except Exception as e:
            return f"Error evaluating expression: {e}"

    tools = [
        Tool(
            name="DocSearch",
            func=doc_search,
            description=(
                "Search the company's HR and IT policy documents. "
                "Use this for questions about leave, benefits, security, devices, or IT policies."
            ),
        ),
        Tool(
            name="Calculator",
            func=calculator,
            description=(
                "Evaluate a mathematical expression. "
                "Input must be a valid Python arithmetic expression, e.g. '25 * 12' or '365 / 7'."
            ),
        ),
    ]

    llm = OllamaLLM(model="llama3.2")

    agent = initialize_agent(
        tools=tools,
        llm=llm,
        agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=5,
    )
    return agent


if __name__ == "__main__":
    agent = build_agent()
    questions = [
        "How many days of annual leave do employees get?",
        "If I get 20 annual leave days per year, how many days is that per month?",
        "What should I do if I suspect a security breach?",
    ]
    for q in questions:
        print(f"\n{'='*60}\nQ: {q}")
        result = agent.invoke({"input": q})
        print(f"\nFinal Answer: {result['output']}")
