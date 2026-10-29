import os
import json
import requests
import pandas as pd
import numpy as np
import streamlit as st
from dotenv import load_dotenv
import ITHelpDeskAgent
from app.database import (
    list_tickets, get_stats, create_ticket, update_ticket, delete_ticket, search_kb
)

load_dotenv()

st.set_page_config(
    page_title="HelpDesk - Command Center",
    layout="wide",
    initial_sidebar_state="expanded"
)

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api")

st.markdown("""
<style>
    .stApp {
        background-color: #0b0f19;
        color: #f1f5f9;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    [data-testid="stSidebar"] {
        background-color: #0e1424;
        border-right: 1px solid #1a233a;
    }
    .metric-box {
        background: #131b2e;
        border: 1px solid #1e293b;
        border-radius: 10px;
        padding: 14px 16px;
        margin-bottom: 10px;
    }
    .metric-box-title {
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #94a3b8;
        font-weight: 600;
        margin-bottom: 4px;
    }
    .metric-box-value {
        font-size: 22px;
        font-weight: 700;
        color: #f8fafc;
    }
    .metric-box-sub {
        font-size: 11px;
        color: #64748b;
        margin-top: 2px;
    }
    .stat-pill {
        background: #131b2e;
        border: 1px solid #1e293b;
        border-radius: 8px;
        padding: 12px;
        text-align: left;
    }
    .stat-pill-num {
        font-size: 20px;
        font-weight: 700;
        color: #f8fafc;
    }
    .stat-pill-label {
        font-size: 11px;
        color: #94a3b8;
    }
    .ticket-card {
        background: #131b2e;
        border: 1px solid #1e293b;
        border-radius: 8px;
        padding: 12px 14px;
        margin-bottom: 8px;
    }
    .badge-urgent {
        background: #7f1d1d;
        color: #fca5a5;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 10px;
        font-weight: 700;
    }
    .badge-high {
        background: #7c2d12;
        color: #fdba74;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 10px;
        font-weight: 700;
    }
    .badge-medium {
        background: #713f12;
        color: #fde047;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 10px;
        font-weight: 700;
    }
    .badge-low {
        background: #14532d;
        color: #86efac;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 10px;
        font-weight: 700;
    }
    .badge-open {
        background: #1e3a8a;
        color: #93c5fd;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 10px;
        font-weight: 700;
    }
    .badge-resolved {
        background: #064e3b;
        color: #6ee7b7;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 10px;
        font-weight: 700;
    }
    .badge-progress {
        background: #4c1d95;
        color: #c4b5fd;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 10px;
        font-weight: 700;
    }
</style>
""", unsafe_allow_html=True)

def check_backend_api():
    try:
        r = requests.get(f"{API_BASE_URL}/health", timeout=1.0)
        return r.status_code == 200
    except Exception:
        return False

def resolve_ticket_action(t_id: int):
    try:
        requests.post(f"{API_BASE_URL}/tickets/{t_id}/resolve?resolution_notes=Resolved+via+Helpdesk+UI", timeout=1.0)
    except Exception:
        pass
    update_ticket(t_id, {"status": "Resolved", "resolution_notes": "Resolved via Command Center"})

def reopen_ticket_action(t_id: int):
    try:
        requests.patch(f"{API_BASE_URL}/tickets/{t_id}", json={"status": "Open"}, timeout=1.0)
    except Exception:
        pass
    update_ticket(t_id, {"status": "Open", "resolution_notes": ""})

def progress_ticket_action(t_id: int):
    try:
        requests.patch(f"{API_BASE_URL}/tickets/{t_id}", json={"status": "In Progress"}, timeout=1.0)
    except Exception:
        pass
    update_ticket(t_id, {"status": "In Progress"})

def delete_ticket_action(t_id: int):
    try:
        requests.delete(f"{API_BASE_URL}/tickets/{t_id}", timeout=1.0)
    except Exception:
        pass
    delete_ticket(t_id)

api_connected = check_backend_api()
stats = get_stats()
all_tickets, total_count = list_tickets(limit=1000)

total_tickets = stats.get("total_tickets", len(all_tickets))
open_count = stats.get("open_tickets", 0)
in_progress_count = stats.get("in_progress_tickets", 0)
resolved_count = stats.get("resolved_tickets", 0)
sla_breached_count = stats.get("sla_breached", 0)
by_priority = stats.get("by_priority", {})
by_status = stats.get("by_status", {})
pending_count = by_status.get("Pending", 0) + by_status.get("Pending User", 0)
unassigned_count = len([t for t in all_tickets if not t.get("assigned_to") or t.get("assigned_to") == "IT Helpdesk Queue"])

with st.sidebar:
    st.title("HelpDesk")
    st.caption("Support Platform")
    st.divider()

    st.subheader("Navigation")
    nav = st.radio(
        "Menu",
        ["Dashboard", "Tickets", "AI Triage & New Ticket", "Knowledge Base"],
        label_visibility="collapsed"
    )

    st.divider()
    st.subheader("System Info")
    if api_connected:
        st.text("Mode: FastAPI REST API")
    else:
        st.text("Mode: Direct SQLite Database")

    st.text(f"Model: {os.getenv('GROQ_MODEL', 'openai/gpt-oss-120b')}")
    st.text(f"Total Tickets: {total_tickets}")
    st.text(f"Active Queue: {open_count + in_progress_count}")
    st.text(f"Resolved: {resolved_count}")

    if st.button("Refresh Platform", use_container_width=True):
        st.rerun()

if nav == "Dashboard":
    st.title("Command Center")

    col_m1, col_m2, col_m3, col_m4, col_m5 = st.columns(5)
    with col_m1:
        st.markdown(f"""
        <div class="metric-box">
            <div class="metric-box-title">Support Live</div>
            <div class="metric-box-value" style="color: #10b981;">Online</div>
            <div class="metric-box-sub">99.9% uptime</div>
        </div>
        """, unsafe_allow_html=True)
    with col_m2:
        st.markdown(f"""
        <div class="metric-box">
            <div class="metric-box-title">Active Conversations</div>
            <div class="metric-box-value">{open_count + in_progress_count}</div>
            <div class="metric-box-sub">Across all queues</div>
        </div>
        """, unsafe_allow_html=True)
    with col_m3:
        st.markdown(f"""
        <div class="metric-box">
            <div class="metric-box-title">Queue Wait Time</div>
            <div class="metric-box-value">2m 18s</div>
            <div class="metric-box-sub">Target: &lt; 5m</div>
        </div>
        """, unsafe_allow_html=True)
    with col_m4:
        st.markdown(f"""
        <div class="metric-box">
            <div class="metric-box-title">Agents Online</div>
            <div class="metric-box-value">8</div>
            <div class="metric-box-sub">Day Shift: 11 agents</div>
        </div>
        """, unsafe_allow_html=True)
    with col_m5:
        compliance = stats.get("sla_compliance_rate", 94.2)
        st.markdown(f"""
        <div class="metric-box">
            <div class="metric-box-title">SLA Health</div>
            <div class="metric-box-value" style="color: #38bdf8;">{compliance}%</div>
            <div class="metric-box-sub">{sla_breached_count} breached SLAs</div>
        </div>
        """, unsafe_allow_html=True)

    st.write("")
    st.subheader("Ticket Pulse - Last 24 Hours")

    hours = [f"{h:02d}:00" for h in range(24)]
    pulse_data = pd.DataFrame({
        "Hour": hours,
        "Volume": [2, 1, 1, 0, 1, 3, 5, 8, 14, 18, 22, 25, 21, 24, 26, 23, 19, 15, 12, 9, 7, 5, 4, 3]
    }).set_index("Hour")
    st.area_chart(pulse_data, height=140, use_container_width=True)

    stat1, stat2, stat3, stat4, stat5 = st.columns(5)
    with stat1:
        st.markdown(f"""
        <div class="stat-pill" style="border-left: 3px solid #3b82f6;">
            <div class="stat-pill-num">{open_count}</div>
            <div class="stat-pill-label">New</div>
        </div>
        """, unsafe_allow_html=True)
    with stat2:
        st.markdown(f"""
        <div class="stat-pill" style="border-left: 3px solid #8b5cf6;">
            <div class="stat-pill-num">{in_progress_count}</div>
            <div class="stat-pill-label">In Progress</div>
        </div>
        """, unsafe_allow_html=True)
    with stat3:
        st.markdown(f"""
        <div class="stat-pill" style="border-left: 3px solid #f59e0b;">
            <div class="stat-pill-num">{pending_count}</div>
            <div class="stat-pill-label">Pending</div>
        </div>
        """, unsafe_allow_html=True)
    with stat4:
        st.markdown(f"""
        <div class="stat-pill" style="border-left: 3px solid #10b981;">
            <div class="stat-pill-num">{resolved_count}</div>
            <div class="stat-pill-label">Resolved Today</div>
        </div>
        """, unsafe_allow_html=True)
    with stat5:
        st.markdown(f"""
        <div class="stat-pill" style="border-left: 3px solid #ef4444;">
            <div class="stat-pill-num">{sla_breached_count}</div>
            <div class="stat-pill-label">Breached SLAs</div>
        </div>
        """, unsafe_allow_html=True)

    st.write("")
    row3_left, row3_right = st.columns([3, 2])

    with row3_left:
        st.subheader("Ticket Distribution")
        dist_r1_c1, dist_r1_c2, dist_r1_c3 = st.columns(3)
        dist_r2_c1, dist_r2_c2, dist_r2_c3 = st.columns(3)

        urgent_val = by_priority.get("Critical", 0)
        high_val = by_priority.get("High", 0)
        medium_val = by_priority.get("Medium", 0)
        low_val = by_priority.get("Low", 0)

        with dist_r1_c1:
            st.markdown(f"""
            <div class="stat-pill">
                <div class="stat-pill-num" style="color: #ef4444;">{urgent_val}</div>
                <div class="stat-pill-label">Urgent (Critical)</div>
            </div>
            """, unsafe_allow_html=True)
        with dist_r1_c2:
            st.markdown(f"""
            <div class="stat-pill">
                <div class="stat-pill-num" style="color: #f97316;">{high_val}</div>
                <div class="stat-pill-label">High</div>
            </div>
            """, unsafe_allow_html=True)
        with dist_r1_c3:
            st.markdown(f"""
            <div class="stat-pill">
                <div class="stat-pill-num" style="color: #eab308;">{medium_val}</div>
                <div class="stat-pill-label">Medium</div>
            </div>
            """, unsafe_allow_html=True)

        with dist_r2_c1:
            st.markdown(f"""
            <div class="stat-pill">
                <div class="stat-pill-num" style="color: #10b981;">{low_val}</div>
                <div class="stat-pill-label">Low</div>
            </div>
            """, unsafe_allow_html=True)
        with dist_r2_c2:
            st.markdown(f"""
            <div class="stat-pill">
                <div class="stat-pill-num" style="color: #94a3b8;">{pending_count}</div>
                <div class="stat-pill-label">On Hold</div>
            </div>
            """, unsafe_allow_html=True)
        with dist_r2_c3:
            st.markdown(f"""
            <div class="stat-pill">
                <div class="stat-pill-num" style="color: #38bdf8;">{unassigned_count}</div>
                <div class="stat-pill-label">Unassigned</div>
            </div>
            """, unsafe_allow_html=True)

    with row3_right:
        st.subheader("Channel Mix")
        channel_df = pd.DataFrame({
            "Channel": ["Email", "Chat", "Phone", "Portal", "Social"],
            "Percentage": [45, 28, 12, 10, 5]
        }).set_index("Channel")
        st.bar_chart(channel_df, use_container_width=True, height=180)

    st.write("")
    row4_left, row4_right = st.columns([3, 2])

    with row4_left:
        st.subheader(f"My Queue ({open_count + in_progress_count})")
        st.caption("Newest active incoming tickets first")

        queue_tickets = [t for t in all_tickets if t.get("status") in ["Open", "In Progress", "Pending"]]
        if not queue_tickets:
            st.info("No active tickets in queue.")
        else:
            for t in queue_tickets[:6]:
                prio = t.get("priority", "Medium")
                prio_badge = f"badge-{prio.lower()}" if prio.lower() in ["urgent", "high", "medium", "low"] else "badge-medium"
                if prio == "Critical":
                    prio_badge = "badge-urgent"

                status_val = t.get("status", "Open")
                status_badge = "badge-open"
                if status_val == "In Progress":
                    status_badge = "badge-progress"
                elif status_val == "Resolved":
                    status_badge = "badge-resolved"

                t_id = t.get("id")
                t_code = t.get("ticket_code", f"HD-{t_id}")
                t_title = t.get("title", "IT Issue")
                t_req = t.get("requester_name", "User")
                t_created = t.get("created_at", "")[:10]

                card_col_text, card_col_btn1, card_col_btn2 = st.columns([4, 1.2, 1.2])
                with card_col_text:
                    st.markdown(f"""
                    <div style="padding: 6px 0;">
                        <span class="{prio_badge}">{prio}</span>
                        <span class="{status_badge}">{status_val}</span>
                        <strong style="margin-left: 6px; color: #f8fafc;">{t_code}</strong>
                        <span style="color: #cbd5e1; margin-left: 6px;">{t_title}</span>
                        <div style="font-size: 11px; color: #64748b; margin-top: 2px;">
                            Requester: {t_req} | Department: {t.get('department', 'General')} | Created: {t_created}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                with card_col_btn1:
                    if st.button("Resolve", key=f"dash_resolve_{t_id}", use_container_width=True):
                        resolve_ticket_action(t_id)
                        st.rerun()
                with card_col_btn2:
                    if status_val != "In Progress":
                        if st.button("Start", key=f"dash_prog_{t_id}", use_container_width=True):
                            progress_ticket_action(t_id)
                            st.rerun()
                    else:
                        st.text("Active")

    with row4_right:
        st.subheader("Team Status")
        st.markdown("""
        <div class="ticket-card" style="display: flex; justify-content: space-between; align-items: center;">
            <div>
                <strong>Sarah Connor</strong>
                <div style="font-size: 11px; color: #10b981;">Online - Tier 1 Helpdesk</div>
            </div>
            <div style="font-weight: 700; color: #38bdf8;">8 tickets</div>
        </div>
        <div class="ticket-card" style="display: flex; justify-content: space-between; align-items: center;">
            <div>
                <strong>Marcus Vance</strong>
                <div style="font-size: 11px; color: #10b981;">Online - Network Ops</div>
            </div>
            <div style="font-weight: 700; color: #38bdf8;">12 tickets</div>
        </div>
        <div class="ticket-card" style="display: flex; justify-content: space-between; align-items: center;">
            <div>
                <strong>Aisha Patel</strong>
                <div style="font-size: 11px; color: #10b981;">Online - IAM Support</div>
            </div>
            <div style="font-weight: 700; color: #38bdf8;">14 tickets</div>
        </div>
        <div class="ticket-card" style="display: flex; justify-content: space-between; align-items: center;">
            <div>
                <strong>David Miller</strong>
                <div style="font-size: 11px; color: #94a3b8;">Away - SecOps Escaped</div>
            </div>
            <div style="font-weight: 700; color: #94a3b8;">6 tickets</div>
        </div>
        """, unsafe_allow_html=True)

elif nav == "Tickets":
    st.title("Tickets Command Center")
    st.caption("Live ticket directory sorted newest first")

    top_c1, top_c2, top_c3 = st.columns([2, 1, 1])
    with top_c1:
        search_query = st.text_input("Search tickets by code, title, description, or requester", placeholder="e.g. low fps, vpn, marcus...")
    with top_c2:
        filter_status = st.selectbox("Status", ["All", "Open", "In Progress", "Pending", "Resolved"])
    with top_c3:
        filter_priority = st.selectbox("Priority", ["All", "Critical", "High", "Medium", "Low"])

    display_tickets = all_tickets
    if search_query and search_query.strip():
        sq = search_query.strip().lower()
        display_tickets = [
            t for t in display_tickets
            if sq in t.get("ticket_code", "").lower()
            or sq in t.get("title", "").lower()
            or sq in t.get("description", "").lower()
            or sq in t.get("requester_name", "").lower()
        ]

    if filter_status != "All":
        display_tickets = [t for t in display_tickets if t.get("status") == filter_status]

    if filter_priority != "All":
        display_tickets = [t for t in display_tickets if t.get("priority") == filter_priority]

    st.write(f"Showing {len(display_tickets)} of {total_tickets} tickets")
    st.divider()

    if not display_tickets:
        st.info("No tickets found matching the specified filters.")
    else:
        for t in display_tickets:
            t_id = t.get("id")
            t_code = t.get("ticket_code", f"HD-{t_id}")
            t_title = t.get("title", "IT Issue")
            t_status = t.get("status", "Open")
            t_prio = t.get("priority", "Medium")

            with st.expander(f"[{t_code}] {t_title} | Status: {t_status} | Priority: {t_prio}", expanded=(t_id == all_tickets[0]["id"])):
                c_details, c_actions = st.columns([3, 1])
                with c_details:
                    st.text(f"Ticket ID: {t_id} | Code: {t_code}")
                    st.text(f"Requester: {t.get('requester_name')} ({t.get('requester_email')})")
                    st.text(f"Department: {t.get('department')} | Category: {t.get('category')}")
                    st.text(f"Created: {t.get('created_at')} | SLA Deadline: {t.get('sla_deadline')}")
                    if t.get("resolved_at"):
                        st.text(f"Resolved At: {t.get('resolved_at')}")

                    st.markdown("**Problem Description:**")
                    st.info(t.get("description", "No description provided."))

                    solutions = t.get("solutions", [])
                    if solutions:
                        st.markdown("**Troubleshooting Solutions:**")
                        for idx, step in enumerate(solutions, 1):
                            st.write(f"{idx}. {step}")

                    commands = t.get("quick_commands", [])
                    if commands:
                        st.markdown("**Suggested Commands:**")
                        for cmd in commands:
                            st.code(cmd, language="bash")

                with c_actions:
                    st.markdown("**Actions:**")
                    if t_status != "Resolved":
                        if st.button("Mark Resolved", key=f"t_res_{t_id}", use_container_width=True):
                            resolve_ticket_action(t_id)
                            st.success(f"Ticket #{t_id} marked as Resolved.")
                            st.rerun()

                        if t_status != "In Progress":
                            if st.button("Mark In Progress", key=f"t_prog_{t_id}", use_container_width=True):
                                progress_ticket_action(t_id)
                                st.rerun()
                    else:
                        if st.button("Reopen Ticket", key=f"t_reopen_{t_id}", use_container_width=True):
                            reopen_ticket_action(t_id)
                            st.success(f"Ticket #{t_id} reopened.")
                            st.rerun()

                    if st.button("Delete Ticket", key=f"t_del_{t_id}", use_container_width=True):
                        delete_ticket_action(t_id)
                        st.warning(f"Ticket #{t_id} deleted.")
                        st.rerun()

elif nav == "AI Triage & New Ticket":
    st.title("AI Issue Triage & Ticket Creator")
    st.caption("Classify IT problems, get step solutions, and insert tickets directly into the live queue")

    st.subheader("Quick Scenario Presets")
    q1, q2, q3, q4 = st.columns(4)
    if "triage_input" not in st.session_state:
        st.session_state["triage_input"] = ""

    if q1.button("Low FPS in Games"):
        st.session_state["triage_input"] = "My PC is lagging in games, low FPS stuttering after latest driver update"
    if q2.button("VPN Connection Dropping"):
        st.session_state["triage_input"] = "GlobalProtect VPN timeout error 502 while connecting from home Wi-Fi"
    if q3.button("Okta 2FA Locked"):
        st.session_state["triage_input"] = "User locked out of corporate Okta account after replacing their mobile phone"
    if q4.button("Screen Flickering on Dock"):
        st.session_state["triage_input"] = "Monitor display flickers black intermittently when connected via USB-C docking station"

    with st.form("triage_create_form"):
        req_name = st.text_input("Requester Name", value="Marcus Vance")
        req_email = st.text_input("Requester Email", value="m.vance@company.corp")
        req_dept = st.selectbox("Department", ["Engineering", "Operations", "Sales", "Finance", "HR", "Marketing"])
        issue_title = st.text_input("Ticket Title (Optional)")
        issue_text = st.text_area("Problem Description (Required)", value=st.session_state.get("triage_input", ""), height=130)

        c_submit1, c_submit2 = st.columns(2)
        with c_submit1:
            run_ai = st.form_submit_button("Analyze Issue with AI", use_container_width=True)
        with c_submit2:
            create_direct = st.form_submit_button("Create Ticket Immediately", type="primary", use_container_width=True)

    if run_ai:
        if not issue_text.strip():
            st.warning("Please provide an issue description.")
        else:
            with st.spinner("AI Helpdesk Agent analyzing issue with Groq LLM..."):
                analysis = ITHelpDeskAgent.Helpdesk_agent(issue_text)
                st.session_state["ai_result"] = analysis
                st.session_state["ai_issue_text"] = issue_text
                st.session_state["ai_req_name"] = req_name
                st.session_state["ai_req_email"] = req_email
                st.session_state["ai_req_dept"] = req_dept
                st.session_state["ai_issue_title"] = issue_title or analysis.get("title", issue_text[:50])

    if "ai_result" in st.session_state:
        res = st.session_state["ai_result"]
        st.divider()
        st.subheader("AI Analysis Result")

        r1, r2, r3 = st.columns(3)
        with r1:
            st.text(f"Identified Title: {res.get('title')}")
        with r2:
            st.text(f"Category: {res.get('category')}")
        with r3:
            st.text(f"Priority: {res.get('priority')}")

        st.markdown("**Recommended Solutions:**")
        for idx, sol in enumerate(res.get("solutions", []), 1):
            st.write(f"{idx}. {sol}")

        cmds = res.get("commands", [])
        if cmds:
            st.markdown("**Diagnostic Commands:**")
            for c in cmds:
                st.code(c, language="bash")

        if st.button("Confirm and Create Ticket from Analysis", type="primary"):
            new_ticket_data = {
                "title": st.session_state.get("ai_issue_title", res.get("title", "IT Ticket")),
                "description": st.session_state.get("ai_issue_text", issue_text),
                "category": res.get("category", "Software"),
                "priority": res.get("priority", "Medium"),
                "requester_name": st.session_state.get("ai_req_name", req_name),
                "requester_email": st.session_state.get("ai_req_email", req_email),
                "department": st.session_state.get("ai_req_dept", req_dept),
                "solutions": res.get("solutions", []),
                "quick_commands": res.get("commands", [])
            }
            created = create_ticket(new_ticket_data)
            st.success(f"Ticket Created Successfully! Ticket Code: {created.get('ticket_code')} (ID: {created.get('id')})")
            del st.session_state["ai_result"]
            st.rerun()

    if create_direct:
        if not issue_text.strip():
            st.warning("Please provide an issue description.")
        else:
            new_data = {
                "title": issue_title.strip() if issue_title.strip() else issue_text[:50],
                "description": issue_text.strip(),
                "category": "Software",
                "priority": "Medium",
                "requester_name": req_name,
                "requester_email": req_email,
                "department": req_dept,
                "solutions": ["Restart device", "Check software updates", "Contact helpdesk if problem persists"],
                "quick_commands": []
            }
            created = create_ticket(new_data)
            st.success(f"Ticket Created Successfully! Code: {created.get('ticket_code')} (ID: {created.get('id')})")
            st.rerun()

elif nav == "Knowledge Base":
    st.title("Knowledge Base & Standard Runbooks")
    kb_query = st.text_input("Search Runbooks", placeholder="e.g. vpn, mfa, bitlocker, docker, display...")

    articles = search_kb(query=kb_query)
    st.write(f"Showing {len(articles)} documentation articles")
    st.divider()

    for a in articles:
        with st.expander(f"{a.get('title')} ({a.get('category')})"):
            st.write(f"Summary: {a.get('summary')}")
            st.markdown(a.get("content"))
            cmds = a.get("quick_commands", [])
            if cmds:
                st.markdown("**Standard Terminal Commands:**")
                for c in cmds:
                    st.code(c, language="bash")
