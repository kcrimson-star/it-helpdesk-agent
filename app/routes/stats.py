from fastapi import APIRouter
from app.models import HelpdeskStats
from app.database import get_stats

router = APIRouter(prefix="/api/stats", tags=["Helpdesk Analytics & SLA"])

@router.get("", response_model=HelpdeskStats)
async def get_helpdesk_statistics():
    """
    Returns real-time helpdesk operational KPIs:
    - Total tickets, open, in-progress, resolved
    - Critical and high priority incident counts
    - SLA compliance rate and active breaches
    - Distribution breakdown by category and status
    """
    stats = get_stats()
    return stats
