__import__("pysqlite3")
import sys
sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")

from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_ollama import OllamaLLM
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate

CHROMA_DIR = "chroma_db"
EMBED_MODEL = "all-MiniLM-L6-v2"

PROMPT_TEMPLATE = """You are a helpful Digital Workplace Assistant for American Express employees.
Use ONLY the context below to answer the question. If the answer is in the context, provide it fully and clearly.
Do NOT say "I don't have access" or "I cannot find" if the information is present in the context.

Context:
{context}

Question: {question}

Answer:"""

def load_rag_chain():
    embeddings = HuggingFaceEmbeddings(model_name=EMBED_MODEL)
    vectorstore = Chroma(persist_directory=CHROMA_DIR, embedding_function=embeddings)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 6})
    llm = OllamaLLM(model="llama3.2")
    prompt = PromptTemplate(
        template=PROMPT_TEMPLATE,
        input_variables=["context", "question"],
    )
    chain = RetrievalQA.from_chain_type(
        llm=llm,
        retriever=retriever,
        return_source_documents=True,
        chain_type_kwargs={"prompt": prompt},
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
