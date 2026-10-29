import os
import json
import re
from typing import Dict, Any, List, Optional, Tuple
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from app.config import settings
from app.models import AIAnalysisResult, PriorityLevel, IssueCategory

SYSTEM_TRIAGE_PROMPT = """You are NovaDesk AI, an expert Principal IT Helpdesk Engineer & Incident Manager with 20+ years of enterprise ITIL experience.
Your mission is to analyze IT support inquiries, accurately classify them, determine priority based on ITIL impact/urgency matrices, identify likely root causes, provide actionable step-by-step resolution instructions, and provide copy-paste terminal/PowerShell commands when applicable.

Return ONLY a valid JSON object with the following schema:
{
  "title": "A concise, professional ticket title summarizing the core issue",
  "category": "One of: Hardware, Software, Network & Connectivity, Identity & Access (IAM), Security & Compliance, Email & Collaboration, Cloud & Infrastructure, Peripherals & Workstation, Other / General IT",
  "sub_category": "Specific component or technology (e.g., GlobalProtect VPN, BitLocker, Outlook OST, Docker Daemon, MFA Push, Wi-Fi 802.1x)",
  "priority": "One of: Critical, High, Medium, Low",
  "urgency": "One of: Critical, High, Medium, Low",
  "impact": "One of: Company-wide, Department, Multiple Users, Single User",
  "sentiment": "One of: Frustrated, Urgent, Neutral, Calm",
  "estimated_sla_hours": 1 (for Critical), 4 (for High), 24 (for Medium), or 48 (for Low),
  "assigned_department": "Target queue: Network Engineering, IAM Support, Endpoint Security, Workstation Tech, Cloud DevOps, or Tier 1 Helpdesk",
  "root_cause_hypothesis": "1-2 sentences explaining what is technically causing this problem",
  "can_self_resolve": true/false (true if the user can execute the solution themselves without admin credentials),
  "escalation_needed": true/false (true if onsite technician, hardware replacement, or domain admin credentials are required),
  "solutions": [
    "Step 1: Specific action with exact setting names",
    "Step 2: Verification step",
    "Step 3: Fallback workaround"
  ],
  "quick_commands": [
    "executable CLI or PowerShell commands if relevant, or empty list if purely GUI/physical"
  ],
  "suggested_kb_topics": [
    "3-4 search keywords for finding matching knowledge base articles"
  ]
}

ITIL Priority Matrix Rules:
- Critical (P1): Entire company/department down, core infrastructure down, security incident, data breach, or executive executive-blocker. SLA = 1 hour.
- High (P2): Multiple users blocked from core work, VPN gateway down, server failure without redundant node. SLA = 4 hours.
- Medium (P3): Single user workflow blocked but individual impact, or non-critical application issue with workaround. SLA = 24 hours.
- Low (P4): Information request, non-blocking bug, peripheral cosmetic issue, software install request. SLA = 48 hours.

Important: Output pure JSON with no markdown backticks, or wrapped in ```json ```. Do not add conversational text outside the JSON."""

SYSTEM_CHAT_PROMPT = """You are NovaDesk AI, an interactive enterprise IT Helpdesk Agent.
You assist employees and engineers in diagnosing and resolving hardware, software, network, access, and security issues.
Be concise, friendly, and technically precise.
Always provide concrete, step-by-step diagnostic actions.
Where appropriate, provide copyable commands (PowerShell, bash, CMD) formatted in code blocks.

At the end of your response, if the user has described an IT issue that can be cataloged as a ticket or has enough details, you MUST include a diagnosis block formatted as:
<<<DIAGNOSIS>>>
{
  "title": "Concise summary",
  "category": "Hardware | Software | Network & Connectivity | Identity & Access (IAM) | Security & Compliance | Email & Collaboration | Cloud & Infrastructure | Peripherals & Workstation | Other / General IT",
  "sub_category": "Component name",
  "priority": "Critical | High | Medium | Low",
  "urgency": "Critical | High | Medium | Low",
  "impact": "Company-wide | Department | Multiple Users | Single User",
  "sentiment": "Neutral",
  "estimated_sla_hours": 24,
  "assigned_department": "Tier 1 Helpdesk",
  "root_cause_hypothesis": "Probable technical cause",
  "can_self_resolve": true,
  "escalation_needed": false,
  "solutions": ["Step 1", "Step 2"],
  "quick_commands": ["command here"],
  "suggested_kb_topics": ["keyword"]
}
<<<END_DIAGNOSIS>>>

If the user is merely greeting or clarifying without an issue, do not include the diagnosis block."""

def parse_sla_hours(val, default: int = 24) -> int:
    if isinstance(val, (int, float)):
        return max(1, int(val))
    if isinstance(val, str):
        match = re.search(r'\d+', val)
        if match:
            return max(1, int(match.group(0)))
    return default

class HelpdeskAgent:
    def __init__(self):
        self.groq_api_key = settings.GROQ_API_KEY
        self.primary_model = settings.GROQ_MODEL
        self.fallback_model = settings.GROQ_FALLBACK_MODEL
        self._llm = None
        self._init_llm()

    def _init_llm(self):
        if self.groq_api_key:
            try:
                self._llm = ChatGroq(
                    model=self.primary_model,
                    groq_api_key=self.groq_api_key,
                    temperature=0.15,
                    max_tokens=2048,
                )
            except Exception as e:
                print(f"[HelpdeskAgent] Warning initializing primary model: {e}")
                self._llm = None

    def _get_llm(self, fallback: bool = False):
        if not self.groq_api_key:
            return None
        model_name = self.fallback_model if fallback else self.primary_model
        return ChatGroq(
            model=model_name,
            groq_api_key=self.groq_api_key,
            temperature=0.15,
            max_tokens=2048,
        )

    def _clean_json_output(self, raw_text: str) -> Dict[str, Any]:
        """Strips markdown code blocks, reasoning tags, and parses JSON safely."""
        text = raw_text.strip()
        # Remove reasoning tags if any
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
        text = re.sub(r"^```json\s*", "", text, flags=re.MULTILINE)
        text = re.sub(r"^```\s*", "", text, flags=re.MULTILINE)
        text = re.sub(r"```$", "", text, flags=re.MULTILINE).strip()

        # Find first { and last }
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1:
            json_str = text[start:end+1]
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass

        # Fallback regex extraction for essential fields
        return self._extract_fallback_fields(raw_text)

    def _extract_fallback_fields(self, text: str) -> Dict[str, Any]:
        """Resilient fallback parser when JSON format is broken."""
        cat = "Software"
        prio = "Medium"
        lower = text.lower()
        if any(w in lower for w in ["down", "outage", "ransom", "breach", "critical", "blue screen", "bsod"]):
            prio = "Critical"
        elif any(w in lower for w in ["vpn", "wifi", "network", "offline", "dns"]):
            cat = "Network & Connectivity"
            prio = "High"
        elif any(w in lower for w in ["password", "mfa", "2fa", "okta", "login", "locked"]):
            cat = "Identity & Access (IAM)"
        elif any(w in lower for w in ["monitor", "cable", "screen", "keyboard", "mouse", "dock"]):
            cat = "Hardware"

        return {
            "title": "IT Helpdesk Inquiry",
            "category": cat,
            "sub_category": "General",
            "priority": prio,
            "urgency": "Medium",
            "impact": "Single User",
            "sentiment": "Neutral",
            "estimated_sla_hours": 24 if prio == "Medium" else (1 if prio == "Critical" else 4),
            "assigned_department": "Tier 1 Helpdesk",
            "root_cause_hypothesis": "Identified from user issue description.",
            "can_self_resolve": True,
            "escalation_needed": False,
            "solutions": [
                "Verify power and network physical connectivity.",
                "Restart application and workstation.",
                "Review system event logs for error codes."
            ],
            "quick_commands": [],
            "suggested_kb_topics": ["troubleshooting", "general-it"]
        }

    def _rule_based_diagnosis(self, description: str, system_info: Optional[str] = None) -> AIAnalysisResult:
        """High-quality offline rule-based heuristic classifier when no LLM key or API is available."""
        desc_lower = description.lower()

        if any(k in desc_lower for k in ["vpn", "connect", "dns", "gateway", "wifi", "internet", "ping", "subnets"]):
            return AIAnalysisResult(
                title="Network / VPN Gateway Connectivity Failure",
                category="Network & Connectivity",
                sub_category="VPN / Wi-Fi",
                priority="High",
                urgency="High",
                impact="Single User",
                sentiment="Urgent",
                estimated_sla_hours=4,
                assigned_department="Network Engineering",
                root_cause_hypothesis="DNS resolution timeout or expired SSL-VPN security tunnel certificate.",
                can_self_resolve=True,
                escalation_needed=False,
                solutions=[
                    "Flush local DNS resolver cache: `ipconfig /flushdns` (Windows) or `sudo resolvectl flush-caches` (Linux).",
                    "Disconnect and restart the VPN client daemon.",
                    "Verify corporate split-tunnel route gateway responding to ICMP ping.",
                    "Restart local Wi-Fi router / network adapter interface."
                ],
                quick_commands=["ipconfig /flushdns", "ipconfig /renew", "netsh winsock reset"],
                suggested_kb_topics=["vpn", "network", "dns"]
            )
        elif any(k in desc_lower for k in ["mfa", "2fa", "okta", "authenticator", "password", "locked", "sso", "login", "reset"]):
            return AIAnalysisResult(
                title="IAM Account Lockout / MFA Authentication Reset",
                category="Identity & Access (IAM)",
                sub_category="MFA / SSO",
                priority="Medium",
                urgency="High",
                impact="Single User",
                sentiment="Frustrated",
                estimated_sla_hours=4,
                assigned_department="IAM Support",
                root_cause_hypothesis="Stale cached session tokens or desynchronized TOTP hardware token time drift.",
                can_self_resolve=False,
                escalation_needed=True,
                solutions=[
                    "Ensure phone system time is set to Automatic Network Time (prevent TOTP drift).",
                    "Clear browser cookies and cached active SSO tokens.",
                    "Contact Helpdesk administrator to issue a 24-hour Temporary Access Pass (TAP) or reset MFA device."
                ],
                quick_commands=["klist purge"],
                suggested_kb_topics=["mfa", "okta", "password-reset"]
            )
        elif any(k in desc_lower for k in ["bitlocker", "encrypt", "ransomware", "virus", "malware", "phishing", "breach"]):
            return AIAnalysisResult(
                title="Security Alert: Drive Encryption / Security Policy Incident",
                category="Security & Compliance",
                sub_category="BitLocker / Endpoint Security",
                priority="Critical",
                urgency="Critical",
                impact="Single User",
                sentiment="Urgent",
                estimated_sla_hours=1,
                assigned_department="Endpoint Security",
                root_cause_hypothesis="TPM Platform Configuration Register (PCR) mismatch triggered by hardware or firmware state alteration.",
                can_self_resolve=False,
                escalation_needed=True,
                solutions=[
                    "Retrieve 48-digit BitLocker recovery key via https://myaccount.microsoft.com/device-list.",
                    "Do not power cycle repeatedly to avoid TPM hardware lockout lock timer.",
                    "Escalate to Endpoint Security team for identity verification and PCR rebinding."
                ],
                quick_commands=["manage-bde -status"],
                suggested_kb_topics=["bitlocker", "encryption", "security"]
            )
        elif any(k in desc_lower for k in ["monitor", "screen", "flicker", "hdmi", "cable", "dock", "laptop", "battery"]):
            return AIAnalysisResult(
                title="Hardware / Docking Station Display Malfunction",
                category="Hardware",
                sub_category="Display & Docking",
                priority="Medium",
                urgency="Medium",
                impact="Single User",
                sentiment="Neutral",
                estimated_sla_hours=24,
                assigned_department="Workstation Tech",
                root_cause_hypothesis="DisplayPort MST bandwidth saturation or outdated Thunderbolt dock controller firmware.",
                can_self_resolve=True,
                escalation_needed=False,
                solutions=[
                    "Power cycle docking station: Unplug power adapter for 30s to discharge internal capacitor.",
                    "Reset graphics subsystem via keyboard shortcut: Win + Ctrl + Shift + B.",
                    "Lower monitor refresh rate to 60Hz in Display Settings.",
                    "Test with a direct HDMI/USB-C cable bypassing the dock."
                ],
                quick_commands=["Win + Ctrl + Shift + B"],
                suggested_kb_topics=["dock", "monitor", "hardware"]
            )
        else:
            return AIAnalysisResult(
                title="General Software & Application Technical Issue",
                category="Software",
                sub_category="Application Troubleshooting",
                priority="Medium",
                urgency="Medium",
                impact="Single User",
                sentiment="Neutral",
                estimated_sla_hours=24,
                assigned_department="Tier 1 Helpdesk",
                root_cause_hypothesis="Corrupted application local user state cache or missing runtime dependencies.",
                can_self_resolve=True,
                escalation_needed=False,
                solutions=[
                    "Completely terminate the application process using Task Manager / pkill.",
                    "Clear application temporary cache and restart workstation.",
                    "Verify corporate application is updated to the latest certified version in Company Portal."
                ],
                quick_commands=["taskkill /F /IM <app>.exe"],
                suggested_kb_topics=["software", "troubleshooting"]
            )

    def diagnose_issue(self, description: str, system_info: Optional[str] = None, title: Optional[str] = None) -> AIAnalysisResult:
        """Runs LangChain Groq model (openai/gpt-oss-120b) to diagnose, classify, and generate solutions."""
        user_prompt = f"Issue Description:\n{description.strip()}"
        if title:
            user_prompt = f"Subject: {title}\n" + user_prompt
        if system_info:
            user_prompt += f"\nSystem Environment: {system_info}"

        # Try Groq LLM
        for attempt, model_variant in enumerate([False, True]): # primary, then fallback
            try:
                llm = self._get_llm(fallback=model_variant)
                if not llm:
                    break
                messages = [
                    SystemMessage(content=SYSTEM_TRIAGE_PROMPT),
                    HumanMessage(content=user_prompt)
                ]
                response = llm.invoke(messages)
                content = response.content if hasattr(response, "content") else str(response)
                parsed = self._clean_json_output(content)
                if parsed and "category" in parsed and "priority" in parsed:
                    # Validate / sanitize
                    return AIAnalysisResult(
                        title=parsed.get("title") or (title or "IT Helpdesk Ticket"),
                        category=parsed.get("category", "Software"),
                        sub_category=parsed.get("sub_category", "General"),
                        priority=parsed.get("priority", "Medium"),
                        urgency=parsed.get("urgency", "Medium"),
                        impact=parsed.get("impact", "Single User"),
                        sentiment=parsed.get("sentiment", "Neutral"),
                        estimated_sla_hours=parse_sla_hours(parsed.get("estimated_sla_hours", 24)),
                        assigned_department=parsed.get("assigned_department", "Tier 1 Helpdesk"),
                        root_cause_hypothesis=parsed.get("root_cause_hypothesis", ""),
                        can_self_resolve=bool(parsed.get("can_self_resolve", False)),
                        escalation_needed=bool(parsed.get("escalation_needed", False)),
                        solutions=parsed.get("solutions", []),
                        quick_commands=parsed.get("quick_commands", []),
                        suggested_kb_topics=parsed.get("suggested_kb_topics", [])
                    )
            except Exception as e:
                print(f"[HelpdeskAgent] LLM diagnosis attempt {attempt+1} failed: {e}")

        # Fallback heuristic
        return self._rule_based_diagnosis(description, system_info)

    def chat_troubleshoot(
        self,
        user_message: str,
        history: Optional[List[Dict[str, str]]] = None
    ) -> Tuple[str, Optional[AIAnalysisResult], List[str], List[str]]:
        """Conversational IT troubleshooting chat with memory and real-time diagnosis extraction."""
        history = history or []
        messages = [SystemMessage(content=SYSTEM_CHAT_PROMPT)]

        # Add recent conversation turns
        for turn in history[-8:]:
            role = turn.get("role", "user")
            content = turn.get("content", "")
            if role == "user":
                messages.append(HumanMessage(content=content))
            else:
                messages.append(AIMessage(content=content))

        messages.append(HumanMessage(content=user_message))

        try:
            llm = self._get_llm(fallback=False)
            if not llm:
                raise ValueError("No LLM available")
            response = llm.invoke(messages)
            raw_reply = response.content if hasattr(response, "content") else str(response)
        except Exception as e:
            print(f"[HelpdeskAgent] Chat error: {e}")
            # Fallback chat response
            diag = self._rule_based_diagnosis(user_message)
            return (
                f"I understand you are experiencing an issue: **{user_message}**.\n\n"
                f"**Immediate Recommended Actions:**\n"
                + "\n".join([f"- {s}" for s in diag.solutions[:3]])
                + "\n\nWould you like me to create an official support ticket for this?",
                diag,
                ["Yes, create a ticket", "That didn't fix it", "Show more commands"],
                diag.quick_commands
            )

        # Parse Diagnosis block if present
        diagnosis = None
        cleaned_reply = raw_reply

        diag_match = re.search(r"<<<DIAGNOSIS>>>(.*?)<<<END_DIAGNOSIS>>>", raw_reply, flags=re.DOTALL)
        if diag_match:
            diag_json_str = diag_match.group(1).strip()
            cleaned_reply = raw_reply.replace(diag_match.group(0), "").strip()
            try:
                parsed_diag = self._clean_json_output(diag_json_str)
                diagnosis = AIAnalysisResult(
                    title=parsed_diag.get("title", "IT Helpdesk Issue"),
                    category=parsed_diag.get("category", "Software"),
                    sub_category=parsed_diag.get("sub_category", "General"),
                    priority=parsed_diag.get("priority", "Medium"),
                    urgency=parsed_diag.get("urgency", "Medium"),
                    impact=parsed_diag.get("impact", "Single User"),
                    sentiment=parsed_diag.get("sentiment", "Neutral"),
                    estimated_sla_hours=parse_sla_hours(parsed_diag.get("estimated_sla_hours", 24)),
                    assigned_department=parsed_diag.get("assigned_department", "Tier 1 Helpdesk"),
                    root_cause_hypothesis=parsed_diag.get("root_cause_hypothesis", ""),
                    can_self_resolve=bool(parsed_diag.get("can_self_resolve", False)),
                    escalation_needed=bool(parsed_diag.get("escalation_needed", False)),
                    solutions=parsed_diag.get("solutions", []),
                    quick_commands=parsed_diag.get("quick_commands", []),
                    suggested_kb_topics=parsed_diag.get("suggested_kb_topics", [])
                )
            except Exception as e:
                print(f"[HelpdeskAgent] Failed to parse chat diagnosis block: {e}")

        # If user message looks like an issue and diagnosis block was omitted, run lightweight diagnosis
        if not diagnosis and len(user_message.split()) >= 4:
            lower = user_message.lower()
            if any(term in lower for term in ["error", "fail", "not working", "broken", "issue", "crash", "vpn", "mfa", "login", "slow", "freeze", "screen", "wifi"]):
                diagnosis = self.diagnose_issue(user_message)

        # Extract commands from reply if code block exists
        suggested_commands = []
        code_blocks = re.findall(r"```(?:bash|powershell|cmd|sh)?\n(.*?)```", cleaned_reply, flags=re.DOTALL)
        for cb in code_blocks:
            lines = [l.strip() for l in cb.splitlines() if l.strip() and not l.strip().startswith("#")]
            suggested_commands.extend(lines)

        if diagnosis and diagnosis.quick_commands:
            for cmd in diagnosis.quick_commands:
                if cmd not in suggested_commands:
                    suggested_commands.append(cmd)

        suggested_quick_replies = [
            "Create a ticket for this issue",
            "This resolved my issue, thanks!",
            "I tried that and it didn't work",
            "Escalate to human technician"
        ]

        return cleaned_reply, diagnosis, suggested_quick_replies, suggested_commands[:4]

helpdesk_agent = HelpdeskAgent()
