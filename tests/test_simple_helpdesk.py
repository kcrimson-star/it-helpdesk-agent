import pytest
from fastapi.testclient import TestClient
from app.main import app
import ITHelpDeskAgent

client = TestClient(app)

def test_direct_classify_api():
    payload = {
        "issue_description": "Cannot connect to company Wi-Fi network from conference room",
        "requester_name": "Test User"
    }
    res = client.post("/api/classify", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert "Network" in data["analysis"]["category"] or "Software" in data["analysis"]["category"]
    assert len(data["analysis"]["solutions"]) >= 1

def test_helpdesk_agent_fallback_classification():
    res = ITHelpDeskAgent.Helpdesk_agent("VPN connection timed out error 502")
    assert res["category"] == "Network"
    assert res["priority"] == "High"
    assert len(res["solutions"]) >= 1

def test_helpdesk_agent_hardware_classification():
    res = ITHelpDeskAgent.Helpdesk_agent("Laptop screen monitor flickering on dock")
    assert res["category"] == "Hardware"
    assert len(res["solutions"]) >= 1

def test_ticket_creation_api():
    payload = {
        "title": "Printer paper jam on Floor 3",
        "description": "Office printer shows error 13.00 jam in tray 2",
        "category": "Hardware",
        "priority": "Medium",
        "requester_name": "Alice Tech",
        "auto_diagnose": False
    }
    res = client.post("/api/tickets", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["status"] == "Open"
    assert data["ticket_code"].startswith("HD-")
