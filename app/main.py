import os
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.routes import triage, tickets, agent_chat, kb, stats

BASE_DIR = Path(__file__).resolve().parent.parent

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize SQLite database and seed data
    print(f"[NovaDesk AI] Initializing database at {settings.DATABASE_PATH}...")
    init_db()
    print(f"[NovaDesk AI] Active LLM Model: {settings.GROQ_MODEL} (Groq)")
    yield
    print("[NovaDesk AI] Shutting down.")

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Intelligent IT Helpdesk Agent with Issue Classification, Solution Suggestion, and Automated Ticket Creation REST APIs.",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(triage.router)
app.include_router(tickets.router)
app.include_router(agent_chat.router)
app.include_router(kb.router)
app.include_router(stats.router)

@app.post("/api/classify", response_model=triage.TriageResponse)
async def direct_classify(payload: triage.TriageRequest):
    return await triage.classify_and_suggest_solutions(payload)


# Mount Static Files
static_dir = BASE_DIR / "static"
if not static_dir.exists():
    static_dir.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

@app.get("/", include_in_schema=False)
async def serve_index():
    index_file = static_dir / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"message": "NovaDesk AI API is running. UI is initializing.", "docs": "/docs"}

@app.get("/api/health", tags=["System Health"])
async def system_health():
    """
    System health check returning status of database and configured LLM engine.
    """
    db_exists = os.path.exists(settings.DATABASE_PATH)
    has_key = bool(settings.GROQ_API_KEY)
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "llm_engine": "Groq",
        "model": settings.GROQ_MODEL,
        "fallback_model": settings.GROQ_FALLBACK_MODEL,
        "api_key_configured": has_key,
        "database_connected": db_exists,
        "swagger_docs": "/docs"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.APP_HOST, port=settings.APP_PORT, reload=settings.DEBUG)
