__import__("pysqlite3")
import sys
sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")

from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

DOCS_DIR = "docs"
CHROMA_DIR = "chroma_db"
EMBED_MODEL = "all-MiniLM-L6-v2"

def ingest():
    print("Loading documents...")
    loader = DirectoryLoader(DOCS_DIR, glob="**/*.txt", loader_cls=TextLoader)
    documents = loader.load()
    print(f"Loaded {len(documents)} documents")

    print("Splitting into chunks...")
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = splitter.split_documents(documents)
    print(f"Created {len(chunks)} chunks")

    print("Creating embeddings and storing in ChromaDB...")
    embeddings = HuggingFaceEmbeddings(model_name=EMBED_MODEL)
    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=CHROMA_DIR,
    )
    vectorstore.persist()
    print(f"Done. {len(chunks)} chunks stored in '{CHROMA_DIR}/'")

if __name__ == "__main__":
    ingest()
