from enum import Enum
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field
from datetime import datetime

class IssueCategory(str, Enum):
    HARDWARE = "Hardware"
    SOFTWARE = "Software"
    NETWORK = "Network & Connectivity"
    IDENTITY_ACCESS = "Identity & Access (IAM)"
    SECURITY = "Security & Compliance"
    EMAIL_COLLAB = "Email & Collaboration"
    CLOUD_INFRA = "Cloud & Infrastructure"
    PERIPHERALS = "Peripherals & Workstation"
    OTHER = "Other / General IT"

class PriorityLevel(str, Enum):
    CRITICAL = "Critical"   # P1: Immediate business outage, SLA ~ 1 hour
    HIGH = "High"           # P2: Major disruption, SLA ~ 4 hours
    MEDIUM = "Medium"       # P3: Minor disruption, SLA ~ 24 hours
    LOW = "Low"             # P4: General request / minor bug, SLA ~ 48 hours

class TicketStatus(str, Enum):
    OPEN = "Open"
    IN_PROGRESS = "In Progress"
    PENDING_USER = "Pending User"
    RESOLVED = "Resolved"
    CLOSED = "Closed"

class UrgencyLevel(str, Enum):
    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"

class ImpactLevel(str, Enum):
    COMPANY_WIDE = "Company-wide"
    DEPARTMENT = "Department"
    MULTIPLE_USERS = "Multiple Users"
    SINGLE_USER = "Single User"

# AI Diagnosis Schemas
class SolutionStep(BaseModel):
    step_number: int
    action: str
    detail: str
    command: Optional[str] = None

class AIAnalysisResult(BaseModel):
    title: str = Field(description="Clear, concise professional ticket summary title")
    category: str = Field(description="Primary category of the issue")
    sub_category: Optional[str] = Field(default="General", description="Granular subcategory")
    priority: str = Field(description="Critical, High, Medium, or Low based on ITIL framework")
    urgency: str = Field(default="Medium", description="Urgency level")
    impact: str = Field(default="Single User", description="Impact scope")
    sentiment: Optional[str] = Field(default="Neutral", description="Requester sentiment/frustration level")
    estimated_sla_hours: int = Field(default=24, description="Recommended SLA resolution deadline in hours")
    assigned_department: str = Field(default="IT Helpdesk", description="Routing queue: Helpdesk, SecOps, NetOps, etc.")
    root_cause_hypothesis: Optional[str] = Field(default="", description="Probable underlying technical cause")
    can_self_resolve: bool = Field(default=False, description="Whether user can fix this independently via self-service")
    escalation_needed: bool = Field(default=False, description="Requires Tier 2/3 or onsite technician")
    solutions: List[str] = Field(default_factory=list, description="Step-by-step troubleshooting actions")
    quick_commands: List[str] = Field(default_factory=list, description="Copy-paste terminal/PowerShell commands")
    suggested_kb_topics: List[str] = Field(default_factory=list, description="Keywords for relevant KB articles")

class TriageRequest(BaseModel):
    issue_description: str = Field(..., min_length=5, description="Full description of the technical issue")
    title: Optional[str] = Field(None, description="Optional brief title or subject")
    requester_name: Optional[str] = Field(default="Employee", description="Name of requester")
    requester_email: Optional[str] = Field(default="user@company.local", description="Email of requester")
    system_info: Optional[str] = Field(default=None, description="Operating System, device model, or browser")

class TriageResponse(BaseModel):
    success: bool = True
    analysis: AIAnalysisResult
    relevant_kb_articles: List[Dict[str, Any]] = Field(default_factory=list)

# Ticket Schemas
class TicketCreate(BaseModel):
    title: Optional[str] = Field(None, description="Title of the ticket (auto-generated if omitted)")
    description: str = Field(..., min_length=1, description="Detailed problem description")
    category: Optional[str] = Field(None, description="Issue Category (auto-detected if omitted)")
    sub_category: Optional[str] = Field(None, description="Issue Subcategory")
    priority: Optional[str] = Field(None, description="Priority Level (auto-detected if omitted)")
    requester_name: str = Field(default="Employee", description="Requester full name")
    requester_email: str = Field(default="employee@company.local", description="Requester corporate email")
    department: str = Field(default="Operations", description="Requester department")
    auto_diagnose: bool = Field(default=True, description="Whether to trigger AI diagnosis upon ticket creation")
    ai_analysis: Optional[Union[AIAnalysisResult, Dict[str, Any]]] = Field(default=None, description="Pre-computed AI analysis if already run")

class TicketUpdate(BaseModel):
    title: Optional[str] = None
    category: Optional[str] = None
    sub_category: Optional[str] = None
    priority: Optional[PriorityLevel] = None
    status: Optional[TicketStatus] = None
    assigned_to: Optional[str] = None
    department: Optional[str] = None
    resolution_notes: Optional[str] = None

class TicketCommentCreate(BaseModel):
    author_name: str = Field(default="Support Tech", description="Name of person or bot")
    author_type: str = Field(default="agent", description="'agent', 'user', or 'system'")
    content: str = Field(..., min_length=1, description="Comment body")

class TicketCommentResponse(BaseModel):
    id: int
    ticket_id: int
    author_name: str
    author_type: str
    content: str
    created_at: str

class TicketResponse(BaseModel):
    id: int
    ticket_code: str
    title: str
    description: str
    category: str
    sub_category: Optional[str] = None
    priority: str
    urgency: Optional[str] = "Medium"
    impact: Optional[str] = "Single User"
    status: str
    requester_name: str
    requester_email: str
    department: str
    assigned_to: Optional[str] = None
    solutions: List[str] = Field(default_factory=list)
    quick_commands: List[str] = Field(default_factory=list)
    ai_analysis: Optional[Dict[str, Any]] = None
    resolution_notes: Optional[str] = None
    sla_deadline: Optional[str] = None
    created_at: str
    updated_at: str
    resolved_at: Optional[str] = None
    comments: List[TicketCommentResponse] = Field(default_factory=list)

class TicketListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    tickets: List[TicketResponse]

# Chat Schemas
class ChatMessage(BaseModel):
    role: str # "user" or "assistant"
    content: str

class AgentChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str = Field(..., min_length=1)
    history: Optional[List[ChatMessage]] = Field(default_factory=list)

class AgentChatResponse(BaseModel):
    reply: str
    session_id: str
    diagnosis: Optional[AIAnalysisResult] = None
    suggested_quick_replies: List[str] = Field(default_factory=list)
    suggested_commands: List[str] = Field(default_factory=list)

# Knowledge Base Schemas
class KBArticle(BaseModel):
    id: int
    title: str
    category: str
    tags: List[str]
    summary: str
    content: str
    quick_commands: List[str] = Field(default_factory=list)
    created_at: str

# Stats Schema
class HelpdeskStats(BaseModel):
    total_tickets: int
    open_tickets: int
    in_progress_tickets: int
    resolved_tickets: int
    critical_tickets: int
    high_tickets: int
    sla_breached: int
    sla_compliance_rate: float
    by_category: Dict[str, int]
    by_priority: Dict[str, int]
    by_status: Dict[str, int]
