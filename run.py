#!/usr/bin/env python3
import uvicorn
from app.config import settings

if __name__ == "__main__":
    print(f"🚀 Starting NovaDesk AI Helpdesk on http://{settings.APP_HOST}:{settings.APP_PORT}")
    print(f"📚 OpenAPI Documentation available at http://localhost:{settings.APP_PORT}/docs")
    print(f"🤖 Powered by Groq LLM: {settings.GROQ_MODEL}")
    uvicorn.run("app.main:app", host=settings.APP_HOST, port=settings.APP_PORT, reload=settings.DEBUG)
