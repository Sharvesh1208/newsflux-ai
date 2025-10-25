# scraper/optimizations.py
import time
from functools import wraps
from typing import Callable, Any
import hashlib
import json

class RateLimiter:
    """Rate limiting for API requests"""
    
    def __init__(self, calls_per_second: float = 2):
        self.calls_per_second = calls_per_second
        self.last_call = 0
    
    def wait(self):
        """Wait if necessary to respect rate limit"""
        now = time.time()
        time_since_last = now - self.last_call
        min_interval = 1.0 / self.calls_per_second
        
        if time_since_last < min_interval:
            time.sleep(min_interval - time_since_last)
        
        self.last_call = time.time()


def retry_on_failure(max_retries: int = 3, delay: float = 1.0):
    """Decorator to retry failed operations"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        time.sleep(delay * (attempt + 1))
                    continue
            
            # All retries failed
            raise last_exception
        
        return wrapper
    return decorator


def timing_decorator(func: Callable) -> Callable:
    """Measure function execution time"""
    @wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        start = time.time()
        result = func(*args, **kwargs)
        duration = time.time() - start
        print(f"{func.__name__} took {duration:.2f}s")
        return result
    return wrapper


class SimpleCache:
    """Simple in-memory cache for requests"""
    
    def __init__(self, ttl: int = 3600):
        self.cache = {}
        self.ttl = ttl
    
    def get(self, key: str) -> Any:
        """Get cached value if not expired"""
        if key in self.cache:
            value, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl:
                return value
            else:
                del self.cache[key]
        return None
    
    def set(self, key: str, value: Any):
        """Set cache value with timestamp"""
        self.cache[key] = (value, time.time())
    
    def clear(self):
        """Clear all cache"""
        self.cache.clear()
    
    @staticmethod
    def generate_key(*args, **kwargs) -> str:
        """Generate cache key from arguments"""
        key_data = json.dumps({'args': args, 'kwargs': kwargs}, sort_keys=True)
        return hashlib.md5(key_data.encode()).hexdigest()


def clean_text(text: str) -> str:
    """Clean and normalize text"""
    import re
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove special characters but keep basic punctuation
    text = re.sub(r'[^\w\s\-.,!?:;()\'"]+', '', text)
    
    return text.strip()


def extract_domain(url: str) -> str:
    """Extract domain from URL"""
    from urllib.parse import urlparse
    parsed = urlparse(url)
    return parsed.netloc.replace('www.', '')


def is_valid_url(url: str) -> bool:
    """Check if URL is valid"""
    import re
    url_pattern = re.compile(
        r'^https?://'
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'
        r'localhost|'
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
        r'(?::\d+)?'
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return bool(url_pattern.match(url))


def normalize_url(url: str, base_url: str = '') -> str:
    """Normalize URL (handle relative URLs, etc.)"""
    from urllib.parse import urljoin, urlparse, urlunparse
    
    # Handle relative URLs
    if not url.startswith('http'):
        url = urljoin(base_url, url)
    
    # Parse and reconstruct to normalize
    parsed = urlparse(url)
    
    # Remove fragments and some query params
    normalized = urlunparse((
        parsed.scheme,
        parsed.netloc,
        parsed.path,
        parsed.params,
        parsed.query,
        ''  # Remove fragment
    ))
    
    return normalized


def batch_process(items: list, batch_size: int = 10):
    """Generator to process items in batches"""
    for i in range(0, len(items), batch_size):
        yield items[i:i + batch_size]