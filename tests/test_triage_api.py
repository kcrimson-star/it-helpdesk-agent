import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_triage_classification():
    payload = {
        "issue_description": "GlobalProtect VPN timeout error 502 while connecting to corporate network from home Wi-Fi",
        "requester_name": "Alice Engineer",
        "system_info": "macOS Sonoma 14.5"
    }
    res = client.post("/api/triage/classify", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    analysis = data["analysis"]
    assert "Network" in analysis["category"] or "VPN" in analysis["sub_category"] or "Software" in analysis["category"]
    assert analysis["priority"] in ["Critical", "High", "Medium", "Low"]
    assert len(analysis["solutions"]) >= 1

def test_stats_api():
    res = client.get("/api/stats")
    assert res.status_code == 200
    data = res.json()
    assert data["total_tickets"] >= 1
    assert "by_category" in data
    assert "by_priority" in data
    assert "sla_compliance_rate" in data

def test_kb_api():
    res = client.get("/api/kb")
    assert res.status_code == 200
    articles = res.json()
    assert len(articles) >= 1

    # Search KB
    search_res = client.get("/api/kb?query=BitLocker")
    assert search_res.status_code == 200
    search_articles = search_res.json()
    assert any("BitLocker" in a["title"] or "BitLocker" in a["summary"] for a in search_articles)
