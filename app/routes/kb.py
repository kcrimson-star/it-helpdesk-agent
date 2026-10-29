from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from app.models import KBArticle
from app.database import search_kb, get_kb_article

router = APIRouter(prefix="/api/kb", tags=["Knowledge Base API"])

@router.get("", response_model=List[KBArticle])
async def list_knowledge_base_articles(
    query: Optional[str] = Query(None, description="Search keyword in title, summary, content or tags"),
    category: Optional[str] = Query(None, description="Filter by category")
):
    """
    Search and retrieve curated IT knowledge base articles.
    """
    articles = search_kb(query=query, category=category)
    return articles

@router.get("/{article_id}", response_model=KBArticle)
async def get_article(article_id: int):
    """
    Get a specific knowledge base article by ID.
    """
    article = get_kb_article(article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return article
