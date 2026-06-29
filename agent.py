__import__("pysqlite3")
import sys
sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")

import json
import uuid
import datetime
import os
import random
import string
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_ollama import OllamaLLM
from langchain.tools import Tool
from langchain.agents import AgentType, initialize_agent

TICKETS_FILE = "tickets.json"
CREDENTIALS_FILE = "credentials.json"

VALID_ENVS = {"prod", "staging", "dev"}


def _load_credentials():
    if not os.path.exists(CREDENTIALS_FILE):
        return {}
    with open(CREDENTIALS_FILE, "r") as f:
        return json.load(f)


def _save_credentials(data):
    with open(CREDENTIALS_FILE, "w") as f:
        json.dump(data, f, indent=2)


def _generate_password(length=14):
    chars = string.ascii_letters + string.digits
    while True:
        pwd = "".join(random.choices(chars, k=length))
        # ensure at least 1 uppercase, 1 lowercase, 1 digit
        if (any(c.isupper() for c in pwd)
                and any(c.islower() for c in pwd)
                and any(c.isdigit() for c in pwd)):
            return pwd

CHROMA_DIR = "chroma_db"
EMBED_MODEL = "all-MiniLM-L6-v2"


def build_agent():
    embeddings = HuggingFaceEmbeddings(model_name=EMBED_MODEL)
    vectorstore = Chroma(persist_directory=CHROMA_DIR, embedding_function=embeddings)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

    def doc_search(query: str) -> str:
        docs = retriever.invoke(query)
        docs = [d for d in docs if d.page_content and d.page_content.strip()]
        if not docs:
            return "No relevant documents found."
        return "\n\n".join(
            f"[Source: {d.metadata.get('source', 'unknown')}]\n{d.page_content}"
            for d in docs
        )

    def raise_ticket(issue: str) -> str:
        ticket_id = "INC-" + str(uuid.uuid4())[:8].upper()
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ticket = {
            "ticket_id": ticket_id,
            "issue": issue,
            "status": "Open",
            "priority": "P3",
            "raised_at": timestamp,
            "assigned_to": "IT Helpdesk Team",
        }
        # Load existing tickets or start fresh
        tickets = []
        if os.path.exists(TICKETS_FILE):
            with open(TICKETS_FILE, "r") as f:
                tickets = json.load(f)
        tickets.append(ticket)
        with open(TICKETS_FILE, "w") as f:
            json.dump(tickets, f, indent=2)

        return (
            f"Ticket raised successfully!\n"
            f"  Ticket ID  : {ticket_id}\n"
            f"  Issue      : {issue}\n"
            f"  Status     : Open\n"
            f"  Priority   : P3 (Medium)\n"
            f"  Assigned to: IT Helpdesk Team\n"
            f"  Raised at  : {timestamp}\n"
            f"  All tickets saved to '{TICKETS_FILE}'"
        )

    def _parse_user_env(query: str):
        """Flexible parser — accepts 'dronesup prod', 'user:dronesup env:prod', 'dronesup, prod'."""
        q = query.lower().replace(",", " ")
        parts = {}
        tokens = q.split()
        for token in tokens:
            if ":" in token:
                k, v = token.split(":", 1)
                parts[k.strip()] = v.strip()
        username = parts.get("user") or parts.get("username")
        env = parts.get("env") or parts.get("environment")
        # fallback: if no key:value pairs, pick env from known words, rest is username
        if not username or not env:
            env_found = next((t for t in tokens if t in VALID_ENVS), None)
            user_found = next((t for t in tokens if t not in VALID_ENVS and len(t) > 1), None)
            username = username or user_found
            env = env or env_found
        return username, env

    def fetch_password(query: str) -> str:
        username, env = _parse_user_env(query)
        if not username or not env:
            return f"Could not find username or environment in input. Valid environments: {', '.join(VALID_ENVS)}."
        if env not in VALID_ENVS:
            return f"Unknown environment '{env}'. Valid options: {', '.join(VALID_ENVS)}."
        creds = _load_credentials()
        key = f"{username}@{env}"
        if key not in creds:
            password = _generate_password()
            creds[key] = {
                "username": username,
                "environment": env,
                "password": password,
                "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
            _save_credentials(creds)
        entry = creds[key]
        return (
            f"Credentials fetched successfully!\n"
            f"  Username   : {entry['username']}\n"
            f"  Environment: {entry['environment']}\n"
            f"  Password   : {entry['password']}\n"
            f"  Created at : {entry['created_at']}"
        )

    def clear_password(query: str) -> str:
        username, env = _parse_user_env(query)
        if not username or not env:
            return f"Could not find username or environment in input. Valid environments: {', '.join(VALID_ENVS)}."
        if env not in VALID_ENVS:
            return f"Unknown environment '{env}'. Valid options: {', '.join(VALID_ENVS)}."
        creds = _load_credentials()
        key = f"{username}@{env}"
        if key not in creds:
            return f"No credentials found for user '{username}' in '{env}'."
        del creds[key]
        _save_credentials(creds)
        return f"Credentials for '{username}' in '{env}' have been cleared successfully."

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
        Tool(
            name="TicketRaiser",
            func=raise_ticket,
            description=(
                "Raise an IT support ticket for the user. "
                "Use this when the user reports a problem, requests help, or asks to raise/log/create a ticket. "
                "Input should be a clear description of the issue."
            ),
        ),
        Tool(
            name="FetchPassword",
            func=fetch_password,
            description=(
                "Fetch or generate a password for a user in an environment (prod, staging, or dev). "
                "Use when the user asks for a password or credentials. "
                "Input: username and environment as plain text, e.g. 'dronesup prod'"
            ),
        ),
        Tool(
            name="ClearPassword",
            func=clear_password,
            description=(
                "Clear or delete stored credentials for a user in an environment (prod, staging, or dev). "
                "Use when the user asks to clear, delete, or reset a password. "
                "Input: username and environment as plain text, e.g. 'dronesup prod'"
            ),
        ),
    ]

    llm = OllamaLLM(model="llama3.2")

    agent_prefix = """You are a Digital Workplace Assistant. Answer the user's request using the right tool.

TOOL SELECTION RULES — follow strictly:
- If the user asks to FETCH, GET, SHOW, or RETRIEVE a password or credentials for a specific username → use FetchPassword
- If the user asks to CLEAR, DELETE, or RESET a password or credentials for a specific username → use ClearPassword
- If the user asks to RAISE, LOG, or CREATE a ticket for an issue → use TicketRaiser
- If the user asks to CALCULATE or do MATH → use Calculator
- If the user asks a general policy question (leave, benefits, security, IT rules) → use DocSearch
- NEVER use DocSearch to fetch or clear a user's password

You have access to the following tools:"""

    agent = initialize_agent(
        tools=tools,
        llm=llm,
        agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=8,
        agent_kwargs={"prefix": agent_prefix},
    )
    return agent


if __name__ == "__main__":
    agent = build_agent()
    questions = [
        "How many days of annual leave do employees get?",
        "If I get 20 annual leave days per year, how many days is that per month?",
        "What should I do if I suspect a security breach?",
        "My laptop screen is broken, please raise a ticket for me.",
    ]
    for q in questions:
        print(f"\n{'='*60}\nQ: {q}")
        result = agent.invoke({"input": q})
        print(f"\nFinal Answer: {result['output']}")
