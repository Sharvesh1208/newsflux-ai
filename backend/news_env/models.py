# models.py
from pydantic import BaseModel, HttpUrl, Field
from typing import List, Optional


class ScrapeRequest(BaseModel):
    urls: List[HttpUrl] = Field(..., description="List of news website URLs", min_length=1)
    filters: List[str] = Field(..., description="Search keywords/topics", min_length=1)
    max_results: Optional[int] = Field(20, ge=1, le=200)
    force_refresh: Optional[bool] = Field(False, description="Force profile regeneration")


class Article(BaseModel):
    headline: str
    url: str
    description: Optional[str] = None
    source: str
    relevance_score: Optional[int] = 0


class ScrapeResponse(BaseModel):
    articles: List[Article]
    total: int
    processing_time: float
    sources_scraped: int
    errors: Optional[List[str]] = None
