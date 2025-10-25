from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import logging

from scraper.profile_detector import SiteProfileDetector
from scraper.universal_scraper import UniversalScraper
from scraper.profile_cache import ProfileCache
from scraper.optimizations import RateLimiter, retry_on_failure

# -------------------- Setup Logging --------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# -------------------- FastAPI App --------------------
app = FastAPI(
    title="Universal News Scraper",
    description="Dynamically scrape any news website with intelligent profile detection",
    version="2.0.2"
)

# -------------------- CORS --------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------- Initialize Components --------------------
detector = SiteProfileDetector()
scraper = UniversalScraper()
cache = ProfileCache()
rate_limiter = RateLimiter(calls_per_second=3)

# -------------------- Models --------------------
class ScrapeRequest(BaseModel):
    urls: List[str] = Field(..., description="List of news website URLs", min_length=1)
    filters: List[str] = Field(..., description="Search keywords/topics", min_length=1)
    max_results: Optional[int] = Field(20, ge=1, le=100)
    force_refresh: Optional[bool] = Field(False, description="Force profile regeneration")
    
    @field_validator('urls')
    @classmethod
    def validate_urls(cls, v):
        """Ensure URLs are valid."""
        validated = []
        for url in v:
            url = url.strip()
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            validated.append(url)
        return validated

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
    errors: Optional[List[str]] = []

# -------------------- Helper Functions --------------------
def clean_text(text: Optional[str]) -> str:
    """Safely clean text and remove invalid characters."""
    if not text:
        return ""
    try:
        text = str(text)
        return text.encode("utf-8", errors="ignore").decode("utf-8").strip()
    except Exception:
        return ""

def sanitize_articles(raw_articles: List[dict]) -> List[dict]:
    """Cleans and validates raw article dictionaries."""
    sanitized = []
    for a in raw_articles:
        try:
            sanitized.append({
                "headline": clean_text(a.get("headline", "")),
                "url": clean_text(a.get("url", "")),
                "description": clean_text(a.get("description", "")),
                "source": clean_text(a.get("source", "")) or "unknown",
                "relevance_score": (
                    int(a.get("relevance_score", 0))
                    if str(a.get("relevance_score", "0")).isdigit()
                    else 0
                )
            })
        except Exception as e:
            logger.warning(f"⚠️ Skipping invalid article entry: {e}")
    return sanitized

# -------------------- Scrape Endpoint --------------------
@app.post("/scrape", response_model=ScrapeResponse)
async def scrape_news(request: ScrapeRequest):
    start_time = time.time()
    all_articles = []
    errors = []
    sources_scraped = set()
    
    tasks = [(url, f) for url in request.urls for f in request.filters]
    logger.info(f"🚀 Starting scraping: {len(tasks)} tasks")

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {
            executor.submit(
                scrape_single_site,
                url,
                query,
                request.max_results,
                request.force_refresh
            ): (url, query)
            for url, query in tasks
        }

        for future in as_completed(futures):
            url, query = futures[future]
            try:
                result = future.result(timeout=90)
                if result:
                    sanitized_result = sanitize_articles(result)
                    all_articles.extend(sanitized_result)
                    sources_scraped.add(url)
                    logger.info(f"✅ Scraped {len(sanitized_result)} articles from {url}")
                else:
                    logger.warning(f"❌ No articles found on {url}")
            except Exception as e:
                error_msg = f"Error scraping {url} with '{query}': {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)

    # Remove duplicates and invalid entries
    seen_urls = set()
    final_articles = []
    for article in all_articles:
        try:
            if not article.get("headline") or not article.get("url"):
                continue
            url = article["url"]
            if url in seen_urls:
                continue
            seen_urls.add(url)
            final_articles.append(Article(**article))
        except Exception as e:
            logger.warning(f"⚠️ Skipping malformed article before response: {e}")

    processing_time = time.time() - start_time
    logger.info(f"🏁 Completed: {len(final_articles)} unique articles in {processing_time:.2f}s")

    return ScrapeResponse(
        articles=final_articles[:request.max_results * len(request.urls)],
        total=len(final_articles),
        processing_time=round(processing_time, 2),
        sources_scraped=len(sources_scraped),
        errors=errors if errors else None
    )

# -------------------- Core Scrape Logic --------------------
@retry_on_failure(max_retries=2, delay=1.0)
def scrape_single_site(url: str, query: str, max_results: int, force_refresh: bool = False) -> List[dict]:
    rate_limiter.wait()
    
    profile = None if force_refresh else cache.get_profile(url)
    
    if not profile:
        logger.info(f"🔍 Generating profile for {url}...")
        profile = detector.detect_profile(url, query)
        cache.save_profile(url, profile)
        logger.info(f"💾 Profile cached for {url}")
    else:
        logger.info(f"📦 Using cached profile for {url}")
    
    articles = scraper.scrape(profile, query, max_results)
    return articles

# -------------------- Utility Endpoints --------------------
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "timestamp": time.time(),
        "version": "2.0.2"
    }

@app.get("/profiles")
async def list_profiles():
    """List all cached site profiles."""
    import os
    from pathlib import Path
    
    profiles_dir = Path("profiles")
    if not profiles_dir.exists():
        return {"profiles": []}
    
    profiles = []
    for file in profiles_dir.glob("*.json"):
        profile = cache.get_profile(file.stem.replace('_', '.'))
        if profile:
            profiles.append({
                "domain": file.stem.replace('_', '.'),
                "base_url": profile.get('base_url'),
                "requires_js": profile.get('requires_js', False),
                "cached_at": os.path.getmtime(file)
            })
    
    return {"profiles": profiles, "count": len(profiles)}

@app.delete("/profiles/{domain}")
async def delete_profile(domain: str):
    """Delete a cached profile."""
    from pathlib import Path
    
    profile_path = Path("profiles") / f"{domain.replace('.', '_')}.json"
    if profile_path.exists():
        profile_path.unlink()
        return {"message": f"Profile for {domain} deleted"}
    else:
        raise HTTPException(status_code=404, detail="Profile not found")

@app.post("/test-profile")
async def test_profile_detection(request: dict):
    """Test profile detection for a URL."""
    try:
        url = request.get('url', '')
        if not url:
            raise HTTPException(status_code=400, detail="URL is required")
        
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
            
        profile = detector.detect_profile(url)
        return {"url": url, "profile": profile, "status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# -------------------- Run App --------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)