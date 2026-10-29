import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import init_db

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_database():
    init_db()

def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "Groq" in data["llm_engine"]
    assert "gpt-oss-120b" in data["model"]

def test_create_and_get_ticket():
    payload = {
        "title": "Test VPN Connectivity Dropping",
        "description": "User VPN drops every 5 minutes with TLS negotiation timeout",
        "category": "Network & Connectivity",
        "priority": "High",
        "requester_name": "Test User",
        "requester_email": "test@company.corp",
        "department": "Engineering",
        "auto_diagnose": False
    }
    create_res = client.post("/api/tickets", json=payload)
    assert create_res.status_code == 201
    ticket = create_res.json()
    assert ticket["title"] == payload["title"]
    assert ticket["category"] == "Network & Connectivity"
    assert ticket["priority"] == "High"
    assert ticket["status"] == "Open"
    assert ticket["ticket_code"].startswith("HD-")

    # Fetch single ticket
    get_res = client.get(f"/api/tickets/{ticket['id']}")
    assert get_res.status_code == 200
    fetched = get_res.json()
    assert fetched["id"] == ticket["id"]
    assert len(fetched["comments"]) >= 1

def test_filter_and_search_tickets():
    res = client.get("/api/tickets?status=Open")
    assert res.status_code == 200
    data = res.json()
    assert "tickets" in data
    assert "total" in data

    # Test search query
    search_res = client.get("/api/tickets?search=VPN")
    assert search_res.status_code == 200
    search_data = search_res.json()
    assert search_data["total"] >= 1

def test_update_and_resolve_ticket():
    # Create a ticket
    create_res = client.post("/api/tickets", json={
        "description": "Monitor power cord is loose and sparking",
        "requester_name": "Dave",
        "auto_diagnose": False,
        "category": "Hardware",
        "priority": "Critical"
    })
    ticket_id = create_res.json()["id"]

    # Patch status and priority
    patch_res = client.patch(f"/api/tickets/{ticket_id}", json={
        "status": "In Progress",
        "assigned_to": "Field Tech Bob"
    })
    assert patch_res.status_code == 200
    assert patch_res.json()["status"] == "In Progress"
    assert patch_res.json()["assigned_to"] == "Field Tech Bob"

    # Add a work note / comment
    comment_res = client.post(f"/api/tickets/{ticket_id}/comments", json={
        "author_name": "Field Tech Bob",
        "author_type": "agent",
        "content": "Power cord replaced with certified C13 cable. Tested load OK."
    })
    assert comment_res.status_code == 201

    # Mark as Resolved
    resolve_res = client.post(f"/api/tickets/{ticket_id}/resolve?resolution_notes=Replaced+sparking+cable")
    assert resolve_res.status_code == 200
    assert resolve_res.json()["status"] == "Resolved"
    assert resolve_res.json()["resolution_notes"] == "Replaced sparking cable"
