from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from app.models import (
    TicketCreate, TicketUpdate, TicketResponse, TicketListResponse,
    TicketCommentCreate, TicketCommentResponse
)
from app.database import (
    create_ticket, get_ticket, list_tickets, update_ticket,
    add_ticket_comment, delete_ticket
)
from app.agent import helpdesk_agent

router = APIRouter(prefix="/api/tickets", tags=["Tickets Management API"])

@router.post("", response_model=TicketResponse, status_code=201)
async def create_new_ticket(payload: TicketCreate):
    """
    Creates an official IT Helpdesk ticket.
    If `auto_diagnose` is True and category/priority are not manually provided,
    the LangChain Groq AI agent automatically classifies the issue, calculates SLA,
    and attaches step-by-step solutions to the ticket.
    """
    try:
        ai_analysis = payload.ai_analysis
        solutions = []
        quick_commands = []
        category = payload.category
        priority = payload.priority
        sub_category = payload.sub_category
        title = payload.title

        if payload.auto_diagnose and (not category or not priority or not ai_analysis):
            # Run AI Diagnosis
            diag = helpdesk_agent.diagnose_issue(
                description=payload.description,
                title=title
            )
            ai_analysis = diag
            category = category or diag.category
            priority = priority or diag.priority
            sub_category = sub_category or diag.sub_category
            title = title or diag.title
            solutions = diag.solutions
            quick_commands = diag.quick_commands
        elif ai_analysis:
            if isinstance(ai_analysis, dict):
                category = category or ai_analysis.get("category")
                priority = priority or ai_analysis.get("priority")
                sub_category = sub_category or ai_analysis.get("sub_category")
                title = title or ai_analysis.get("title")
                solutions = ai_analysis.get("solutions", []) or []
                quick_commands = ai_analysis.get("quick_commands", []) or []
            else:
                category = category or getattr(ai_analysis, "category", None)
                priority = priority or getattr(ai_analysis, "priority", None)
                sub_category = sub_category or getattr(ai_analysis, "sub_category", None)
                title = title or getattr(ai_analysis, "title", None)
                solutions = getattr(ai_analysis, "solutions", []) or []
                quick_commands = getattr(ai_analysis, "quick_commands", []) or []

        title = title or (payload.description[:60] + "..." if len(payload.description) > 60 else payload.description)

        # Prepare serializable ai_analysis
        ai_dict = None
        if ai_analysis:
            if hasattr(ai_analysis, "model_dump"):
                ai_dict = ai_analysis.model_dump()
            elif isinstance(ai_analysis, dict):
                ai_dict = ai_analysis

        data = {
            "title": title,
            "description": payload.description,
            "category": category or "Other / General IT",
            "sub_category": sub_category or "General",
            "priority": priority or "Medium",
            "requester_name": payload.requester_name or "Employee",
            "requester_email": payload.requester_email or "employee@company.local",
            "department": payload.department or "Operations",
            "solutions": solutions,
            "quick_commands": quick_commands,
            "ai_analysis": ai_dict,
            "assigned_to": "Tier 1 Helpdesk" if priority not in ["Critical", "High"] else "Escalations Team",
            "status": "Open"
        }

        created = create_ticket(data)
        return created
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Ticket creation failed: {str(e)}")

@router.get("", response_model=TicketListResponse)
async def get_tickets(
    status: Optional[str] = Query(None, description="Filter by status: Open, In Progress, Pending User, Resolved, Closed"),
    priority: Optional[str] = Query(None, description="Filter by priority: Critical, High, Medium, Low"),
    category: Optional[str] = Query(None, description="Filter by category"),
    search: Optional[str] = Query(None, description="Search ticket ID, title, description or requester"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page")
):
    """
    List tickets with comprehensive filtering, search, sorting and pagination.
    """
    offset = (page - 1) * page_size
    tickets, total = list_tickets(
        status=status,
        priority=priority,
        category=category,
        search=search,
        limit=page_size,
        offset=offset
    )
    return TicketListResponse(
        total=total,
        page=page,
        page_size=page_size,
        tickets=tickets
    )

@router.get("/{ticket_id}", response_model=TicketResponse)
async def get_single_ticket(ticket_id: int):
    """
    Get full ticket details including timeline comments, AI diagnosis, and resolution history.
    """
    ticket = get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail=f"Ticket #{ticket_id} not found")
    return ticket

@router.patch("/{ticket_id}", response_model=TicketResponse)
async def update_existing_ticket(ticket_id: int, payload: TicketUpdate):
    """
    Update ticket status, priority, department, assignee, or resolution notes.
    """
    updated = update_ticket(ticket_id, payload.model_dump(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=404, detail=f"Ticket #{ticket_id} not found")
    return updated

@router.post("/{ticket_id}/resolve", response_model=TicketResponse)
async def resolve_ticket(ticket_id: int, resolution_notes: str = Query(..., min_length=3)):
    """
    Mark a ticket as Resolved and record resolution notes.
    """
    updated = update_ticket(ticket_id, {
        "status": "Resolved",
        "resolution_notes": resolution_notes
    })
    if not updated:
        raise HTTPException(status_code=404, detail=f"Ticket #{ticket_id} not found")
    
    # Add system log comment
    add_ticket_comment(ticket_id, "System", "system", f"Ticket marked as Resolved. Notes: {resolution_notes}")
    return get_ticket(ticket_id)

@router.post("/{ticket_id}/comments", response_model=TicketCommentResponse, status_code=201)
async def add_comment(ticket_id: int, payload: TicketCommentCreate):
    """
    Add a comment or internal work note to a ticket thread.
    """
    ticket = get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail=f"Ticket #{ticket_id} not found")

    comment = add_ticket_comment(
        ticket_id=ticket_id,
        author_name=payload.author_name,
        author_type=payload.author_type,
        content=payload.content
    )
    return comment

@router.delete("/{ticket_id}")
async def remove_ticket(ticket_id: int):
    """
    Delete a ticket and its associated comments.
    """
    success = delete_ticket(ticket_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Ticket #{ticket_id} not found")
    return {"success": True, "message": f"Ticket #{ticket_id} deleted successfully"}
