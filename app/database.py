import sqlite3
import json
import os
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional, Tuple
from app.config import settings

def now_utc() -> datetime:
    return datetime.now(timezone.utc)

def get_db_connection() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(settings.DATABASE_PATH), exist_ok=True)
    conn = sqlite3.connect(settings.DATABASE_PATH, timeout=10.0)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Tickets Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tickets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ticket_code TEXT UNIQUE NOT NULL,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        category TEXT NOT NULL,
        sub_category TEXT,
        priority TEXT NOT NULL,
        urgency TEXT DEFAULT 'Medium',
        impact TEXT DEFAULT 'Single User',
        status TEXT NOT NULL DEFAULT 'Open',
        requester_name TEXT NOT NULL,
        requester_email TEXT NOT NULL,
        department TEXT DEFAULT 'Operations',
        assigned_to TEXT,
        solutions_json TEXT,
        quick_commands_json TEXT,
        ai_analysis_json TEXT,
        resolution_notes TEXT,
        sla_deadline TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        resolved_at TEXT
    );
    """)

    # Comments Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ticket_comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ticket_id INTEGER NOT NULL,
        author_name TEXT NOT NULL,
        author_type TEXT NOT NULL, -- 'user', 'agent', 'system'
        content TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (ticket_id) REFERENCES tickets(id) ON DELETE CASCADE
    );
    """)

    # Knowledge Base Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS knowledge_base (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        category TEXT NOT NULL,
        tags_json TEXT,
        summary TEXT NOT NULL,
        content TEXT NOT NULL,
        quick_commands_json TEXT,
        created_at TEXT NOT NULL
    );
    """)

    conn.commit()

    # Check if seeds needed
    cursor.execute("SELECT COUNT(*) as count FROM knowledge_base")
    if cursor.fetchone()["count"] == 0:
        _seed_knowledge_base(cursor)

    cursor.execute("SELECT COUNT(*) as count FROM tickets")
    if cursor.fetchone()["count"] == 0:
        _seed_tickets(cursor)

    conn.commit()
    conn.close()

def _seed_knowledge_base(cursor: sqlite3.Cursor):
    now = now_utc().isoformat()
    articles = [
        (
            "Troubleshooting Corporate VPN (GlobalProtect / AnyConnect) Connection Failures",
            "Network & Connectivity",
            json.dumps(["vpn", "network", "remote-access", "dns"]),
            "Step-by-step diagnostic procedures for SSL-VPN timeouts, gateway unreachable, and split-tunnel DNS issues.",
            """### Common Symptoms:
- Client hangs at 'Connecting...' (Status 502 / Gateway unreachable)
- Connected to VPN but internal intranet/DNS unreachable
- Multi-factor authentication token fails to register

### Resolution Sequence:
1. **Flush local DNS cache and renew DHCP lease**:
   Clear corrupt hostname caches that prevent resolving internal split-tunnel gateways.
2. **Restart Virtual Network Adapter**:
   Disable and re-enable the virtual TAP/TUN interface.
3. **Verify Date & Time Sync**:
   Mismatched system clocks break SSL handshake certificates and TOTP tokens.
4. **Proxy Conflict**:
   Ensure corporate PAC file or local proxy 127.0.0.1:8080 is bypassed.""",
            json.dumps(["ipconfig /flushdns", "ipconfig /release && ipconfig /renew", "netsh winsock reset", "sudo systemctl restart NetworkManager"]),
            now
        ),
        (
            "Okta / Entra ID MFA Device Lost or Push Notification Not Arriving",
            "Identity & Access (IAM)",
            json.dumps(["mfa", "2fa", "okta", "entra", "sso", "login"]),
            "Procedures to re-enroll authenticator app, clear stale sessions, and trigger admin temporary bypass passcodes.",
            """### Immediate Self-Service Steps:
1. Verify phone is connected to cellular data or Wi-Fi with push notification permissions enabled.
2. Ensure device system time is set to 'Automatic' (time drift > 60s invalidates TOTP tokens).
3. If device was replaced or reset:
   - Use backup SMS or hardware FIDO2 key if pre-registered.
   - If no secondary method exists, Helpdesk technician must verify employee identity via video verification before issuing a Temporary Access Pass (TAP).""",
            json.dumps(["klist purge", "az account clear"]),
            now
        ),
        (
            "Outlook & Microsoft 365 Exchange Synchronization Stalls",
            "Email & Collaboration",
            json.dumps(["outlook", "exchange", "office365", "email", "cache"]),
            "Resolving stuck Outbox messages, disconnected status, and corrupt .OST cache files.",
            """### Resolution Steps:
1. **Start Outlook in Safe Mode**:
   Test whether faulty add-ins (e.g., Salesforce, Zoom, Acrobat) cause the freeze.
2. **Rebuild Outlook Cached Exchange Mode Data**:
   Rename or delete the local `.ost` file to trigger a clean sync from the Exchange cloud server.
3. **Run Quick Office Repair**:
   Go to Windows Settings -> Installed Apps -> Microsoft 365 Apps -> Modify -> Quick Repair.""",
            json.dumps(["outlook.exe /safe", "taskkill /F /IM outlook.exe"]),
            now
        ),
        (
            "Windows BitLocker Recovery Key Prompt on Startup",
            "Security & Compliance",
            json.dumps(["bitlocker", "encryption", "tpm", "bios", "boot"]),
            "How to locate your BitLocker recovery key and reset TPM PCR validation registers.",
            """### Recovery Key Retrieval:
1. Employees can self-service retrieve keys at `https://myaccount.microsoft.com/device-list` using mobile device.
2. If triggered by BIOS update or docking station hardware signature change:
   - Enter 48-digit numerical recovery key.
   - Once inside Windows, suspend and resume BitLocker protection to re-bind TPM PCR registers: `Manage-bde -protectors -disable C:` followed by `Manage-bde -protectors -enable C:`.""",
            json.dumps(["manage-bde -status", "manage-bde -protectors -disable C:", "manage-bde -protectors -enable C:"]),
            now
        ),
        (
            "Local Docker Engine Socket Permission & Daemon Failure",
            "Cloud & Infrastructure",
            json.dumps(["docker", "devops", "linux", "containers", "wsl2"]),
            "Resolving 'Cannot connect to the Docker daemon at unix:///var/run/docker.sock' for developers.",
            """### Troubleshooting:
1. Verify user belongs to the `docker` usergroup:
   `sudo usermod -aG docker $USER` and log out/in.
2. Check systemd daemon service:
   `sudo systemctl status docker`
3. For WSL2 on Windows: Restart WSL host via `wsl --shutdown` from PowerShell.""",
            json.dumps(["sudo systemctl restart docker", "sudo usermod -aG docker $USER", "wsl --shutdown"]),
            now
        ),
        (
            "Workstation Display Flickering & Docking Station HDMI/DP Blackouts",
            "Hardware",
            json.dumps(["hardware", "monitor", "dock", "displayport", "hdmi", "usb-c"]),
            "Resolving Thunderbolt / USB-C docking station multi-monitor flicker and power delivery failures.",
            """### Troubleshooting:
1. **Power Cycle Docking Station**:
   Unplug the dock power adapter, wait 30 seconds to drain capacitors, plug back in.
2. **Display Frequency Refresh Rate**:
   Lower monitor refresh rate from 144Hz/120Hz to 60Hz in Display Settings.
3. **Graphics Driver Restart Shortcut**:
   Press `Win + Ctrl + Shift + B` to trigger an immediate GPU driver reset without rebooting.
4. **Firmware Update**: Check Lenovo Vantage / Dell Command Update for Dock firmware.""",
            json.dumps(["Win + Ctrl + Shift + B (Keyboard Shortcut)"]),
            now
        )
    ]
    cursor.executemany("""
    INSERT INTO knowledge_base (title, category, tags_json, summary, content, quick_commands_json, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, articles)

def _seed_tickets(cursor: sqlite3.Cursor):
    now = now_utc()
    seeds = [
        {
            "ticket_code": "HD-1041",
            "title": "GlobalProtect VPN Gateway Timeout 502 for Engineering Team",
            "description": "Multiple engineers in the East Coast hub cannot connect to the primary internal gateway. Logs show timeout after 60s handshake.",
            "category": "Network & Connectivity",
            "sub_category": "VPN",
            "priority": "High",
            "urgency": "High",
            "impact": "Multiple Users",
            "status": "In Progress",
            "requester_name": "Sarah Connor",
            "requester_email": "s.connor@cyberdyne.io",
            "department": "Platform Engineering",
            "assigned_to": "Alex Chen (NetOps)",
            "solutions": [
                "Switch gateway endpoint from us-east.vpn.company.com to us-central-failover.vpn.company.com",
                "Flush local DNS cache and verify port 443 connectivity to failover cluster",
                "NetOps is checking border BGP router interface saturation"
            ],
            "quick_commands": ["ipconfig /flushdns", "curl -Iv https://us-east.vpn.company.com:443"],
            "ai_analysis": {
                "title": "GlobalProtect VPN Gateway Timeout",
                "category": "Network & Connectivity",
                "priority": "High",
                "department": "Network Engineering",
                "estimated_sla_hours": 4
            },
            "sla_deadline": (now + timedelta(hours=3)).isoformat(),
            "created_at": (now - timedelta(hours=1)).isoformat(),
            "updated_at": (now - timedelta(minutes=20)).isoformat(),
            "comments": [
                ("Alex Chen", "agent", "Investigating East Coast BGP gateway peering. Failover route has been activated for priority users."),
                ("Sarah Connor", "user", "Failover gateway worked! Waiting for root cause on primary.")
            ]
        },
        {
            "ticket_code": "HD-1042",
            "title": "MFA Authenticator Push Token Reset after Phone Replacement",
            "description": "Upgraded to iPhone 16 Pro, previous authenticator app backup was not enabled. Cannot log into corporate Workday or Slack.",
            "category": "Identity & Access (IAM)",
            "sub_category": "MFA",
            "priority": "Medium",
            "urgency": "Medium",
            "impact": "Single User",
            "status": "Open",
            "requester_name": "Marcus Vance",
            "requester_email": "m.vance@company.com",
            "department": "Marketing",
            "assigned_to": "Tier 1 Helpdesk",
            "solutions": [
                "Verify identity with manager confirmation or employee badge scan",
                "Generate a 24-hour Temporary Access Pass (TAP) in Entra ID Admin Console",
                "Prompt user to register Microsoft Authenticator on new hardware"
            ],
            "quick_commands": [],
            "ai_analysis": {
                "title": "MFA Push Token Reset",
                "category": "Identity & Access (IAM)",
                "priority": "Medium",
                "department": "IAM Support",
                "estimated_sla_hours": 24
            },
            "sla_deadline": (now + timedelta(hours=22)).isoformat(),
            "created_at": (now - timedelta(hours=2)).isoformat(),
            "updated_at": (now - timedelta(hours=2)).isoformat(),
            "comments": [
                ("System", "system", "Ticket ingested via AI Helpdesk Triage. Priority assigned based on single-user identity lockout.")
            ]
        },
        {
            "ticket_code": "HD-1043",
            "title": "Critical: BitLocker PIN lock loop following BIOS 1.18.0 update",
            "description": "Lenovo ThinkPad X1 Carbon booted into BitLocker recovery blue screen after scheduled automated BIOS patch. Recovery key entered but loops back on restart.",
            "category": "Security & Compliance",
            "sub_category": "BitLocker / TPM",
            "priority": "Critical",
            "urgency": "Critical",
            "impact": "Single User",
            "status": "In Progress",
            "requester_name": "Elena Rostova",
            "requester_email": "e.rostova@finance.corp",
            "department": "Finance (CFO)",
            "assigned_to": "David Miller (SecOps)",
            "solutions": [
                "Boot into Windows Recovery Command Prompt with 48-digit BitLocker recovery key",
                "Run 'manage-bde -protectors -disable C:' to pause TPM PCR checks",
                "Reboot to desktop, verify Windows Update integrity, and re-enable TPM binding: 'manage-bde -protectors -enable C:'"
            ],
            "quick_commands": ["manage-bde -protectors -disable C:", "manage-bde -protectors -enable C:"],
            "ai_analysis": {
                "title": "BitLocker Boot Loop",
                "category": "Security & Compliance",
                "priority": "Critical",
                "department": "Endpoint Security",
                "estimated_sla_hours": 1
            },
            "sla_deadline": (now + timedelta(minutes=45)).isoformat(),
            "created_at": (now - timedelta(minutes=15)).isoformat(),
            "updated_at": (now - timedelta(minutes=5)).isoformat(),
            "comments": [
                ("David Miller", "agent", "Connecting via emergency phone call. Disabling PCR 7 check in UEFI settings.")
            ]
        },
        {
            "ticket_code": "HD-1044",
            "title": "Docking Station Dual Monitors Blacking Out Intermittently",
            "description": "Dell WD19TBS dock causes both external DisplayPort monitors to go black for 3 seconds every 5 minutes while connected to Zoom calls.",
            "category": "Hardware",
            "sub_category": "Docking Station",
            "priority": "Low",
            "urgency": "Low",
            "impact": "Single User",
            "status": "Resolved",
            "requester_name": "Jordan Bell",
            "requester_email": "j.bell@design.studio",
            "department": "Design",
            "assigned_to": "Tier 1 Helpdesk",
            "solutions": [
                "Updated Dell Dock firmware to version 01.00.25 via Dell Command Update",
                "Lowered secondary monitor refresh rate from 144Hz to 60Hz to reduce DisplayPort MST bandwidth",
                "Replaced generic DP cable with certified VESA DisplayPort 1.4 cable"
            ],
            "quick_commands": ["Win + Ctrl + Shift + B"],
            "ai_analysis": {
                "title": "Docking Station Monitor Flickering",
                "category": "Hardware",
                "priority": "Low",
                "department": "Workstation Tech",
                "estimated_sla_hours": 48
            },
            "sla_deadline": (now - timedelta(hours=10)).isoformat(),
            "created_at": (now - timedelta(days=2)).isoformat(),
            "updated_at": (now - timedelta(hours=5)).isoformat(),
            "resolved_at": (now - timedelta(hours=5)).isoformat(),
            "resolution_notes": "Resolved by firmware flash and setting refresh rate to 60Hz. Tested with user for 1 hour without blackout.",
            "comments": [
                ("Tier 1 Helpdesk", "agent", "Firmware flashed successfully. User confirmed stable video signal.")
            ]
        }
    ]

    for item in seeds:
        cursor.execute("""
        INSERT INTO tickets (
            ticket_code, title, description, category, sub_category, priority, urgency, impact,
            status, requester_name, requester_email, department, assigned_to,
            solutions_json, quick_commands_json, ai_analysis_json, resolution_notes,
            sla_deadline, created_at, updated_at, resolved_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            item["ticket_code"], item["title"], item["description"], item["category"],
            item.get("sub_category"), item["priority"], item.get("urgency", "Medium"),
            item.get("impact", "Single User"), item["status"], item["requester_name"],
            item["requester_email"], item["department"], item.get("assigned_to"),
            json.dumps(item.get("solutions", [])), json.dumps(item.get("quick_commands", [])),
            json.dumps(item.get("ai_analysis", {})), item.get("resolution_notes"),
            item.get("sla_deadline"), item["created_at"], item["updated_at"],
            item.get("resolved_at")
        ))
        ticket_id = cursor.lastrowid
        for author, atype, content in item.get("comments", []):
            cursor.execute("""
            INSERT INTO ticket_comments (ticket_id, author_name, author_type, content, created_at)
            VALUES (?, ?, ?, ?, ?)
            """, (ticket_id, author, atype, content, item["updated_at"]))

def _row_to_ticket_dict(row: sqlite3.Row, comments: List[Dict[str, Any]] = None) -> Dict[str, Any]:
    solutions = json.loads(row["solutions_json"]) if row["solutions_json"] else []
    quick_commands = json.loads(row["quick_commands_json"]) if row["quick_commands_json"] else []
    ai_analysis = json.loads(row["ai_analysis_json"]) if row["ai_analysis_json"] else None
    
    return {
        "id": row["id"],
        "ticket_code": row["ticket_code"],
        "title": row["title"],
        "description": row["description"],
        "category": row["category"],
        "sub_category": row["sub_category"],
        "priority": row["priority"],
        "urgency": row["urgency"],
        "impact": row["impact"],
        "status": row["status"],
        "requester_name": row["requester_name"],
        "requester_email": row["requester_email"],
        "department": row["department"],
        "assigned_to": row["assigned_to"],
        "solutions": solutions,
        "quick_commands": quick_commands,
        "ai_analysis": ai_analysis,
        "resolution_notes": row["resolution_notes"],
        "sla_deadline": row["sla_deadline"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "resolved_at": row["resolved_at"],
        "comments": comments or []
    }

def get_ticket(ticket_id: int) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None
    
    cursor.execute("SELECT * FROM ticket_comments WHERE ticket_id = ? ORDER BY id ASC", (ticket_id,))
    comment_rows = cursor.fetchall()
    comments = [
        {
            "id": c["id"],
            "ticket_id": c["ticket_id"],
            "author_name": c["author_name"],
            "author_type": c["author_type"],
            "content": c["content"],
            "created_at": c["created_at"]
        } for c in comment_rows
    ]
    conn.close()
    return _row_to_ticket_dict(row, comments)

def get_ticket_by_code(code: str) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM tickets WHERE ticket_code = ?", (code,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return get_ticket(row["id"])
    return None

def list_tickets(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    category: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 500,
    offset: int = 0,
    sort_by: str = "newest",
    **kwargs
) -> Tuple[List[Dict[str, Any]], int]:

    conn = get_db_connection()
    cursor = conn.cursor()

    conditions = []
    params = []

    if status and status.lower() != "all":
        conditions.append("status = ?")
        params.append(status)

    if priority and priority.lower() != "all":
        conditions.append("priority = ?")
        params.append(priority)

    if category and category.lower() != "all":
        conditions.append("category = ?")
        params.append(category)

    if search and search.strip():
        term = f"%{search.strip()}%"
        conditions.append("(ticket_code LIKE ? OR title LIKE ? OR description LIKE ? OR requester_name LIKE ? OR department LIKE ?)")
        params.extend([term, term, term, term, term])

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    cursor.execute(f"SELECT COUNT(*) as total FROM tickets {where_clause}", params)
    total = cursor.fetchone()["total"]

    if sort_by == "priority":
        order_clause = """
        ORDER BY 
            CASE priority 
                WHEN 'Critical' THEN 1 
                WHEN 'High' THEN 2 
                WHEN 'Medium' THEN 3 
                WHEN 'Low' THEN 4 
                ELSE 5 
            END ASC,
            id DESC
        """
    else:
        order_clause = "ORDER BY id DESC"

    query = f"""
    SELECT * FROM tickets
    {where_clause}
    {order_clause}
    LIMIT ? OFFSET ?
    """
    cursor.execute(query, params + [limit, offset])
    rows = cursor.fetchall()
    tickets = [_row_to_ticket_dict(r) for r in rows]
    conn.close()
    return tickets, total


def create_ticket(data: Dict[str, Any]) -> Dict[str, Any]:
    conn = get_db_connection()
    cursor = conn.cursor()
    now = now_utc()

    # Generate guaranteed unique ticket code
    cursor.execute("SELECT ticket_code FROM tickets")
    rows = cursor.fetchall()
    max_num = 1040
    for r in rows:
        code = r["ticket_code"]
        if code and code.startswith("HD-"):
            num_part = code[3:]
            if num_part.isdigit():
                max_num = max(max_num, int(num_part))
    ticket_code = f"HD-{max_num + 1}"

    solutions_json = json.dumps(data.get("solutions", []))
    quick_commands_json = json.dumps(data.get("quick_commands", []))
    ai_analysis_json = json.dumps(data.get("ai_analysis")) if data.get("ai_analysis") else None

    # Calculate SLA deadline based on priority if not provided
    priority = data.get("priority", "Medium")
    sla_hours = 24
    if priority == "Critical":
        sla_hours = 1
    elif priority == "High":
        sla_hours = 4
    elif priority == "Low":
        sla_hours = 48
    
    sla_deadline = data.get("sla_deadline") or (now + timedelta(hours=sla_hours)).isoformat()
    created_at = now.isoformat()
    updated_at = created_at

    cursor.execute("""
    INSERT INTO tickets (
        ticket_code, title, description, category, sub_category, priority, urgency, impact,
        status, requester_name, requester_email, department, assigned_to,
        solutions_json, quick_commands_json, ai_analysis_json, resolution_notes,
        sla_deadline, created_at, updated_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        ticket_code,
        data.get("title", "IT Helpdesk Ticket"),
        data["description"],
        data.get("category", "Other / General IT"),
        data.get("sub_category", "General"),
        priority,
        data.get("urgency", "Medium"),
        data.get("impact", "Single User"),
        data.get("status", "Open"),
        data.get("requester_name", "Employee"),
        data.get("requester_email", "employee@company.local"),
        data.get("department", "Operations"),
        data.get("assigned_to", "IT Helpdesk Queue"),
        solutions_json,
        quick_commands_json,
        ai_analysis_json,
        data.get("resolution_notes"),
        sla_deadline,
        created_at,
        updated_at
    ))
    new_id = cursor.lastrowid

    # Add initial creation system comment
    cursor.execute("""
    INSERT INTO ticket_comments (ticket_id, author_name, author_type, content, created_at)
    VALUES (?, 'System', 'system', 'Ticket created and queued. AI diagnosis applied.', ?)
    """, (new_id, created_at))

    conn.commit()
    conn.close()
    return get_ticket(new_id)

def update_ticket(ticket_id: int, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,))
    existing = cursor.fetchone()
    if not existing:
        conn.close()
        return None

    now = now_utc().isoformat()
    fields = []
    params = []

    for key, val in updates.items():
        if val is not None and key in [
            "title", "category", "sub_category", "priority", "status",
            "assigned_to", "department", "resolution_notes", "urgency", "impact"
        ]:
            fields.append(f"{key} = ?")
            params.append(val)
            if key == "status":
                if val == "Resolved":
                    fields.append("resolved_at = ?")
                    params.append(now)
                elif val in ["Open", "In Progress", "Pending"]:
                    fields.append("resolved_at = NULL")


    if not fields:
        conn.close()
        return get_ticket(ticket_id)

    fields.append("updated_at = ?")
    params.append(now)
    params.append(ticket_id)

    query = f"UPDATE tickets SET {', '.join(fields)} WHERE id = ?"
    cursor.execute(query, params)
    conn.commit()
    conn.close()
    return get_ticket(ticket_id)

def add_ticket_comment(ticket_id: int, author_name: str, author_type: str, content: str) -> Dict[str, Any]:
    conn = get_db_connection()
    cursor = conn.cursor()
    now = now_utc().isoformat()

    cursor.execute("""
    INSERT INTO ticket_comments (ticket_id, author_name, author_type, content, created_at)
    VALUES (?, ?, ?, ?, ?)
    """, (ticket_id, author_name, author_type, content, now))
    comment_id = cursor.lastrowid

    cursor.execute("UPDATE tickets SET updated_at = ? WHERE id = ?", (now, ticket_id))
    conn.commit()
    conn.close()

    return {
        "id": comment_id,
        "ticket_id": ticket_id,
        "author_name": author_name,
        "author_type": author_type,
        "content": content,
        "created_at": now
    }

def delete_ticket(ticket_id: int) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM ticket_comments WHERE ticket_id = ?", (ticket_id,))
    cursor.execute("DELETE FROM tickets WHERE id = ?", (ticket_id,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted

def get_stats() -> Dict[str, Any]:
    conn = get_db_connection()
    cursor = conn.cursor()
    now = now_utc().isoformat()

    cursor.execute("SELECT COUNT(*) as total FROM tickets")
    total = cursor.fetchone()["total"]

    cursor.execute("SELECT status, COUNT(*) as count FROM tickets GROUP BY status")
    status_counts = {r["status"]: r["count"] for r in cursor.fetchall()}

    cursor.execute("SELECT priority, COUNT(*) as count FROM tickets GROUP BY priority")
    priority_counts = {r["priority"]: r["count"] for r in cursor.fetchall()}

    cursor.execute("SELECT category, COUNT(*) as count FROM tickets GROUP BY category")
    category_counts = {r["category"]: r["count"] for r in cursor.fetchall()}

    cursor.execute("""
    SELECT COUNT(*) as count FROM tickets 
    WHERE status NOT IN ('Resolved', 'Closed') AND sla_deadline < ?
    """, (now,))
    sla_breached = cursor.fetchone()["count"]

    open_count = status_counts.get("Open", 0)
    in_progress_count = status_counts.get("In Progress", 0)
    resolved_count = status_counts.get("Resolved", 0) + status_counts.get("Closed", 0)

    compliance_rate = 100.0
    if total > 0:
        compliance_rate = round(max(0.0, ((total - sla_breached) / total) * 100), 1)

    conn.close()
    return {
        "total_tickets": total,
        "open_tickets": open_count,
        "in_progress_tickets": in_progress_count,
        "resolved_tickets": resolved_count,
        "critical_tickets": priority_counts.get("Critical", 0),
        "high_tickets": priority_counts.get("High", 0),
        "sla_breached": sla_breached,
        "sla_compliance_rate": compliance_rate,
        "by_category": category_counts,
        "by_priority": priority_counts,
        "by_status": status_counts
    }

def search_kb(query: Optional[str] = None, category: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    conditions = []
    params = []

    if category and category.lower() != "all":
        conditions.append("category = ?")
        params.append(category)

    if query and query.strip():
        term = f"%{query.strip()}%"
        conditions.append("(title LIKE ? OR summary LIKE ? OR content LIKE ? OR tags_json LIKE ?)")
        params.extend([term, term, term, term])

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    cursor.execute(f"SELECT * FROM knowledge_base {where_clause} ORDER BY id ASC", params)
    rows = cursor.fetchall()
    results = []
    for r in rows:
        results.append({
            "id": r["id"],
            "title": r["title"],
            "category": r["category"],
            "tags": json.loads(r["tags_json"]) if r["tags_json"] else [],
            "summary": r["summary"],
            "content": r["content"],
            "quick_commands": json.loads(r["quick_commands_json"]) if r["quick_commands_json"] else [],
            "created_at": r["created_at"]
        })
    conn.close()
    return results

def get_kb_article(article_id: int) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM knowledge_base WHERE id = ?", (article_id,))
    r = cursor.fetchone()
    conn.close()
    if not r:
        return None
    return {
        "id": r["id"],
        "title": r["title"],
        "category": r["category"],
        "tags": json.loads(r["tags_json"]) if r["tags_json"] else [],
        "summary": r["summary"],
        "content": r["content"],
        "quick_commands": json.loads(r["quick_commands_json"]) if r["quick_commands_json"] else [],
        "created_at": r["created_at"]
    }
