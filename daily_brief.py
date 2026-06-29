"""
Daily Brief — aggregates data from Slack, Email, and GitHub.

Real integration points are marked with # REAL API comments.
Currently uses mock data for local demo.
"""

import datetime
import random

TODAY = datetime.date.today().strftime("%A, %B %d %Y")


def get_slack_messages() -> dict:
    """
    Returns Slack messages split into 3 categories:
    - channels: public/private channel messages
    - direct_messages: 1-on-1 DMs
    - group_messages: small group DMs (not a channel)

    REAL API:
      client = slack_sdk.WebClient(token=SLACK_TOKEN)
      # Channels:       client.conversations_list(types="public_channel,private_channel")
      # DMs:            client.conversations_list(types="im")
      # Group DMs:      client.conversations_list(types="mpim")
      # Messages:       client.conversations_history(channel=CHANNEL_ID, limit=10)
    """
    channels = [
        {
            "channel": "#general",
            "sender": "Priya Sharma",
            "time": "9:02 AM",
            "message": "Team standup moved to 10:30 AM today. Please update your tickets before joining.",
        },
        {
            "channel": "#it-support",
            "sender": "IT Helpdesk Bot",
            "time": "8:45 AM",
            "message": "Scheduled maintenance on the VPN gateway tonight 11 PM – 1 AM IST. Plan accordingly.",
        },
        {
            "channel": "#hr-updates",
            "sender": "HR Team",
            "time": "8:30 AM",
            "message": "Reminder: Q2 performance goals must be submitted in Workday by end of day Friday.",
        },
        {
            "channel": "#engineering",
            "sender": "Rahul Menon",
            "time": "9:15 AM",
            "message": "PR #247 is ready for review — adds retry logic to the Kafka consumer. Please review when you get a chance.",
        },
        {
            "channel": "#announcements",
            "sender": "Leadership",
            "time": "7:00 AM",
            "message": "AmEx has been recognised as one of Fortune's 100 Best Companies to Work For 2026. Congratulations team!",
        },
    ]

    direct_messages = [
        {
            "from": "Sneha Kapoor",
            "time": "9:20 AM",
            "message": "Hey! Can you share the latest version of the RAG pipeline doc? Need it for the demo today.",
        },
        {
            "from": "Manager — Vikram Nair",
            "time": "8:55 AM",
            "message": "Don't forget to add your agenda points to the 1:1 doc before 2 PM. Also, your Q2 goals look good — minor feedback added.",
        },
        {
            "from": "Ravi Anand",
            "time": "Yesterday 11:45 PM",
            "message": "Pushed a fix to the ingest pipeline. Can you review when free? No rush.",
        },
        {
            "from": "IT Helpdesk",
            "time": "8:10 AM",
            "message": "Your ticket INC-EC1033F0 (laptop screen) has been assigned to a technician. Expected resolution: today by 5 PM.",
        },
    ]

    group_messages = [
        {
            "group": "ML Platform Team (Arushi, Rahul, Sneha, Priya)",
            "sender": "Rahul Menon",
            "time": "9:30 AM",
            "message": "Quick reminder — demo to leadership is at 3 PM today. Please have your part ready. Arushi, can you show the RAG + agent flow?",
        },
        {
            "group": "Bangalore Office Buddies",
            "sender": "Priya Sharma",
            "time": "8:00 AM",
            "message": "Anyone up for lunch at the Prestige food court today? Thinking 1 PM.",
        },
        {
            "group": "Project Phoenix — Standup",
            "sender": "Sneha Kapoor",
            "time": "Yesterday 6:00 PM",
            "message": "Standup notes from yesterday shared in the channel. Please review blockers — 2 items need input from the team.",
        },
    ]

    return {"channels": channels, "direct_messages": direct_messages, "group_messages": group_messages}


def get_emails() -> list[dict]:
    # REAL API: imaplib / Gmail API / Microsoft Graph API
    return [
        {
            "from": "manager@aexp.com",
            "subject": "1:1 Agenda for this week",
            "time": "8:15 AM",
            "preview": "Hi, please add your discussion points to the shared doc before our 2 PM call today.",
            "unread": True,
        },
        {
            "from": "noreply@workday.com",
            "subject": "Action Required: Submit your Q2 Goals",
            "time": "7:00 AM",
            "preview": "Your Q2 goals are due by June 30. Log in to Workday to complete your submission.",
            "unread": True,
        },
        {
            "from": "it-security@aexp.com",
            "subject": "Your laptop security patch is ready",
            "time": "Yesterday 6:30 PM",
            "preview": "A critical security patch is available for your MacBook. Please install it at your next restart.",
            "unread": True,
        },
        {
            "from": "hr@aexp.com",
            "subject": "Your leave application LV-A1B2C3D4 has been approved",
            "time": "Yesterday 5:00 PM",
            "preview": "Your annual leave request for July 5–7 has been approved by your manager.",
            "unread": False,
        },
        {
            "from": "learning@aexp.com",
            "subject": "New course available: Generative AI for Engineers",
            "time": "Yesterday 9:00 AM",
            "preview": "A new L&D course on Generative AI has been added to the Learning Portal. Enroll before July 15.",
            "unread": False,
        },
    ]


def get_github_activity() -> dict:
    # REAL API: github.Github(GITHUB_TOKEN).get_user().get_notifications() / get_repos()
    return {
        "pull_requests": [
            {
                "repo": "amex/digital-workplace-platform",
                "pr_number": 247,
                "title": "Add retry logic to Kafka consumer",
                "author": "rahul-menon",
                "status": "Review Requested",
                "updated": "2 hours ago",
            },
            {
                "repo": "amex/ml-pipeline",
                "pr_number": 183,
                "title": "Upgrade embedding model to MiniLM-L12",
                "author": "you",
                "status": "Changes Requested",
                "updated": "Yesterday",
            },
        ],
        "assigned_issues": [
            {
                "repo": "amex/digital-workplace-platform",
                "issue_number": 312,
                "title": "ChromaDB retrieval latency spikes during peak hours",
                "priority": "High",
                "due": "Jul 3",
            },
            {
                "repo": "amex/ml-pipeline",
                "issue_number": 289,
                "title": "Add unit tests for ingest pipeline",
                "priority": "Medium",
                "due": "Jul 10",
            },
        ],
        "recent_commits": [
            {
                "repo": "amex/digital-workplace-platform",
                "message": "fix: handle None chunks in ChromaDB retriever",
                "time": "Yesterday 8:42 PM",
            },
            {
                "repo": "amex/digital-workplace-platform",
                "message": "feat: add TicketRaiser and FetchPassword agent tools",
                "time": "2 days ago",
            },
        ],
    }


def build_brief_summary(slack: dict, emails: list, github: dict) -> str:
    """Build a plain-text summary for the LLM to optionally reformat."""
    unread   = sum(1 for e in emails if e["unread"])
    prs      = len(github["pull_requests"])
    issues   = len(github["assigned_issues"])
    channels = len(slack["channels"])
    dms      = len(slack["direct_messages"])
    groups   = len(slack["group_messages"])
    return (
        f"Today is {TODAY}.\n"
        f"Slack: {channels} channel messages, {dms} direct messages, {groups} group messages.\n"
        f"Email: {unread} unread emails.\n"
        f"GitHub: {prs} open PRs (1 needs your review, 1 has changes requested), "
        f"{issues} assigned issues (1 high priority due Jul 3).\n"
        f"Key actions: Submit Q2 goals in Workday, review PR #247, "
        f"attend standup at 10:30 AM, prepare for 3 PM leadership demo, install laptop security patch."
    )
