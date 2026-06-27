__import__("pysqlite3")
import sys
sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")

import streamlit as st
from rag import load_rag_chain
from agent import build_agent

st.set_page_config(
    page_title="Digital Workplace Assistant",
    page_icon="💼",
    layout="centered",
)

st.title("💼 Digital Workplace Assistant")
st.caption("Ask questions about HR policies, IT policies, and more.")


@st.cache_resource
def get_rag_chain():
    return load_rag_chain()


@st.cache_resource
def get_agent():
    return build_agent()


mode = st.radio(
    "Mode",
    ["RAG (Simple Q&A)", "Agent (ReAct — can reason + calculate)"],
    horizontal=True,
)

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Ask me anything about workplace policies..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            if mode.startswith("RAG"):
                chain = get_rag_chain()
                result = chain.invoke({"query": prompt})
                answer = result["result"]
                sources = list({
                    d.metadata.get("source", "unknown")
                    for d in result["source_documents"]
                })
                response = answer
                if sources:
                    response += "\n\n**Sources:** " + ", ".join(
                        f"`{s.split('/')[-1]}`" for s in sources
                    )
            else:
                agent = get_agent()
                result = agent.invoke({"input": prompt})
                response = result["output"]

        st.markdown(response)

    st.session_state.messages.append({"role": "assistant", "content": response})

with st.sidebar:
    st.header("About this app")
    st.markdown("""
**Stack:**
- 🦙 Llama 3.2 via Ollama (local LLM)
- 🔗 LangChain (orchestration)
- 🗄️ ChromaDB (vector store)
- 🤗 HuggingFace Embeddings
- 🌐 Streamlit (UI)

**Modes:**
- **RAG** — retrieves relevant policy chunks, then answers
- **Agent** — uses ReAct loop: can reason, search docs, and calculate

**Documents loaded:**
- `hr_policy.txt` — leave, benefits, conduct
- `it_policy.txt` — devices, security, software
    """)

    if st.button("Clear chat"):
        st.session_state.messages = []
        st.rerun()
