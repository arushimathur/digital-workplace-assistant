__import__("pysqlite3")
import sys
sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")

import json
import os
import re
import uuid
import difflib
import streamlit as st
from rag import load_rag_chain
from agent import (
    build_agent, TICKETS_FILE,
    _load_credentials, _save_credentials, _generate_password, VALID_ENVS,
)
import datetime
from daily_brief import get_slack_messages, get_emails, get_github_activity, build_brief_summary, TODAY

CITY_FILE_MAP = {
    "bangalore": "leave_calendars/bangalore.txt",
    "bengaluru": "leave_calendars/bangalore.txt",
    "dallas":    "leave_calendars/dallas.txt",
    "new york":  "leave_calendars/new_york.txt",
    "newyork":   "leave_calendars/new_york.txt",
    "phoenix":   "leave_calendars/phoenix.txt",
    "london":    "leave_calendars/london.txt",
}

# Canonical name each alias/misspelling resolves to
CITY_ALIASES = {
    # Bangalore
    "bangalore": "bangalore", "bengaluru": "bangalore", "banglore": "bangalore",
    "banglaore": "bangalore", "bangaluru": "bangalore", "bangalor": "bangalore",
    "bengalore": "bangalore", "bangloore": "bangalore", "banglure": "bangalore",
    "bangulore": "bangalore", "bangalure": "bangalore", "banglauru": "bangalore",
    # Dallas
    "dallas": "dallas", "dalas": "dallas", "dallus": "dallas",
    "dallass": "dallas", "dalls": "dallas", "dals": "dallas",
    # New York
    "new york": "new york", "newyork": "new york", "new yourk": "new york",
    "new yark": "new york", "newyrok": "new york", "new yrk": "new york",
    "new yok": "new york", "new yokr": "new york",
    # Phoenix
    "phoenix": "phoenix", "pheonix": "phoenix", "phonix": "phoenix",
    "phoenx": "phoenix", "phoinex": "phoenix", "pheniox": "phoenix",
    "pheonix": "phoenix", "pheonx": "phoenix",
    # London
    "london": "london", "londun": "london", "londen": "london",
    "londn": "london", "londone": "london", "londan": "london",
}

def match_city(text: str):
    """
    Resolve a city name from user text.
    1. Check alias dict (covers common misspellings explicitly)
    2. Fall back to difflib fuzzy match on each word token (cutoff=0.6)
    """
    t = text.lower().strip()
    # 1. Alias dict — exact key lookup on full text and individual tokens
    if t in CITY_ALIASES:
        return CITY_ALIASES[t]
    tokens = re.findall(r"[a-z]+", t)
    for token in tokens:
        if token in CITY_ALIASES:
            return CITY_ALIASES[token]
    # Also try two-word combos (e.g. "new york")
    words = t.split()
    for i in range(len(words) - 1):
        bigram = words[i] + " " + words[i + 1]
        if bigram in CITY_ALIASES:
            return CITY_ALIASES[bigram]
    # 2. Fuzzy fallback via difflib on single tokens
    all_aliases = list(CITY_ALIASES.keys())
    for token in tokens:
        if len(token) < 3:
            continue
        close = difflib.get_close_matches(token, all_aliases, n=1, cutoff=0.6)
        if close:
            return CITY_ALIASES[close[0]]
    return None

def fuzzy_contains(text, keywords, cutoff=0.75):
    """
    Returns True if any word in `text` is close enough to any keyword.
    Handles misspellings like 'calander'→'calendar', 'tickt'→'ticket', 'pasword'→'password'.
    - Exact substring match first (fast path)
    - Then difflib fuzzy match on each token
    """
    t = text.lower()
    # Fast path: exact match
    if any(kw in t for kw in keywords):
        return True
    # Fuzzy match: each word in text vs each keyword
    tokens = re.findall(r"[a-z]+", t)
    for token in tokens:
        if len(token) < 3:
            continue
        close = difflib.get_close_matches(token, keywords, n=1, cutoff=cutoff)
        if close:
            return True
    return False


# Annual leave days + city-specific public holidays (sourced from the documents)
CITY_LEAVE_INFO = {
    "bangalore": {"annual": 20, "public": 16, "restricted_choice": 2,  "note": "Plus 2 restricted holidays of your choice"},
    "dallas":    {"annual": 20, "public": 14, "floating": 2,            "note": "Plus 2 floating holidays"},
    "new york":  {"annual": 20, "public": 12, "floating": 3,            "note": "Plus 3 floating holidays + 7 days paid sick leave"},
    "phoenix":   {"annual": 20, "public": 12, "floating": 2,            "note": "Plus 2 floating holidays"},
    "london":    {"annual": 25, "public": 8,  "floating": 0,            "note": "UK employees get 25 annual leave days (not 20)"},
}

def handle_leave_calendar(text: str):
    """Directly read leave calendar file for a city — no LLM needed."""
    t = text.lower()
    if not fuzzy_contains(t, ["leave", "holiday", "calendar", "holidays"]):
        return None

    # Total leave calculation query
    is_total_query = fuzzy_contains(t, ["total", "how many", "how much", "count", "including", "combined", "altogether"])
    matched_city = match_city(t)

    if is_total_query and matched_city:
        info = CITY_LEAVE_INFO.get(matched_city)
        if info:
            total = info["annual"] + info["public"] + info.get("floating", 0) + info.get("restricted_choice", 0)
            lines = [
                f"### Total Leave for **{matched_city.title()}** in 2026\n",
                f"| Type | Days |",
                f"|------|------|",
                f"| Annual (Paid) Leave | {info['annual']} days |",
                f"| Public Holidays | {info['public']} days |",
            ]
            if info.get("floating"):
                lines.append(f"| Floating Holidays | {info['floating']} days |")
            if info.get("restricted_choice"):
                lines.append(f"| Restricted Holidays (your choice) | {info['restricted_choice']} days |")
            lines.append(f"| **Total** | **{total} days** |")
            lines.append(f"\n> {info['note']}")
            return "\n".join(lines)

    if not matched_city:
        cities = ", ".join(sorted(set(CITY_FILE_MAP.keys()) - {"bengaluru", "newyork"}))
        return f"Leave calendars are available for: **{cities}**.\n\nPlease specify a city, e.g. *fetch leave calendar for Bangalore*."

    filepath = CITY_FILE_MAP[matched_city]
    if not os.path.exists(filepath):
        return f"Leave calendar file for **{matched_city}** not found."
    with open(filepath, "r") as f:
        content = f.read()
    return f"```\n{content}\n```"


def _extract_user_env(text: str):
    """Pull username and environment out of a plain-English sentence."""
    text_lower = text.lower()
    env = next((e for e in VALID_ENVS if e in text_lower), None)
    # strip common filler words, then find the token that isn't a stopword or env
    stopwords = {"fetch", "get", "show", "retrieve", "clear", "delete", "reset",
                 "password", "credentials", "for", "user", "in", "the", "a",
                 "an", "of", "please", "me", "my"} | VALID_ENVS
    tokens = re.findall(r"[a-zA-Z0-9_\-]+", text_lower)
    username = next((t for t in tokens if t not in stopwords), None)
    return username, env


def handle_greeting(text: str):
    """Respond to greetings directly — no LLM needed."""
    t = text.strip().lower()
    greetings = ["hi", "hello", "hey", "hii", "helo", "heya", "howdy",
                 "good morning", "good afternoon", "good evening", "whats up", "what's up"]
    if not fuzzy_contains(t, greetings, cutoff=0.8) or len(t.split()) > 5:
        return None
    return (
        "Hello! 👋 I'm your Digital Workplace Assistant.\n\n"
        "Here's what I can help you with:\n"
        "- 📋 **Policy questions** — leave, IT, HR, benefits\n"
        "- 🗓️ **Leave calendars** — holidays for Bangalore, Dallas, New York, Phoenix, London\n"
        "- ☀️ **Daily brief** — Slack, Email, GitHub summary\n"
        "- 🎫 **Raise IT tickets** — just describe your issue\n"
        "- 🔑 **Fetch/clear passwords** — for prod, staging, or dev\n\n"
        "What can I help you with today?"
    )


def handle_daily_brief(text: str):
    """Respond with daily brief in chat when user asks for it."""
    t = text.lower()
    # Match both 'daily brief' and 'today's tasks / todo / what should I do'
    is_brief = fuzzy_contains(t, ["brief", "happening", "update", "summary", "digest"])
    is_tasks = fuzzy_contains(t, ["task", "tasks", "todo", "todos", "agenda",
                                   "action", "actions", "pending", "reminders", "schedule"])
    if not (is_brief or is_tasks):
        return None
    if not fuzzy_contains(t, ["daily", "today", "morning", "my", "all", "todays", "give", "show"]):
        return None

    slack  = get_slack_messages()
    emails = get_emails()
    github = get_github_activity()

    unread_count = sum(1 for e in emails if e["unread"])
    lines = [f"### ☀️ Daily Brief — {TODAY}\n"]

    # AI summary via LLM
    try:
        from langchain_ollama import OllamaLLM
        summary_text = build_brief_summary(slack, emails, github)
        llm = OllamaLLM(model="llama3.2")
        ai_summary = llm.invoke(
            f"You are a workplace assistant. Give a concise 3-bullet daily briefing "
            f"based on this data. Focus only on action items and important updates.\n\n{summary_text}"
        )
        lines.append(f"**🤖 Key Actions Today:**\n{ai_summary}\n")
    except Exception:
        pass

    # Slack summary
    lines.append("---\n**💬 Slack — Channels**")
    for msg in slack["channels"]:
        lines.append(f"- `{msg['channel']}` **{msg['sender']}** ({msg['time']}): {msg['message']}")

    lines.append("\n**💬 Slack — Direct Messages**")
    for dm in slack["direct_messages"]:
        lines.append(f"- 👤 **{dm['from']}** ({dm['time']}): {dm['message']}")

    lines.append("\n**💬 Slack — Group Messages**")
    for gm in slack["group_messages"]:
        lines.append(f"- 👥 **{gm['group']}** · {gm['sender']} ({gm['time']}): {gm['message']}")

    # Email summary
    lines.append(f"\n**📧 Email — {unread_count} Unread**")
    for email in emails:
        badge = "🔵" if email["unread"] else "⚪"
        lines.append(f"- {badge} **{email['subject']}** — *{email['from']}* ({email['time']})")

    # GitHub summary
    lines.append("\n**🐙 GitHub — Open PRs**")
    for pr in github["pull_requests"]:
        icon = "🟡" if pr["status"] == "Review Requested" else "🔴"
        lines.append(f"- {icon} #{pr['pr_number']} {pr['title']} [{pr['status']}]")

    lines.append("\n**🐙 GitHub — Assigned Issues**")
    for issue in github["assigned_issues"]:
        icon = "🔴" if issue["priority"] == "High" else "🟡"
        lines.append(f"- {icon} #{issue['issue_number']} {issue['title']} (Due: {issue['due']})")

    return "\n".join(lines)


def handle_ticket(text: str):
    """Detect ticket-raise intent with fuzzy matching and raise directly."""
    t = text.lower()
    is_action = fuzzy_contains(t, ["raise", "create", "log", "open", "submit", "file"])
    is_ticket  = fuzzy_contains(t, ["ticket", "issue", "request", "incident"])
    if not (is_action and is_ticket):
        return None
    # Import here to avoid circular issues
    import uuid as _uuid, json as _json, datetime as _dt
    ticket_id = "INC-" + str(_uuid.uuid4())[:8].upper()
    timestamp = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # Strip intent words to get the actual issue description
    stopwords = {"raise","create","log","open","submit","file","a","an","the",
                 "ticket","issue","request","incident","for","me","please","my","i"}
    tokens = [w for w in re.findall(r"[a-zA-Z0-9]+", text) if w.lower() not in stopwords]
    issue = " ".join(tokens) if tokens else text
    ticket = {
        "ticket_id": ticket_id, "issue": issue, "status": "Open",
        "priority": "P3", "raised_at": timestamp, "assigned_to": "IT Helpdesk Team",
    }
    tickets = []
    if os.path.exists(TICKETS_FILE):
        with open(TICKETS_FILE) as f:
            tickets = _json.load(f)
    tickets.append(ticket)
    with open(TICKETS_FILE, "w") as f:
        _json.dump(tickets, f, indent=2)
    return (
        f"**Ticket raised successfully!**\n\n"
        f"| Field | Value |\n|-------|-------|\n"
        f"| Ticket ID | `{ticket_id}` |\n"
        f"| Issue | {issue} |\n"
        f"| Status | Open |\n"
        f"| Priority | P3 (Medium) |\n"
        f"| Assigned to | IT Helpdesk Team |\n"
        f"| Raised at | {timestamp} |"
    )


def handle_direct_command(text: str):
    """
    Intercept credential commands directly — no LLM needed.
    Returns a response string, or None if this isn't a credential command.
    """
    t = text.lower()
    is_fetch = fuzzy_contains(t, ["fetch", "get", "show", "retrieve"]) and fuzzy_contains(t, ["password", "credentials", "creds", "passwd"])
    is_clear = fuzzy_contains(t, ["clear", "delete", "reset", "remove"]) and fuzzy_contains(t, ["password", "credentials", "creds", "passwd"])

    if not is_fetch and not is_clear:
        return None  # let the agent handle it

    username, env = _extract_user_env(text)
    if not username or not env:
        return (
            f"Please specify a username and environment. "
            f"Valid environments: {', '.join(VALID_ENVS)}.\n"
            f"Example: *fetch password for dronesup in prod*"
        )

    if is_fetch:
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
            f"**Credentials fetched successfully!**\n\n"
            f"| Field | Value |\n|-------|-------|\n"
            f"| Username | `{entry['username']}` |\n"
            f"| Environment | `{entry['environment']}` |\n"
            f"| Password | `{entry['password']}` |\n"
            f"| Created at | {entry['created_at']} |"
        )

    if is_clear:
        creds = _load_credentials()
        key = f"{username}@{env}"
        if key not in creds:
            return f"No credentials found for **{username}** in **{env}**."
        del creds[key]
        _save_credentials(creds)
        return f"Credentials for **{username}** in **{env}** have been cleared successfully."


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


# ── helper functions ────────────────────────────────────────────
LEAVE_FILE = "leave_applications.json"

def load_tickets():
    if not os.path.exists(TICKETS_FILE):
        return []
    with open(TICKETS_FILE) as f:
        return json.load(f)

def load_leave_applications():
    if not os.path.exists(LEAVE_FILE):
        return []
    with open(LEAVE_FILE) as f:
        return json.load(f)

def save_leave_application(app):
    apps = load_leave_applications()
    apps.append(app)
    with open(LEAVE_FILE, "w") as f:
        json.dump(apps, f, indent=2)

# ── tabs ─────────────────────────────────────────────────────────
tab_chat, tab_tickets, tab_leave, tab_brief = st.tabs([
    "💬 Chat", "🎫 IT Tickets", "🗓️ Leave", "☀️ Daily Brief"
])

# ══════════════════════════════════════════════════════════════════
# TAB 1 — CHAT
# ══════════════════════════════════════════════════════════════════
with tab_chat:
    mode = st.radio(
        "Mode",
        ["RAG (Simple Q&A)", "Agent (ReAct — can reason + calculate)"],
        horizontal=True,
    )

    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Render full chat history — always above the input box
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Input box renders here — at the bottom of existing messages
    if prompt := st.chat_input("Ask me anything about workplace policies..."):
        # Compute response first
        with st.spinner("Thinking..."):
            # Greeting and intent-based handlers run first in both modes
            response = handle_greeting(prompt) or handle_daily_brief(prompt) or handle_leave_calendar(prompt) or handle_ticket(prompt)
            if response is None:
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
                    response = handle_direct_command(prompt)
                    if response is None:
                        agent = get_agent()
                        result = agent.invoke({"input": prompt})
                        response = result["output"]

        # Save both messages to session state, then rerun
        # On rerun, messages render from history loop above — always above the input box
        st.session_state.messages.append({"role": "user",      "content": prompt})
        st.session_state.messages.append({"role": "assistant", "content": response})
        st.rerun()

# ══════════════════════════════════════════════════════════════════
# TAB 2 — IT TICKETS
# ══════════════════════════════════════════════════════════════════
with tab_tickets:
    st.subheader("🎫 IT Support Tickets")
    tickets = load_tickets()
    if not tickets:
        st.info("No tickets raised yet. Ask the assistant in the Chat tab to raise one.")
    else:
        col1, col2, col3 = st.columns(3)
        col1.metric("Total", len(tickets))
        col2.metric("Open", sum(1 for t in tickets if t["status"] == "Open"))
        col3.metric("Resolved", sum(1 for t in tickets if t["status"] == "Resolved"))
        st.markdown("---")
        for ticket in reversed(tickets):
            icon = "🟢" if ticket["status"] == "Resolved" else "🔴"
            with st.expander(f"{icon} {ticket['ticket_id']} — {ticket['issue'][:60]}"):
                c1, c2 = st.columns(2)
                c1.markdown(f"**Ticket ID:** `{ticket['ticket_id']}`")
                c1.markdown(f"**Status:** {ticket['status']}")
                c1.markdown(f"**Priority:** {ticket['priority']}")
                c2.markdown(f"**Raised at:** {ticket['raised_at']}")
                c2.markdown(f"**Assigned to:** {ticket['assigned_to']}")
                st.markdown(f"**Issue:** {ticket['issue']}")
    if st.button("Refresh Tickets"):
        st.rerun()

# ══════════════════════════════════════════════════════════════════
# TAB 3 — LEAVE
# ══════════════════════════════════════════════════════════════════
with tab_leave:
    st.subheader("🗓️ Apply for Leave")
    with st.form("leave_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            employee_name = st.text_input("Employee Name", placeholder="e.g. Arushi Mathur")
            leave_type = st.selectbox("Leave Type", [
                "Annual Leave", "Sick Leave", "Casual Leave",
                "Maternity/Paternity Leave", "Bereavement Leave", "Unpaid Leave"
            ])
            city = st.selectbox("Office Location", ["Bangalore", "Dallas", "New York", "Phoenix", "London"])
        with col2:
            start_date = st.date_input("Start Date", min_value=datetime.date.today())
            end_date   = st.date_input("End Date",   min_value=datetime.date.today())
            reason     = st.text_area("Reason", placeholder="Brief reason for leave", height=100)
        submitted = st.form_submit_button("Submit Leave Application")

    if submitted:
        if not employee_name.strip():
            st.error("Please enter your name.")
        elif end_date < start_date:
            st.error("End date cannot be before start date.")
        elif not reason.strip():
            st.error("Please provide a reason.")
        else:
            num_days = (end_date - start_date).days + 1
            app_id   = "LV-" + str(uuid.uuid4())[:8].upper()
            application = {
                "application_id": app_id,
                "employee_name":  employee_name.strip(),
                "leave_type":     leave_type,
                "city":           city,
                "start_date":     str(start_date),
                "end_date":       str(end_date),
                "num_days":       num_days,
                "reason":         reason.strip(),
                "status":         "Pending",
                "applied_at":     datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
            save_leave_application(application)
            st.success(
                f"Leave application submitted!\n\n"
                f"**Application ID:** `{app_id}`  \n"
                f"**Days:** {num_days} day(s) — {start_date} to {end_date}  \n"
                f"**Status:** Pending approval"
            )

    st.divider()
    st.subheader("📋 Leave History")
    applications = load_leave_applications()
    if not applications:
        st.info("No leave applications yet.")
    else:
        col1, col2, col3 = st.columns(3)
        col1.metric("Total", len(applications))
        col2.metric("Pending",  sum(1 for a in applications if a["status"] == "Pending"))
        col3.metric("Approved", sum(1 for a in applications if a["status"] == "Approved"))
        st.markdown("---")
        for app in reversed(applications):
            icon = {"Pending": "🟡", "Approved": "🟢", "Rejected": "🔴"}.get(app["status"], "⚪")
            with st.expander(f"{icon} {app['application_id']} — {app['employee_name']} | {app['leave_type']} | {app['num_days']} day(s)"):
                c1, c2 = st.columns(2)
                c1.markdown(f"**Application ID:** `{app['application_id']}`")
                c1.markdown(f"**Employee:** {app['employee_name']}")
                c1.markdown(f"**Leave Type:** {app['leave_type']}")
                c1.markdown(f"**City:** {app['city']}")
                c2.markdown(f"**From:** {app['start_date']}")
                c2.markdown(f"**To:** {app['end_date']}")
                c2.markdown(f"**Days:** {app['num_days']}")
                c2.markdown(f"**Status:** {app['status']}")
                st.markdown(f"**Reason:** {app['reason']}")
                st.caption(f"Applied at: {app['applied_at']}")
    if st.button("Refresh Applications"):
        st.rerun()

# ══════════════════════════════════════════════════════════════════
# TAB 4 — DAILY BRIEF
# ══════════════════════════════════════════════════════════════════
with tab_brief:
    st.subheader(f"☀️ My Daily Brief — {TODAY}")

    if st.button("Generate My Daily Brief", type="primary"):
        slack   = get_slack_messages()
        emails  = get_emails()
        github  = get_github_activity()
        summary = build_brief_summary(slack, emails, github)

        st.markdown("### 🤖 AI Summary")
        with st.spinner("Summarising your day..."):
            try:
                from langchain_ollama import OllamaLLM
                llm = OllamaLLM(model="llama3.2")
                ai_summary = llm.invoke(
                    f"You are a workplace assistant. Give a concise 3-bullet daily briefing "
                    f"based on this data. Focus only on action items and important updates.\n\n{summary}"
                )
                st.info(ai_summary)
            except Exception:
                st.info(summary)

        st.markdown("### 💬 Slack — Channels")
        for msg in slack["channels"]:
            with st.container(border=True):
                col_a, col_b = st.columns([1, 4])
                col_a.markdown(f"**{msg['channel']}**  \n`{msg['time']}`")
                col_b.markdown(f"**{msg['sender']}:** {msg['message']}")

        st.markdown("### 💬 Slack — Direct Messages")
        for dm in slack["direct_messages"]:
            with st.container(border=True):
                col_a, col_b = st.columns([1, 4])
                col_a.markdown(f"👤 **{dm['from']}**  \n`{dm['time']}`")
                col_b.markdown(dm["message"])

        st.markdown("### 💬 Slack — Group Messages")
        for gm in slack["group_messages"]:
            with st.container(border=True):
                col_a, col_b = st.columns([1, 4])
                col_a.markdown(f"👥 **{gm['sender']}**  \n`{gm['time']}`  \n_{gm['group']}_")
                col_b.markdown(gm["message"])

        st.markdown("### 📧 Email — Inbox")
        for email in emails:
            badge = "🔵 Unread" if email["unread"] else "⚪ Read"
            with st.container(border=True):
                col_a, col_b = st.columns([1, 4])
                col_a.markdown(f"{badge}  \n`{email['time']}`  \n*{email['from']}*")
                col_b.markdown(f"**{email['subject']}**  \n{email['preview']}")

        st.markdown("### 🐙 GitHub — Pull Requests")
        for pr in github["pull_requests"]:
            icon = "🟡" if pr["status"] == "Review Requested" else "🔴"
            with st.container(border=True):
                col_a, col_b = st.columns([3, 1])
                col_a.markdown(f"{icon} **#{pr['pr_number']}** {pr['title']}  \n`{pr['repo']}` · by **{pr['author']}**")
                col_b.markdown(f"**{pr['status']}**  \n{pr['updated']}")

        st.markdown("### 🐙 GitHub — Assigned Issues")
        for issue in github["assigned_issues"]:
            icon = "🔴" if issue["priority"] == "High" else "🟡"
            with st.container(border=True):
                col_a, col_b = st.columns([3, 1])
                col_a.markdown(f"{icon} **#{issue['issue_number']}** {issue['title']}  \n`{issue['repo']}`")
                col_b.markdown(f"**{issue['priority']} Priority**  \nDue: {issue['due']}")

        st.markdown("### 🐙 GitHub — Recent Commits")
        for commit in github["recent_commits"]:
            st.markdown(f"- `{commit['repo']}` — {commit['message']} · _{commit['time']}_")

with st.sidebar:
    st.header("About this app")
    st.markdown("""
**Stack:**
- 🦙 Llama 3.2 via Ollama (local LLM)
- 🔗 LangChain (orchestration)
- 🗄️ ChromaDB (vector store)
- 🤗 HuggingFace Embeddings
- 🌐 Streamlit (UI)

**Modes (Chat tab):**
- **RAG** — retrieves policy chunks, then answers
- **Agent** — ReAct loop: reason, search, calculate
    """)
    if st.button("Clear Chat"):
        st.session_state.messages = []
        st.rerun()
    if st.button("Reload AI Models"):
        st.cache_resource.clear()
        st.success("Cache cleared.")
        st.rerun()
