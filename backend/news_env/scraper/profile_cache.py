# scraper/profile_cache.py
import json
import os
from pathlib import Path
from typing import Dict, Optional
from urllib.parse import urlparse

class ProfileCache:
    """Manages site profile storage and retrieval"""
    
    def __init__(self, cache_dir: str = "profiles"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
    
    def get_profile(self, url: str) -> Optional[Dict]:
        """Retrieve cached profile for a URL"""
        domain = self._url_to_filename(url)
        profile_path = self.cache_dir / f"{domain}.json"
        
        if profile_path.exists():
            with open(profile_path, 'r') as f:
                return json.load(f)
        return None
    
    def save_profile(self, url: str, profile: Dict):
        """Save profile to cache"""
        domain = self._url_to_filename(url)
        profile_path = self.cache_dir / f"{domain}.json"
        
        with open(profile_path, 'w') as f:
            json.dump(profile, f, indent=2)
    
    def _url_to_filename(self, url: str) -> str:
        """Convert URL to safe filename"""
        domain = urlparse(url).netloc
        return domain.replace('.', '_')