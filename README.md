# NovaDesk AI — Intelligent Enterprise IT Helpdesk Agent

![IT Helpdesk Agent Motion Graphics Showcase](it_helpdesk_preview.gif)

An end-to-end IT Helpdesk management platform powered by **FastAPI**, **LangChain**, **Groq (`openai/gpt-oss-120b`)**, **Streamlit**, and **REST APIs**.


NovaDesk AI automatically classifies IT support requests, calculates ITIL-compliant SLA priorities, formulates step-by-step diagnostic procedures with copyable terminal commands, matches internal knowledge base runbooks, and creates trackable tickets via REST APIs.

---

## 🌟 Key Features

1. **⚡ AI Issue Classification & SLA Prioritization**:
   - **ITIL Category Mapping**: Automatically classifies inquiries into *Hardware*, *Software*, *Network & Connectivity*, *Identity & Access (IAM)*, *Security & Compliance*, *Email & Collaboration*, *Cloud & Infrastructure*, etc.
   - **Calculated Priorities**: Assigns **P1 Critical** (1h SLA), **P2 High** (4h SLA), **P3 Medium** (24h SLA), or **P4 Low** (48h SLA) based on urgency and impact.
   - **Target Queue Routing**: Identifies the appropriate department (e.g., *NetOps*, *SecOps*, *IAM*, *DevOps*, *Workstation Tech*).

2. **🛠️ Actionable Troubleshooting & Solutions**:
   - Generates sequential, step-by-step diagnostic actions tailored to the user's operating environment.
   - Provides ready-to-run terminal, PowerShell, or bash commands (e.g. `ipconfig /flushdns`, `manage-bde -status`, `taskkill /F /IM outlook.exe`).
   - Assesses whether the issue is self-resolvable or requires on-site technician escalation.

3. **🎟️ Complete Ticket Management REST APIs**:
   - Create tickets with automated or custom AI diagnostics (`POST /api/tickets`).
   - Query tickets with real-time text search, status filters, priority filters, and pagination (`GET /api/tickets`).
   - Detailed ticket timeline and internal technician work notes thread (`POST /api/tickets/{id}/comments`).
   - Ticket resolution lifecycle with root-cause logging (`POST /api/tickets/{id}/resolve`).
   - Interactive OpenAPI / Swagger UI at `/docs`.

4. **💬 Conversational IT Helpdesk Agent**:
   - Real-time chat with the AI Helpdesk Agent.
   - Simultaneous live diagnosis extraction: as you chat, the **Live AI Incident Diagnosis Card** dynamically updates on the right.
   - One-click **"Create Official Ticket From Diagnosis"** action.

5. **📚 Knowledge Base & Runbooks**:
   - Searchable library of standard operating procedures (SOPs) for VPN issues, MFA desync, BitLocker recovery, Outlook cache corruption, Docker socket errors, and docking station display glitches.

6. **📊 Operational SLA & Health Analytics**:
   - Tracks total tickets, active queues, critical SLA compliance, and category distribution.

---

## 🏗️ Architecture & Technology Stack

```
Chatbot/
├── app/
│   ├── __init__.py
│   ├── config.py             # Settings, env vars, Pydantic ConfigDict
│   ├── database.py           # SQLite repository, migrations, and seed data
│   ├── models.py             # Pydantic schemas for tickets, triage, chat, KB, stats
│   ├── agent.py              # LangChain IT Helpdesk Agent using Groq gpt-oss-120b
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── triage.py         # AI Triage & Classification endpoints (/api/triage)
│   │   ├── tickets.py        # Complete Ticket CRUD endpoints (/api/tickets)
│   │   ├── agent_chat.py     # Interactive IT Helpdesk Chatbot (/api/agent/chat)
│   │   ├── kb.py             # Knowledge Base API (/api/kb)
│   │   └── stats.py          # Real-time metrics & SLA compliance (/api/stats)
│   └── main.py               # FastAPI entry point & static file hosting
├── static/
│   ├── css/
│   │   └── style.css         # Modern animations, pulse indicators, scrollbars
│   ├── js/
│   │   └── app.js            # Single Page Application controller (Vanilla JS)
│   └── index.html            # Dark-mode dashboard (TailwindCSS + Lucide Icons)
├── tests/
│   ├── test_agent.py         # Agent diagnosis & fallback tests
│   ├── test_tickets_api.py   # FastAPI tickets API tests
│   └── test_triage_api.py    # Triage, KB, and stats tests
├── run.py                    # Server startup script
├── .env                      # Groq API Key and model configurations
└── requirements.txt          # Project dependencies
```

- **Backend**: FastAPI 0.115+, Uvicorn, Pydantic v2
- **AI / LLM Engine**: LangChain (`langchain-groq`), Groq API running `openai/gpt-oss-120b` (with automatic fallback to `openai/gpt-oss-20b` and heuristic rule-based engine)
- **Database**: SQLite with thread-safe connection pooling and automatic seeding
- **Frontend**: Responsive Single-Page Application (HTML5, TailwindCSS, Lucide Icons, Marked.js)
- **Testing**: Pytest & HTTPX TestClient (9 passing unit & integration tests)

---

## 🚀 Quickstart Guide

### 1. Environment Setup

Ensure Python 3.10+ is installed:

```bash
# Clone or navigate to the repository
cd /home/mike/Desktop/Chatbot

# Activate virtual environment
source .venv/bin/activate

# Install dependencies (if needed)
pip install -r requirements.txt
```

### 2. Configure Environment Variables

The `.env` file is already set up with your Groq API key:

```env
GROQ_API_KEY="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"
GROQ_MODEL="openai/gpt-oss-120b"
GROQ_FALLBACK_MODEL="openai/gpt-oss-20b"
APP_HOST="0.0.0.0"
APP_PORT=8000
DEBUG=True
```

### 3. Launch the Application

Run the server with Python:

```bash
python run.py
```
Or with Uvicorn directly:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Then open your browser at:
- **Web Dashboard**: [http://localhost:8000](http://localhost:8000)
- **Interactive OpenAPI Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 🧪 Running the Test Suite

Run the full pytest suite:

```bash
PYTHONPATH=. .venv/bin/pytest -v
```

All 9 test suites will verify:
- Rule-based & LLM issue diagnosis
- ITIL category and priority assignments
- Full ticket lifecycle: creation, filtering, comment addition, status patching, resolution
- Knowledge Base search and statistical analytics

---

## 📡 REST API Reference & Examples

### 1. Classify and Triage an Issue
```bash
curl -X POST "http://localhost:8000/api/triage/classify" \
  -H "Content-Type: application/json" \
  -d '{
    "issue_description": "GlobalProtect VPN timeout error 502 while connecting",
    "requester_name": "Sarah Connor",
    "system_info": "macOS Sonoma 14.5"
  }'
```

### 2. Create a Ticket with Automatic AI Diagnosis
```bash
curl -X POST "http://localhost:8000/api/tickets" \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Lenovo laptop blue screens with BitLocker prompt after BIOS update",
    "requester_name": "Marcus Vance",
    "requester_email": "m.vance@company.corp",
    "department": "Finance",
    "auto_diagnose": true
  }'
```

### 3. List Tickets with Filters
```bash
curl -X GET "http://localhost:8000/api/tickets?status=Open&priority=Critical"
```

### 4. Interactive Chat with Helpdesk Agent
```bash
curl -X POST "http://localhost:8000/api/agent/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "My Outlook calendar is refusing to sync new invites",
    "history": []
  }'
```

### 5. Mark Ticket as Resolved
```bash
curl -X POST "http://localhost:8000/api/tickets/1041/resolve?resolution_notes=Reconfigured+failover+BGP+gateway+route"
```
