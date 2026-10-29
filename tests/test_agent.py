import pytest
from app.agent import helpdesk_agent
from app.models import AIAnalysisResult

def test_agent_rule_based_diagnosis():
    # Test VPN rule
    vpn_diag = helpdesk_agent._rule_based_diagnosis("GlobalProtect VPN timeout on Wi-Fi")
    assert isinstance(vpn_diag, AIAnalysisResult)
    assert vpn_diag.category == "Network & Connectivity"
    assert vpn_diag.priority == "High"
    assert len(vpn_diag.solutions) > 0
    assert "ipconfig /flushdns" in vpn_diag.quick_commands

    # Test MFA rule
    mfa_diag = helpdesk_agent._rule_based_diagnosis("Locked out of Okta 2FA on my new phone")
    assert mfa_diag.category == "Identity & Access (IAM)"
    assert mfa_diag.priority == "Medium"
    assert len(mfa_diag.solutions) > 0

    # Test BitLocker security rule
    sec_diag = helpdesk_agent._rule_based_diagnosis("Laptop blue screen asking for BitLocker recovery key")
    assert sec_diag.category == "Security & Compliance"
    assert sec_diag.priority == "Critical"

def test_agent_clean_json_output():
    raw_markdown = """```json
{
  "title": "Corrupted Outlook OST Cache",
  "category": "Email & Collaboration",
  "sub_category": "Outlook",
  "priority": "Medium",
  "urgency": "Medium",
  "impact": "Single User",
  "sentiment": "Neutral",
  "estimated_sla_hours": 24,
  "assigned_department": "Tier 1 Helpdesk",
  "root_cause_hypothesis": "Stale OST cache file",
  "can_self_resolve": true,
  "escalation_needed": false,
  "solutions": ["Rebuild OST profile"],
  "quick_commands": ["outlook.exe /safe"],
  "suggested_kb_topics": ["outlook"]
}
```"""
    parsed = helpdesk_agent._clean_json_output(raw_markdown)
    assert parsed["category"] == "Email & Collaboration"
    assert parsed["priority"] == "Medium"
    assert parsed["solutions"] == ["Rebuild OST profile"]
