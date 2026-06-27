__import__("pysqlite3")
import sys
sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")

from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_ollama import OllamaLLM
from langchain.chains import RetrievalQA

CHROMA_DIR = "chroma_db"
EMBED_MODEL = "all-MiniLM-L6-v2"

def load_rag_chain():
    embeddings = HuggingFaceEmbeddings(model_name=EMBED_MODEL)
    vectorstore = Chroma(persist_directory=CHROMA_DIR, embedding_function=embeddings)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
    llm = OllamaLLM(model="llama3.2")
    chain = RetrievalQA.from_chain_type(
        llm=llm,
        retriever=retriever,
        return_source_documents=True,
    )
    return chain

if __name__ == "__main__":
    chain = load_rag_chain()
    questions = [
        "How many days of annual leave do employees get?",
        "What should I do if I suspect a security breach?",
        "Can I install software on my work laptop?",
    ]
    for q in questions:
        print(f"\nQ: {q}")
        result = chain.invoke({"query": q})
        print(f"A: {result['result']}")
        print(f"Sources: {[d.metadata.get('source', '') for d in result['source_documents']]}")
