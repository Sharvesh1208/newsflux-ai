# scraper/profile_detector.py
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re
from typing import List, Dict, Optional
import json

class SiteProfileDetector:
    """Advanced site structure detection with API discovery and better pattern recognition"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
        })
    
    def detect_profile(self, base_url: str, sample_query: str = "news") -> Dict:
        """Analyzes site and generates comprehensive extraction rules"""
        try:
            # Step 1: Try to detect API endpoints first (modern sites)
            api_profile = self._detect_api_endpoint(base_url, sample_query)
            if api_profile:
                print(f"✓ API endpoint detected for {base_url}")
                return api_profile
            
            # Step 2: Try various search URL patterns
            search_patterns = self._generate_search_patterns(base_url, sample_query)
            
            soup = None
            working_url = None
            response_size = 0
            
            for url in search_patterns:
                try:
                    resp = self.session.get(url, timeout=15, allow_redirects=True)
                    if resp.status_code == 200 and len(resp.content) > 1000:
                        soup = BeautifulSoup(resp.content, 'html.parser')
                        working_url = url
                        response_size = len(resp.content)
                        
                        # Check if page has meaningful content
                        if self._has_meaningful_content(soup):
                            print(f"✓ Found working URL: {url}")
                            break
                except Exception as e:
                    continue
            
            if not soup:
                return self._generate_fallback_profile(base_url)
            
            # Step 3: Detect if JS rendering is required
            requires_js = self._check_js_requirement(soup, response_size)
            
            # Step 4: Build comprehensive profile
            profile = {
                "base_url": base_url,
                "search_pattern": working_url,
                "requires_js": requires_js,
                "selectors": {
                    "article_container": self._detect_containers(soup),
                    "headline": self._detect_headlines(soup),
                    "link": self._detect_links(soup, base_url),
                    "description": self._detect_descriptions(soup),
                    "content": self._detect_content_selectors(soup),
                    "metadata": self._detect_metadata_selectors(soup)
                },
                "extraction_strategy": "multi_pass",
                "deep_scrape": True,
                "content_cleaning_rules": self._generate_cleaning_rules(soup)
            }
            
            return profile
            
        except Exception as e:
            print(f"Profile detection error for {base_url}: {e}")
            return self._generate_fallback_profile(base_url)
    
    def _detect_api_endpoint(self, base_url: str, query: str) -> Optional[Dict]:
        """Try to detect if site uses API endpoints for content"""
        common_api_patterns = [
            f"{base_url}/api/search?q={query}",
            f"{base_url}/api/articles?search={query}",
            f"{base_url}/wp-json/wp/v2/posts?search={query}",
            f"{base_url}/api/v1/search?query={query}",
            f"{base_url}/graphql"
        ]
        
        for api_url in common_api_patterns:
            try:
                resp = self.session.get(api_url, timeout=10)
                if resp.status_code == 200:
                    try:
                        data = resp.json()
                        if isinstance(data, (list, dict)) and data:
                            return {
                                "base_url": base_url,
                                "api_endpoint": api_url,
                                "requires_js": False,
                                "extraction_strategy": "api",
                                "api_type": self._detect_api_type(api_url, data)
                            }
                    except:
                        continue
            except:
                continue
        
        return None
    
    def _detect_api_type(self, url: str, data) -> str:
        """Detect API type (WordPress, REST, GraphQL, etc.)"""
        if 'wp-json' in url:
            return 'wordpress'
        elif 'graphql' in url:
            return 'graphql'
        else:
            return 'rest'
    
    def _generate_search_patterns(self, base_url: str, query: str) -> List[str]:
        """Generate comprehensive list of possible search URLs"""
        patterns = [
            # Standard search patterns
            f"{base_url}/search?q={query}",
            f"{base_url}/search?query={query}",
            f"{base_url}/search?search={query}",
            f"{base_url}/search/{query}",
            f"{base_url}/?s={query}",
            f"{base_url}/?search={query}",
            
            # News-specific patterns
            f"{base_url}/news",
            f"{base_url}/news/latest",
            f"{base_url}/latest",
            f"{base_url}/articles",
            f"{base_url}/stories",
            
            # Category patterns
            f"{base_url}/category/news",
            f"{base_url}/news/all",
            
            # Homepage (last resort)
            f"{base_url}",
            f"{base_url}/index.html"
        ]
        
        return patterns
    
    def _has_meaningful_content(self, soup: BeautifulSoup) -> bool:
        """Check if page has actual article content"""
        # Count links that look like articles
        links = soup.find_all('a', href=True)
        article_like_links = 0
        
        for link in links[:100]:
            text = link.get_text(strip=True)
            if 20 < len(text) < 200:  # Reasonable headline length
                article_like_links += 1
        
        # Count headings
        headings = len(soup.find_all(['h1', 'h2', 'h3', 'h4']))
        
        # Check for article elements
        articles = len(soup.find_all(['article', 'div'], class_=re.compile(r'article|post|story|news', re.I)))
        
        return article_like_links >= 5 or headings >= 10 or articles >= 3
    
    def _detect_containers(self, soup: BeautifulSoup) -> List[str]:
        """Enhanced container detection with scoring"""
        candidates = {}
        
        # Keywords that suggest article containers
        container_keywords = [
            'article', 'post', 'story', 'news', 'item', 'entry', 
            'card', 'teaser', 'listing', 'feed', 'result', 'tile'
        ]
        
        # Search in multiple tag types
        for tag in ['article', 'div', 'li', 'section', 'a']:
            elements = soup.find_all(tag, limit=200)
            
            for elem in elements:
                score = 0
                
                # Has heading (strong indicator)
                heading = elem.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
                if heading:
                    score += 5
                    # Heading has meaningful text
                    if len(heading.get_text(strip=True)) > 15:
                        score += 3
                
                # Has link with meaningful text
                links = elem.find_all('a', href=True, limit=3)
                for link in links:
                    link_text = link.get_text(strip=True)
                    if 20 < len(link_text) < 300:
                        score += 3
                        break
                
                # Has description/paragraph
                paragraphs = elem.find_all('p', limit=2)
                if paragraphs and len(paragraphs[0].get_text(strip=True)) > 30:
                    score += 2
                
                # Check class/id for keywords
                attrs = ' '.join(elem.get('class', [])).lower() + ' ' + elem.get('id', '').lower()
                keyword_matches = sum(1 for kw in container_keywords if kw in attrs)
                score += keyword_matches * 2
                
                # Has image
                if elem.find('img'):
                    score += 1
                
                # Has time/date element
                if elem.find('time') or elem.find(class_=re.compile(r'date|time', re.I)):
                    score += 2
                
                # Not too large (likely not main content area)
                text_length = len(elem.get_text(strip=True))
                if 50 < text_length < 2000:
                    score += 1
                
                # Generate selector only if score is good
                if score >= 6:
                    selector = self._generate_selector(elem, tag)
                    candidates[selector] = candidates.get(selector, 0) + score
        
        # Sort by score and return top selectors
        sorted_selectors = sorted(candidates.items(), key=lambda x: x[1], reverse=True)
        result = [sel for sel, score in sorted_selectors[:10]]
        
        # Add generic fallbacks
        fallbacks = [
            'article', 
            'div[class*="article"]', 
            'div[class*="post"]',
            'div[class*="story"]',
            'li[class*="item"]',
            'div[class*="card"]',
            '[class*="news-item"]',
            '[class*="article-item"]'
        ]
        
        result.extend(fallbacks)
        return list(dict.fromkeys(result))[:15]
    
    def _detect_headlines(self, soup: BeautifulSoup) -> List[str]:
        """Enhanced headline detection"""
        selectors = []
        headline_keywords = ['headline', 'title', 'heading', 'name', 'header', 'caption']
        
        # Find headings with specific classes
        for tag in ['h1', 'h2', 'h3', 'h4']:
            elements = soup.find_all(tag, limit=30)
            for elem in elements:
                classes = ' '.join(elem.get('class', [])).lower()
                elem_id = elem.get('id', '').lower()
                
                # Check for headline keywords
                if any(kw in classes or kw in elem_id for kw in headline_keywords):
                    selector = self._generate_selector(elem, tag)
                    if selector not in selectors:
                        selectors.append(selector)
                
                # Check if inside a link (common pattern)
                if elem.find_parent('a'):
                    selectors.append(f"a > {tag}")
        
        # Comprehensive fallbacks with specificity
        selectors.extend([
            'h1', 'h2', 'h3', 'h4',
            'a h1', 'a h2', 'a h3', 'a h4',
            '[class*="headline"]', '[class*="title"]', '[class*="heading"]',
            'article h1', 'article h2', 'article h3',
            'div[class*="article"] h2', 'div[class*="article"] h3',
            'div[class*="post"] h2', 'div[class*="post"] h3',
            'a[class*="title"]', 'a[class*="headline"]',
            'h1 a', 'h2 a', 'h3 a',
            '[role="heading"]'
        ])
        
        return list(dict.fromkeys(selectors))[:20]
    
    def _detect_links(self, soup: BeautifulSoup, base_url: str) -> Dict:
        """Enhanced link detection with better filtering"""
        domain = urlparse(base_url).netloc
        
        return {
            "selector": "a[href]",
            "filter_rules": {
                "min_text_length": 15,
                "max_text_length": 300,
                "exclude_patterns": [
                    '/tag/', '/tags/', '/category/', '/categories/',
                    '/author/', '/about', '/contact', '/privacy', '/terms',
                    '/login', '/register', '/signup', '/subscribe',
                    '#', 'javascript:', 'mailto:', 'tel:',
                    '/feed', '/rss', '/sitemap',
                    '.pdf', '.jpg', '.png', '.gif', '.mp4'
                ],
                "require_domain": domain,
                "allow_relative": True,
                "must_have_text": True
            }
        }
    
    def _detect_descriptions(self, soup: BeautifulSoup) -> List[str]:
        """Enhanced description detection"""
        return [
            'p', 
            'div[class*="excerpt"]', 'div[class*="description"]',
            'div[class*="summary"]', 'div[class*="snippet"]',
            'span[class*="excerpt"]', 'span[class*="description"]',
            'div[class*="teaser"]', 'div[class*="intro"]',
            '[class*="desc"]', '[class*="abstract"]',
            'article p:first-of-type', 
            'div[class*="article"] p:first-of-type',
            'p[class*="lead"]', 'p[class*="intro"]',
            'div[class*="content"] p:first-of-type'
        ]
    
    def _detect_content_selectors(self, soup: BeautifulSoup) -> List[str]:
        """Detect selectors for extracting full article content"""
        return [
            'article',
            '[class*="article-content"]', '[class*="article-body"]',
            '[class*="post-content"]', '[class*="post-body"]',
            '[class*="entry-content"]', '[class*="story-body"]',
            '[id*="article"]', '[id*="content"]',
            'main article', 'main [role="main"]',
            '.content', '#content',
            '[itemprop="articleBody"]',
            'div[class*="text"]', 'div[class*="body"]'
        ]
    
    def _detect_metadata_selectors(self, soup: BeautifulSoup) -> Dict:
        """Detect metadata selectors (date, author, etc.)"""
        return {
            "date": [
                'time', '[datetime]', '[class*="date"]', '[class*="time"]',
                '[class*="published"]', '[itemprop="datePublished"]'
            ],
            "author": [
                '[rel="author"]', '[class*="author"]', '[itemprop="author"]',
                'a[href*="/author/"]', '[class*="byline"]'
            ]
        }
    
    def _check_js_requirement(self, soup: BeautifulSoup, response_size: int) -> bool:
        """Enhanced JS detection"""
        text_content = soup.get_text(strip=True)
        
        # Check for SPA frameworks
        has_react = bool(soup.find('div', id=re.compile(r'root|app|react')))
        has_vue = bool(soup.find('div', id='app') and soup.find('script', src=re.compile(r'vue', re.I)))
        has_angular = bool(soup.find('[ng-app]') or soup.find('[ng-controller]'))
        
        # Check content indicators
        meaningful_text_ratio = len(text_content) / response_size if response_size > 0 else 0
        has_minimal_content = meaningful_text_ratio < 0.05
        
        # Count actual visible elements
        articles = len(soup.find_all(['article', 'h2', 'h3'], limit=20))
        links_with_text = len([a for a in soup.find_all('a', href=True, limit=50) 
                              if len(a.get_text(strip=True)) > 15])
        
        has_few_elements = articles < 3 and links_with_text < 10
        
        # Check for loading indicators
        has_loading = bool(soup.find(class_=re.compile(r'loading|spinner|skeleton', re.I)))
        
        return (has_react or has_vue or has_angular or has_minimal_content or 
                has_few_elements or has_loading)
    
    def _generate_cleaning_rules(self, soup: BeautifulSoup) -> List[str]:
        """Generate rules for cleaning extracted content"""
        return [
            'script', 'style', 'nav', 'footer', 'header', 'aside',
            '[class*="sidebar"]', '[class*="ad"]', '[class*="advertisement"]',
            '[class*="related"]', '[class*="recommended"]',
            '[class*="share"]', '[class*="social"]',
            '[class*="comment"]', '[class*="newsletter"]',
            'iframe', 'form'
        ]
    
    def _generate_selector(self, elem, tag: str) -> str:
        """Generate specific CSS selector for element"""
        classes = elem.get('class', [])
        elem_id = elem.get('id', '')
        
        if elem_id:
            return f"{tag}#{elem_id}"
        elif classes:
            # Use first class that seems meaningful
            for cls in classes:
                if len(cls) > 2 and not cls.startswith(('js-', 'is-')):
                    return f"{tag}.{cls}"
        
        return tag
    
    def _generate_fallback_profile(self, base_url: str) -> Dict:
        """Comprehensive fallback profile"""
        return {
            "base_url": base_url,
            "search_pattern": base_url,
            "requires_js": True,  # Assume JS needed if detection failed
            "selectors": {
                "article_container": [
                    'article', 'div[class*="article"]', 'div[class*="post"]',
                    'div[class*="story"]', 'li[class*="item"]', 'div[class*="card"]',
                    'section[class*="content"]', 'div[class*="entry"]',
                    '[class*="news"]', '[itemtype*="Article"]'
                ],
                "headline": [
                    'h1', 'h2', 'h3', 'h4',
                    'a > h2', 'a > h3', 'a > h4',
                    '[class*="headline"]', '[class*="title"]',
                    'article h2', 'article h3',
                    'div[class*="article"] h2'
                ],
                "link": {
                    "selector": "a[href]",
                    "filter_rules": {
                        "min_text_length": 15,
                        "exclude_patterns": ['/tag/', '/category/', '/about', '#'],
                        "allow_relative": True
                    }
                },
                "description": [
                    'p', 'div[class*="excerpt"]', 'div[class*="description"]',
                    'span[class*="summary"]', 'article p:first-of-type'
                ],
                "content": [
                    'article', '[class*="content"]', '[class*="body"]',
                    'main', '[role="main"]'
                ],
                "metadata": {
                    "date": ['time', '[class*="date"]'],
                    "author": ['[class*="author"]']
                }
            },
            "extraction_strategy": "multi_pass",
            "deep_scrape": True,
            "content_cleaning_rules": [
                'script', 'style', 'nav', 'footer', 'header', 'aside',
                '[class*="ad"]', '[class*="related"]'
            ]
        }