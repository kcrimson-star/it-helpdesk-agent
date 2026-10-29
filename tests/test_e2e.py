import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import init_db

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup():
    init_db()

def test_static_ui_serving():
    # Test index route
    res = client.get("/")
    assert res.status_code == 200
    assert "NovaDesk" in res.text
    assert "AI Incident Diagnosis" in res.text

    # Test static assets
    css_res = client.get("/static/css/style.css")
    assert css_res.status_code == 200
    assert "pulse-red" in css_res.text

    js_res = client.get("/static/js/app.js")
    assert js_res.status_code == 200
    assert "NovaDesk AI" in js_res.text

def test_full_ticket_lifecycle_with_ai():
    # 1. AI Triage
    triage_res = client.post("/api/triage/classify", json={
        "issue_description": "My MacBook screen flickers black whenever I connect to the external HDMI monitor at my desk.",
        "requester_name": "Marcus Vance",
        "system_info": "macOS Sonoma 14.5, Apple Silicon M2"
    })
    assert triage_res.status_code == 200
    triage_data = triage_res.json()
    assert triage_data["success"] is True
    analysis = triage_data["analysis"]
    assert "title" in analysis
    assert "solutions" in analysis
    assert len(analysis["solutions"]) >= 1

    # 2. Create ticket using the AI triage diagnosis
    ticket_res = client.post("/api/tickets", json={
        "title": analysis["title"],
        "description": "My MacBook screen flickers black whenever I connect to the external HDMI monitor at my desk.",
        "category": analysis["category"],
        "priority": analysis["priority"],
        "requester_name": "Marcus Vance",
        "requester_email": "m.vance@company.corp",
        "department": "Design",
        "auto_diagnose": False,
        "ai_analysis": analysis
    })
    assert ticket_res.status_code == 201
    ticket = ticket_res.json()
    ticket_id = ticket["id"]
    assert ticket["ticket_code"].startswith("HD-")
    assert ticket["status"] == "Open"
    assert len(ticket["solutions"]) >= 1

    # 3. Add work note from support tech
    comment_res = client.post(f"/api/tickets/{ticket_id}/comments", json={
        "author_name": "Sarah Tech",
        "author_type": "agent",
        "content": "Delivered high-speed 4K DisplayPort cable to user desk for testing."
    })
    assert comment_res.status_code == 201

    # 4. Mark ticket as In Progress
    patch_res = client.patch(f"/api/tickets/{ticket_id}", json={
        "status": "In Progress",
        "assigned_to": "Sarah Tech"
    })
    assert patch_res.status_code == 200
    assert patch_res.json()["status"] == "In Progress"

    # 5. Resolve ticket
    resolve_res = client.post(f"/api/tickets/{ticket_id}/resolve?resolution_notes=Replaced+defective+HDMI+dongle+with+certified+Thunderbolt+cable")
    assert resolve_res.status_code == 200
    resolved_ticket = resolve_res.json()
    assert resolved_ticket["status"] == "Resolved"
    assert resolved_ticket["resolved_at"] is not None

def test_conversational_chat_agent():
    chat_res = client.post("/api/agent/chat", json={
        "message": "I lost my phone and cannot log into corporate Slack because of MFA. What should I do?",
        "history": []
    })
    assert chat_res.status_code == 200
    chat_data = chat_res.json()
    assert "reply" in chat_data
    assert len(chat_data["reply"]) > 10
    assert chat_data["session_id"] is not None
    assert len(chat_data["suggested_quick_replies"]) > 0
