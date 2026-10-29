from fastapi import APIRouter, HTTPException
from app.models import TriageRequest, TriageResponse
from app.agent import helpdesk_agent
from app.database import search_kb

router = APIRouter(prefix="/api/triage", tags=["AI Triage & Classification"])

@router.post("/classify", response_model=TriageResponse)
async def classify_and_suggest_solutions(payload: TriageRequest):
    """
    Analyzes an IT issue using the LangChain-powered Groq AI Agent.
    Returns:
    - ITIL Classification (Category, Subcategory)
    - Calculated Priority (Critical, High, Medium, Low) with SLA
    - Technical root cause hypothesis
    - Step-by-step diagnostic solutions & copy-paste terminal commands
    - Related internal Knowledge Base articles
    """
    try:
        analysis = helpdesk_agent.diagnose_issue(
            description=payload.issue_description,
            system_info=payload.system_info,
            title=payload.title
        )

        # Retrieve relevant KB articles
        kb_matches = []
        if analysis.suggested_kb_topics:
            for topic in analysis.suggested_kb_topics:
                results = search_kb(query=topic)
                for r in results:
                    if r not in kb_matches:
                        kb_matches.append(r)
                if len(kb_matches) >= 3:
                    break

        if not kb_matches:
            kb_matches = search_kb(category=analysis.category)

        return TriageResponse(
            success=True,
            analysis=analysis,
            relevant_kb_articles=kb_matches[:3]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI Triage error: {str(e)}")
