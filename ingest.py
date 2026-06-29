__import__("pysqlite3")
import sys
sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")

import os
import shutil
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

DOCS_DIRS = ["docs", "hr_docs", "it_docs", "leave_calendars"]
CHROMA_DIR = "chroma_db"
EMBED_MODEL = "all-MiniLM-L6-v2"

def ingest():
    # Wipe existing ChromaDB so re-runs don't create duplicates
    if os.path.exists(CHROMA_DIR):
        shutil.rmtree(CHROMA_DIR)
        print(f"Cleared existing '{CHROMA_DIR}/'")

    print("Loading documents...")
    documents = []
    for folder in DOCS_DIRS:
        if not os.path.exists(folder):
            print(f"  Skipping '{folder}' (folder not found)")
            continue
        loader = DirectoryLoader(folder, glob="**/*.txt", loader_cls=TextLoader)
        loaded = loader.load()
        print(f"  '{folder}': {len(loaded)} documents")
        documents.extend(loaded)
    print(f"Loaded {len(documents)} documents total")

    print("Splitting into chunks...")
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = splitter.split_documents(documents)
    # Remove empty or None chunks to avoid ChromaDB validation errors
    chunks = [c for c in chunks if c.page_content and c.page_content.strip()]
    print(f"Created {len(chunks)} chunks")

    print("Creating embeddings and storing in ChromaDB...")
    embeddings = HuggingFaceEmbeddings(model_name=EMBED_MODEL)
    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=CHROMA_DIR
    )
    vectorstore.persist()
    print(f"Done. {len(chunks)} chunks stored in '{CHROMA_DIR}/'")

if __name__ == "__main__":
    ingest()
