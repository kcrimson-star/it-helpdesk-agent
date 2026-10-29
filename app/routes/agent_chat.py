import uuid
from fastapi import APIRouter, HTTPException
from app.models import AgentChatRequest, AgentChatResponse
from app.agent import helpdesk_agent

router = APIRouter(prefix="/api/agent", tags=["Interactive AI Helpdesk Agent"])

@router.post("/chat", response_model=AgentChatResponse)
async def chat_with_agent(payload: AgentChatRequest):
    """
    Conversational endpoint for interactive IT troubleshooting.
    The LangChain Groq model analyzes the issue context, guides the user step-by-step,
    and returns a structured AI diagnosis whenever an actionable IT issue is detected.
    """
    session_id = payload.session_id or str(uuid.uuid4())
    history_dicts = [
        {"role": msg.role, "content": msg.content}
        for msg in (payload.history or [])
    ]

    try:
        reply, diagnosis, quick_replies, commands = helpdesk_agent.chat_troubleshoot(
            user_message=payload.message,
            history=history_dicts
        )

        return AgentChatResponse(
            reply=reply,
            session_id=session_id,
            diagnosis=diagnosis,
            suggested_quick_replies=quick_replies,
            suggested_commands=commands
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent chat failure: {str(e)}")
