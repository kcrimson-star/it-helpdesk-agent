# NovaDesk AI Helpdesk — Comprehensive 7-Page System Documentation

> **Font Specification:** Apple SF-Pro (`-apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text"`)  
> **Print Edition:** [DOCUMENTATION.html](file:///home/mike/Desktop/Chatbot/DOCUMENTATION.html) (Exact A4 7-Page Print & PDF Layout)  
> **Version:** 2.0.0  
> **Author:** NovaDesk Technical Architecture Group  

---

<!-- PAGE BREAK: PAGE 1 -->
## Page 1: Executive Overview & System Architecture

### 1.1 Project Synopsis & Mission
NovaDesk AI is a lightweight autonomous IT Helpdesk triage engine designed to ingest raw employee technical inquiries, perform instant classification, determine ITIL impact/urgency priority levels, produce verified step-by-step diagnostic procedures, and create structured tickets through programmatic REST APIs.

### 1.2 Architectural Blueprint
```
+-------------------------------------------------------------+
|                 PRESENTATION & CLIENT LAYER                 |
|   Streamlit Interface (streamlit_app.py) + React 18 Radar   |
+------------------------------+------------------------------+
                               | (HTTP / REST API Calls)
                               v
+-------------------------------------------------------------+
|                   REST API BACKEND GATEWAY                  |
|    FastAPI Microservices + Pydantic v2 Schema Validation     |
|       (POST /api/classify, POST /api/tickets, /health)      |
+------------------------------+------------------------------+
                               |
                               v
+-------------------------------------------------------------+
|                 AI AGENT ORCHESTRATION CORE                 |
|       LangChain Core + Groq LPU Inference Orchestrator      |
|             (Primary: openai/gpt-oss-120b Model)            |
+---------------+-----------------------------+---------------+
                |                             |
                | (Fallback if offline)       | (Database I/O)
                v                             v
+-------------------------------+ +---------------------------+
| DETERMINISTIC HEURISTIC RULES | |  SQLITE RELATIONAL STORE  |
| Regex / Keyword Safety Engine | | Tickets, KB & Work Notes  |
+-------------------------------+ +---------------------------+
```

### 1.3 Technology Stack Matrix
| Layer | Technology | Version | Purpose |
| :--- | :--- | :--- | :--- |
| **Backend REST API** | FastAPI + Uvicorn | 0.115.0 | Async endpoints, auto-generated OpenAPI Swagger docs |
| **AI Orchestration** | LangChain / LangChain-Groq | 0.3.0 | Prompt chains, structured output validation, guardrails |
| **Inference Model** | Groq LPU Cloud | API v1 | `openai/gpt-oss-120b` (sub-second inference speed) |
| **Frontend UI** | Streamlit | 1.65.0 | Multi-tab operational dashboard, ticket management |
| **Micro-Frontend** | React 18 + Babel | 18.2.0 | Embedded client-side live ticket status and radar |
| **Database** | SQLite 3 | WAL Mode | Atomic local storage for tickets and runbooks |

### 1.4 Core Architectural Tenets
1. **Zero-Latency Fallback Guarantee:** If Groq API rate limits or network blocks occur, a built-in deterministic heuristic rule engine immediately classifies the issue without dropping transactions.
2. **Strict ITIL Alignment:** Incidents are categorized across Urgency and Impact matrices to calculate SLA resolution targets (1h to 48h).

---

<!-- PAGE BREAK: PAGE 2 -->
## Page 2: AI Triage & Agent Intelligence Engine

### 2.1 Inference Pipeline
The primary cognitive engine utilizes **openai/gpt-oss-120b** hosted on Groq LPUs. The model delivers enterprise-grade reasoning capable of diagnosing complex IT scenarios in under 750 milliseconds.

### 2.2 System Prompt & Schema Guardrails
The agent is governed by strict system prompts enforcing pure JSON output conforming to the following specification:
```json
{
  "title": "Concise professional summary",
  "category": "Hardware | Software | Network & Connectivity | Identity & Access (IAM) | Security & Compliance",
  "sub_category": "Specific component (e.g. GlobalProtect VPN, BitLocker, Okta)",
  "priority": "Critical | High | Medium | Low",
  "urgency": "Critical | High | Medium | Low",
  "impact": "Company-wide | Department | Multiple Users | Single User",
  "estimated_sla_hours": 24,
  "assigned_department": "Target routing queue",
  "root_cause_hypothesis": "Technical diagnosis",
  "solutions": ["Step 1", "Step 2", "Step 3"],
  "quick_commands": ["diagnostic commands"]
}
```

### 2.3 ITIL Priority & SLA Calculation
| Priority | Trigger Criteria | SLA Target | Target Queue |
| :--- | :--- | :--- | :--- |
| **Critical (P1)** | Company-wide outage, Security breach, Ransomware | **1 Hour** | Endpoint SecOps |
| **High (P2)** | Department blocked, VPN gateway timeout | **4 Hours** | Network Engineering |
| **Medium (P3)** | Single user blocked, workaround available | **24 Hours** | Tier 1 Workstation Tech |
| **Low (P4)** | Informational request, minor software glitch | **48 Hours** | General IT Queue |

### 2.4 Deterministic Heuristic Fallback Engine
When external LLM inference is unreachable, [ITHelpDeskAgent.py](file:///home/mike/Desktop/Chatbot/ITHelpDeskAgent.py) executes keyword regex patterns:
- **Network & Connectivity:** Activated by `vpn`, `wifi`, `dns`, `timeout 502` $\rightarrow$ Priority **High**, outputs `ipconfig /flushdns`.
- **Identity & Access (IAM):** Activated by `mfa`, `okta`, `2fa`, `locked` $\rightarrow$ Priority **Medium**, outputs time-sync verification and TAP procedures.
- **Security & Compliance:** Activated by `bitlocker`, `ransomware`, `virus`, `bsod` $\rightarrow$ Priority **Critical**, outputs quarantine steps.
- **Hardware:** Activated by `dock`, `monitor`, `flicker`, `cable` $\rightarrow$ Priority **Medium**, outputs graphics reset shortcuts.

---

<!-- PAGE BREAK: PAGE 3 -->
## Page 3: FastAPI Backend & REST API Specification

### 3.1 Service Lifecycle Architecture
Implemented in [app/main.py](file:///home/mike/Desktop/Chatbot/app/main.py), the API runs on an asynchronous event loop with lifespan hooks that initialize the SQLite database schema, register CORS permissions, and mount static UI bundles.

### 3.2 Endpoint Reference Matrix
| Method | Path | Request Body | Description |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/classify` | `TriageRequest` | Run AI triage analysis and solution generation |
| `POST` | `/api/tickets` | `TicketCreate` | Create a ticket (auto-diagnoses if requested) |
| `GET` | `/api/tickets` | Query parameters | List tickets with filters (`status`, `priority`, `search`) |
| `GET` | `/api/tickets/{id}` | Path parameter | Retrieve single ticket with comments thread |
| `PATCH`| `/api/tickets/{id}` | `TicketUpdate` | Update status, priority, department, or assignee |
| `POST` | `/api/tickets/{id}/resolve`| Query parameter | Mark ticket resolved with official resolution notes |
| `POST` | `/api/tickets/{id}/comments`| `TicketCommentCreate`| Append technician work notes or user comments |
| `GET` | `/api/health` | None | Returns database and Groq engine health status |

### 3.3 Example API Payloads
**Request (`POST /api/tickets`):**
```json
{
  "title": "VPN Gateway Dropping",
  "description": "GlobalProtect times out every 5 minutes on home Wi-Fi",
  "category": "Network & Connectivity",
  "priority": "High",
  "requester_name": "Marcus Vance",
  "auto_diagnose": false
}
```

**Response (`HTTP 201 Created`):**
```json
{
  "id": 50,
  "ticket_code": "HD-1076",
  "title": "VPN Gateway Dropping",
  "status": "Open",
  "assigned_to": "Escalations Team",
  "sla_deadline": "2026-10-29T15:00:00Z",
  "created_at": "2026-10-29T11:00:00Z"
}
```

---

<!-- PAGE BREAK: PAGE 4 -->
## Page 4: Streamlit UI & React 18 Integration

### 4.1 Hybrid Presentation Layer
The frontend ([streamlit_app.py](file:///home/mike/Desktop/Chatbot/streamlit_app.py)) bridges Python server-side reactivity with client-side React 18 component execution via `streamlit.components.v1.html`.

### 4.2 Multi-Tab Architecture
- **Tab 1: AI Issue Classifier & Solutions**
  - Pre-populated test scenario buttons (VPN timeout, Okta MFA, Dock flickering, BitLocker).
  - Problem intake form with requester identification.
  - Formatted diagnosis cards with color-coded priority pills and terminal command copy blocks.
  - Direct 1-click button to dispatch a ticket to the REST API.
- **Tab 2: Ticket Management Dashboard**
  - Live query results reflecting the database state.
  - Multi-criteria filtering by Status (Open, In Progress, Resolved) and Priority.
  - Expandable accordion cards displaying solutions and requester information.
  - Interactive "Mark Resolved" triggers.
- **Tab 3: Interactive React 18 Radar Widget**
  - Self-contained React 18 component compiled in-browser with standalone Babel.
  - Implements dynamic `useState` management for instant client-side filtering.
  - Real-time incident simulator button adding synthetic incidents to the DOM without triggering Streamlit server refreshes.

### 4.3 Client-Side React 18 Code Architecture
```jsx
const { useState } = React;
function HelpdeskRadar() {
  const [incidents, setIncidents] = useState(initialIncidents);
  const [filter, setFilter] = useState("All");

  const toggleStatus = (id) => {
    setIncidents(incidents.map(inc => 
      inc.id === id ? { ...inc, status: inc.status === "Active" ? "Resolved" : "Active" } : inc
    ));
  };
  // Real-time render loop inside Streamlit iframe
}
```

---

<!-- PAGE BREAK: PAGE 5 -->
## Page 5: Data Layer & Knowledge Base Subsystem

### 5.1 SQLite Persistence Engine
Implemented in [app/database.py](file:///home/mike/Desktop/Chatbot/app/database.py), the data layer operates on a local SQLite 3 database (`data/helpdesk.db`) configured with Write-Ahead Logging (WAL) for concurrent read-write performance.

### 5.2 Database Schema
```sql
CREATE TABLE tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_code TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    category TEXT NOT NULL,
    priority TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'Open',
    requester_name TEXT NOT NULL,
    requester_email TEXT NOT NULL,
    department TEXT NOT NULL,
    assigned_to TEXT,
    solutions TEXT,       -- Stored as JSON array
    quick_commands TEXT,  -- Stored as JSON array
    sla_deadline TEXT,
    created_at TEXT NOT NULL,
    resolved_at TEXT
);

CREATE TABLE ticket_comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id INTEGER NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
    author_name TEXT NOT NULL,
    author_type TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE kb_articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    category TEXT NOT NULL,
    tags TEXT NOT NULL,   -- Stored as JSON array
    summary TEXT NOT NULL,
    content TEXT NOT NULL,
    quick_commands TEXT,
    created_at TEXT NOT NULL
);
```

### 5.3 Pre-Seeded Standard Operating Procedures (Runbooks)
1. **GlobalProtect VPN Gateway Failures:** DNS cache purging, gateway split-tunnel route validation.
2. **Okta / Entra ID MFA Device Desync:** TOTP clock-drift correction, Temporary Access Pass (TAP) workflows.
3. **BitLocker Drive Encryption:** Microsoft Intune 48-digit key extraction, TPM register re-binding.
4. **Outlook OST Cache Stalls:** Outlook safe mode switch (`outlook.exe /safe`), cache container rebuilds.

---

<!-- PAGE BREAK: PAGE 6 -->
## Page 6: Verification & Testing Methodology

### 6.1 Quality Assurance Architecture
The test suite utilizes **Pytest** with **FastAPI TestClient** across 5 distinct test modules, validating the entire operational envelope in both offline fallback mode and live LLM integration mode.

### 6.2 Test Suite Inventory (16 Passing Tests)
| Test Suite | File | Verified Behaviors |
| :--- | :--- | :--- |
| **Simple Helpdesk** | `test_simple_helpdesk.py` | Direct `/api/classify` route, fallback rules, ticket creation |
| **Ticket REST API** | `test_tickets_api.py` | Health check, ticket CRUD, query filters, resolution notes |
| **Triage API** | `test_triage_api.py` | Issue classification, KPI stats calculation, KB query retrieval |
| **Agent Heuristics** | `test_agent.py` | Rule-based classifications, JSON regex parser, Markdown cleanup |
| **End-to-End** | `test_e2e.py` | Static UI delivery, multi-step ticket lifecycles, chat assistant |

### 6.3 Test Execution Log
```bash
$ PYTHONPATH=. .venv/bin/pytest
============================= test session starts ==============================
collected 16 items

tests/test_agent.py ..                                                   [ 12%]
tests/test_e2e.py ...                                                    [ 31%]
tests/test_simple_helpdesk.py ....                                       [ 56%]
tests/test_tickets_api.py ....                                           [ 81%]
tests/test_triage_api.py ...                                             [100%]

============================== 16 passed in 1.10s ==============================
```

---

<!-- PAGE BREAK: PAGE 7 -->
## Page 7: Deployment & Operations Runbook

### 7.1 Configuration Management (.env)
```ini
GROQ_API_KEY="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"
GROQ_MODEL="openai/gpt-oss-120b"
GROQ_FALLBACK_MODEL="llama-3.3-70b-versatile"
APP_HOST="0.0.0.0"
APP_PORT=8000
DEBUG=False
API_BASE_URL="http://localhost:8000/api"
```

### 7.2 Service Startup Runbook

#### 1. Launch FastAPI Backend
```bash
python3 run.py
```
- API Base URL: `http://localhost:8000`
- Interactive OpenAPI Docs: `http://localhost:8000/docs`
- Health Endpoint: `http://localhost:8000/api/health`

#### 2. Launch Streamlit UI
```bash
.venv/bin/streamlit run streamlit_app.py
```
- User Interface: `http://localhost:8501`

### 7.3 Operational Troubleshooting
- **Address Already in Use (Port 8000):** Kill the stale process via `fuser -k 8000/tcp` before launching.
- **Groq API Rate Limits (429):** The application automatically falls back to secondary models or offline deterministic heuristics.
- **Database Access Issues:** Ensure write permissions exist on the `data/` directory.

### 7.4 Future Architecture Roadmap
- **Containerization:** Multi-stage `Dockerfile` and `docker-compose.yml` for unified microservice deployment.
- **Vector Search:** Transition SQLite KB matching to ChromaDB / FAISS dense embeddings.
- **Incident Webhooks:** Dispatch automated real-time alerts to Slack and Microsoft Teams channels.
