import os
import json
import requests
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

load_dotenv()

API_KEY = os.getenv("GROQ_API_KEY", "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")
MODEL_NAME = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

def get_groq_llm():
    return ChatGroq(
        model=MODEL_NAME,
        groq_api_key=API_KEY,
        temperature=0.2
    )

def Helpdesk_agent(issue: str) -> dict:
    prompt = (
        "You are an IT helpdesk specialist. Analyze this technical issue:\n"
        f"\"{issue}\"\n\n"
        "Return ONLY a JSON object with these exact keys:\n"
        "{\n"
        "  \"title\": \"brief issue title\",\n"
        "  \"category\": \"Hardware, Software, Network, Security, or Access\",\n"
        "  \"priority\": \"Critical, High, Medium, or Low\",\n"
        "  \"solutions\": [\"step 1\", \"step 2\", \"step 3\"],\n"
        "  \"commands\": [\"relevant command if applicable\"]\n"
        "}"
    )

    try:
        llm = get_groq_llm()
        messages = [
            SystemMessage(content="You classify IT issues and suggest solutions in valid JSON only."),
            HumanMessage(content=prompt)
        ]
        response = llm.invoke(messages)
        text = response.content.strip()

        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()

        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1:
            return json.loads(text[start:end+1])
    except Exception:
        pass

    lower = issue.lower()
    cat = "Software"
    prio = "Medium"
    if any(k in lower for k in ["vpn", "wifi", "network", "internet", "dns"]):
        cat = "Network"
        prio = "High"
        sol = ["Flush DNS cache", "Restart network adapter", "Verify VPN credentials"]
        cmds = ["ipconfig /flushdns"]
    elif any(k in lower for k in ["password", "mfa", "2fa", "login", "locked", "okta"]):
        cat = "Access"
        prio = "Medium"
        sol = ["Check phone time sync", "Clear browser cache", "Request admin MFA reset"]
        cmds = []
    elif any(k in lower for k in ["blue screen", "bsod", "virus", "ransomware", "bitlocker"]):
        cat = "Security"
        prio = "Critical"
        sol = ["Disconnect from network immediately", "Locate BitLocker recovery key", "Contact SecOps"]
        cmds = ["manage-bde -status"]
    elif any(k in lower for k in ["monitor", "keyboard", "mouse", "dock", "laptop"]):
        cat = "Hardware"
        prio = "Medium"
        sol = ["Re-plug all cable connections", "Power cycle dock for 30s", "Update display drivers"]
        cmds = []
    else:
        sol = ["Restart the software application", "Check system logs for errors", "Reinstall current version"]
        cmds = []

    return {
        "title": issue[:50],
        "category": cat,
        "priority": prio,
        "solutions": sol,
        "commands": cmds
    }

def create_ticket_api(title: str, description: str, category: str, priority: str, requester: str = "User", api_url: str = "http://localhost:8000/api/tickets") -> dict:
    payload = {
        "title": title,
        "description": description,
        "category": category,
        "priority": priority,
        "requester_name": requester,
        "auto_diagnose": False
    }
    try:
        res = requests.post(api_url, json=payload, timeout=5)
        if res.status_code in [200, 201]:
            return res.json()
    except Exception:
        pass

    return {
        "id": 1,
        "ticket_code": "HD-LOCAL",
        "title": title,
        "category": category,
        "priority": priority,
        "status": "Open",
        "requester_name": requester
    }