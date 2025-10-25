from pydantic import BaseModel, HttpUrl
from typing import List, Optional

class ScrapeRequest(BaseModel):
    urls: List[HttpUrl]
    filters: List[str]
    max_results: Optional[int] = 20
    use_cache: Optional[bool] = True

class Article(BaseModel):
    headline: str
    url: str
    description: Optional[str] = None
    source: str

class ScrapeResponse(BaseModel):
    articles: List[Article]
    total: int
    processing_time: float
    sites_processed: int
    sites_failed: int
    errors: Optional[List[str]] = None