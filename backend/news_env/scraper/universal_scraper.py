# scraper/universal_scraper.py
import requests
from bs4 import BeautifulSoup, Comment
from selenium import webdriver
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.firefox import GeckoDriverManager
import time
import re
from urllib.parse import urljoin, urlparse
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib

class UniversalScraper:
    """Advanced scraper with readability algorithm and deep content extraction"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive'
        })
    
    def scrape(self, profile: Dict, query: str, max_results: int = 20) -> List[Dict]:
        """Main scraping orchestration with multiple strategies"""
        articles = []
        
        # Strategy 1: API-based extraction (if available)
        if profile.get('extraction_strategy') == 'api':
            articles = self._scrape_via_api(profile, query, max_results)
            if articles:
                print(f"✓ API scraping successful: {len(articles)} articles")
                return articles[:max_results]
        
        # Strategy 2: HTML scraping (with or without JS)
        if profile.get('requires_js', False):
            articles = self._scrape_with_selenium(profile, query, max_results * 2)
        else:
            articles = self._scrape_with_requests(profile, query, max_results * 2)
        
        print(f"Initial extraction: {len(articles)} articles")
        
        # Strategy 3: If insufficient results, try homepage + multiple pages
        if len(articles) < max_results // 2:
            print(f"⚠ Low results, trying alternative strategies...")
            homepage_articles = self._scrape_homepage(profile, max_results)
            articles.extend(homepage_articles)
            print(f"After homepage scraping: {len(articles)} articles")
        
        # Strategy 4: Deep content extraction from article pages
        if profile.get('deep_scrape', True) and articles:
            articles = self._enrich_with_deep_content(articles, max_workers=15)
            print(f"After deep extraction: {len(articles)} articles with content")
        
        # Strategy 5: Intelligent relevance filtering
        articles = self._smart_filter_by_relevance(articles, query)
        print(f"After relevance filtering: {len(articles)} articles")
        
        # Strategy 6: Quality scoring and deduplication
        articles = self._score_and_deduplicate(articles)
        
        return articles[:max_results]
    
    def _scrape_via_api(self, profile: Dict, query: str, max_results: int) -> List[Dict]:
        """Scrape using API endpoints"""
        try:
            api_url = profile['api_endpoint']
            api_type = profile.get('api_type', 'rest')
            
            # Build API request
            if '{query}' in api_url:
                api_url = api_url.replace('{query}', query)
            elif '?' in api_url and 'query' not in api_url:
                api_url += f"&search={query}"
            
            response = self.session.get(api_url, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            # Parse based on API type
            if api_type == 'wordpress':
                return self._parse_wordpress_api(data, profile['base_url'])
            else:
                return self._parse_generic_api(data, profile['base_url'])
        
        except Exception as e:
            print(f"API scraping error: {e}")
            return []
    
    def _parse_wordpress_api(self, data: List[Dict], base_url: str) -> List[Dict]:
        """Parse WordPress REST API response"""
        articles = []
        for item in data[:50]:
            try:
                article = {
                    'headline': BeautifulSoup(item.get('title', {}).get('rendered', ''), 'html.parser').get_text(strip=True),
                    'url': item.get('link', ''),
                    'description': BeautifulSoup(item.get('excerpt', {}).get('rendered', ''), 'html.parser').get_text(strip=True)[:300],
                    'full_content': BeautifulSoup(item.get('content', {}).get('rendered', ''), 'html.parser').get_text(strip=True)[:1000],
                    'source': urlparse(base_url).netloc
                }
                if article['headline'] and article['url']:
                    articles.append(article)
            except:
                continue
        return articles
    
    def _parse_generic_api(self, data, base_url: str) -> List[Dict]:
        """Parse generic API responses"""
        articles = []
        items = data if isinstance(data, list) else data.get('results', data.get('items', data.get('articles', [])))
        
        for item in items[:50]:
            try:
                # Try common field names
                headline = (item.get('title') or item.get('headline') or 
                           item.get('name') or item.get('heading', ''))
                url = (item.get('url') or item.get('link') or 
                      item.get('href') or item.get('permalink', ''))
                desc = (item.get('description') or item.get('excerpt') or 
                       item.get('summary') or item.get('snippet', ''))
                
                if headline and url:
                    articles.append({
                        'headline': str(headline)[:300],
                        'url': urljoin(base_url, url),
                        'description': str(desc)[:300] if desc else '',
                        'source': urlparse(base_url).netloc
                    })
            except:
                continue
        
        return articles
    
    def _scrape_with_requests(self, profile: Dict, query: str, max_results: int) -> List[Dict]:
        """Enhanced static HTML scraping"""
        try:
            search_url = self._build_search_url(profile, query)
            print(f"Scraping URL: {search_url}")
            
            response = self.session.get(search_url, timeout=20)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Multi-pass extraction with multiple strategies
            articles = self._extract_articles_comprehensive(soup, profile, max_results)
            
            return articles
            
        except Exception as e:
            print(f"Requests scraping error: {e}")
            return []
    
    def _scrape_with_selenium(self, profile: Dict, query: str, max_results: int) -> List[Dict]:
        """Enhanced JavaScript rendering with smart waiting"""
        driver = None
        try:
            search_url = self._build_search_url(profile, query)
            print(f"Selenium scraping URL: {search_url}")
            
            options = FirefoxOptions()
            options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("--window-size=1920,1080")
            options.page_load_strategy = 'normal'
            
            service = FirefoxService(GeckoDriverManager().install())
            driver = webdriver.Firefox(service=service, options=options)
            driver.set_page_load_timeout(30)
            
            driver.get(search_url)
            
            # Progressive waiting strategy
            wait = WebDriverWait(driver, 15)
            
            # Wait for common article indicators
            try:
                wait.until(lambda d: (
                    len(d.find_elements(By.TAG_NAME, "article")) > 0 or
                    len(d.find_elements(By.TAG_NAME, "h2")) > 5 or
                    len(d.find_elements(By.XPATH, "//a[string-length(text()) > 20]")) > 5
                ))
            except:
                # Fallback: just wait a bit
                time.sleep(4)
            
            # Scroll to trigger lazy loading
            last_height = driver.execute_script("return document.body.scrollHeight")
            for scroll_attempt in range(4):
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1)
                new_height = driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height
            
            # Scroll back to top to ensure all content is in DOM
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(1)
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            articles = self._extract_articles_comprehensive(soup, profile, max_results)
            
            return articles
            
        except Exception as e:
            print(f"Selenium scraping error: {e}")
            return []
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass
    
    def _scrape_homepage(self, profile: Dict, max_results: int) -> List[Dict]:
        """Scrape homepage and recent articles section"""
        articles = []
        try:
            # Try homepage
            response = self.session.get(profile['base_url'], timeout=15)
            soup = BeautifulSoup(response.content, 'html.parser')
            articles.extend(self._extract_articles_comprehensive(soup, profile, max_results))
            
            # Try common article listing pages
            for path in ['/news', '/latest', '/articles', '/stories']:
                try:
                    url = profile['base_url'].rstrip('/') + path
                    response = self.session.get(url, timeout=10)
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.content, 'html.parser')
                        articles.extend(self._extract_articles_comprehensive(soup, profile, max_results))
                except:
                    continue
            
            return articles
        except:
            return articles
    
    def _extract_articles_comprehensive(self, soup: BeautifulSoup, profile: Dict, max_results: int) -> List[Dict]:
        """Multi-strategy comprehensive article extraction"""
        articles = []
        selectors = profile['selectors']
        base_url = profile['base_url']
        
        # Pass 1: Container-based extraction (most reliable)
        container_articles = self._extract_from_containers(soup, selectors, base_url, max_results * 3)
        articles.extend(container_articles)
        
        # Pass 2: Direct link mining (for sites without clear containers)
        if len(articles) < max_results:
            link_articles = self._extract_from_links(soup, base_url, selectors)
            articles.extend(link_articles)
        
        # Pass 3: Semantic HTML extraction (article tags, schema.org)
        if len(articles) < max_results:
            semantic_articles = self._extract_semantic_articles(soup, base_url)
            articles.extend(semantic_articles)
        
        return articles
    
    def _extract_from_containers(self, soup: BeautifulSoup, selectors: Dict, base_url: str, limit: int) -> List[Dict]:
        """Extract articles from detected containers"""
        articles = []
        containers = self._find_containers(soup, selectors['article_container'], limit)
        
        for container in containers:
            article = self._extract_article_from_element(container, selectors, base_url)
            if self._is_valid_article(article):
                articles.append(article)
        
        return articles
    
    def _extract_from_links(self, soup: BeautifulSoup, base_url: str, selectors: Dict) -> List[Dict]:
        """Extract articles by analyzing all links"""
        articles = []
        domain = urlparse(base_url).netloc
        links = soup.find_all('a', href=True, limit=300)
        
        for link in links:
            href = link.get('href', '')
            text = link.get_text(strip=True)
            
            # Apply filtering rules
            if not self._is_valid_article_link(href, text, domain):
                continue
            
            url = urljoin(base_url, href)
            
            # Look for description in surrounding context
            description = self._find_description_near_link(link)
            
            article = {
                'headline': text[:300],
                'url': url,
                'description': description,
                'source': domain
            }
            
            if self._is_valid_article(article):
                articles.append(article)
        
        return articles
    
    def _extract_semantic_articles(self, soup: BeautifulSoup, base_url: str) -> List[Dict]:
        """Extract using semantic HTML and microdata"""
        articles = []
        domain = urlparse(base_url).netloc
        
        # Find article tags
        for article_elem in soup.find_all('article', limit=100):
            headline_elem = article_elem.find(['h1', 'h2', 'h3', 'h4'])
            link_elem = article_elem.find('a', href=True)
            
            if headline_elem and link_elem:
                article = {
                    'headline': headline_elem.get_text(strip=True),
                    'url': urljoin(base_url, link_elem['href']),
                    'description': '',
                    'source': domain
                }
                
                # Try to find description
                desc_elem = article_elem.find('p')
                if desc_elem:
                    article['description'] = desc_elem.get_text(strip=True)[:300]
                
                if self._is_valid_article(article):
                    articles.append(article)
        
        # Find schema.org articles
        for item in soup.find_all(itemtype=re.compile(r'Article|NewsArticle', re.I)):
            headline = item.find(itemprop='headline')
            url = item.find(itemprop='url')
            
            if headline and url:
                article = {
                    'headline': headline.get_text(strip=True),
                    'url': urljoin(base_url, url.get('href', '')),
                    'description': '',
                    'source': domain
                }
                
                desc = item.find(itemprop='description')
                if desc:
                    article['description'] = desc.get_text(strip=True)[:300]
                
                if self._is_valid_article(article):
                    articles.append(article)
        
        return articles
    
    def _find_containers(self, soup: BeautifulSoup, selectors: List[str], limit: int) -> List:
        """Find article containers using multiple selectors"""
        containers = []
        seen = set()
        
        for selector in selectors:
            try:
                elements = soup.select(selector, limit=limit)
                for elem in elements:
                    # Use element hash to avoid duplicates
                    elem_hash = self._element_hash(elem)
                    if elem_hash not in seen:
                        containers.append(elem)
                        seen.add(elem_hash)
                        if len(containers) >= limit:
                            return containers
            except Exception as e:
                continue
        
        return containers
    
    def _extract_article_from_element(self, container, selectors: Dict, base_url: str) -> Dict:
        """Extract complete article data from a container element"""
        article = {'source': urlparse(base_url).netloc}
        
        # Extract headline (try multiple selectors)
        for selector in selectors['headline']:
            try:
                elem = container.select_one(selector)
                if elem:
                    text = elem.get_text(strip=True)
                    if 15 < len(text) < 500:  # Reasonable headline length
                        article['headline'] = text
                        break
            except:
                continue
        
        # Extract URL (multiple strategies)
        link = self._find_article_link(container, selectors['headline'])
        if link:
            href = link.get('href', '')
            if href:
                article['url'] = urljoin(base_url, href)
        
        # Extract description
        for selector in selectors['description']:
            try:
                elem = container.select_one(selector)
                if elem:
                    text = elem.get_text(strip=True)
                    # Must be meaningful and different from headline
                    if 30 < len(text) < 1000 and text != article.get('headline', ''):
                        article['description'] = text[:400]
                        break
            except:
                continue
        
        # If no description found, try generic paragraph search
        if not article.get('description'):
            paragraphs = container.find_all('p', limit=3)
            for p in paragraphs:
                text = p.get_text(strip=True)
                if 30 < len(text) < 1000 and text != article.get('headline', ''):
                    article['description'] = text[:400]
                    break
        
        return article
    
    def _find_article_link(self, container, headline_selectors: List[str]) -> Optional:
        """Find the main article link in a container"""
        # Try finding link in headline first
        for selector in headline_selectors:
            try:
                elem = container.select_one(selector)
                if elem:
                    # Check if headline itself is a link
                    if elem.name == 'a':
                        return elem
                    # Check if headline is inside a link
                    parent_link = elem.find_parent('a')
                    if parent_link:
                        return parent_link
                    # Check if headline contains a link
                    child_link = elem.find('a')
                    if child_link:
                        return child_link
            except:
                continue
        
        # Fallback: find any prominent link
        links = container.find_all('a', href=True, limit=5)
        for link in links:
            text = link.get_text(strip=True)
            if len(text) > 15:  # Meaningful text
                return link
        
        return None
    
    def _find_description_near_link(self, link) -> str:
        """Find description text near a link element"""
        # Check parent and siblings
        parent = link.parent
        if parent:
            # Look for paragraphs in parent
            paragraphs = parent.find_all('p', limit=2)
            for p in paragraphs:
                text = p.get_text(strip=True)
                if 30 < len(text) < 1000:
                    return text[:400]
            
            # Look in next siblings
            for sibling in parent.find_next_siblings(limit=3):
                if sibling.name == 'p':
                    text = sibling.get_text(strip=True)
                    if 30 < len(text) < 1000:
                        return text[:400]
        
        return ''
    
    def _is_valid_article_link(self, href: str, text: str, domain: str) -> bool:
        """Validate if a link is likely an article"""
        # Text length check
        if not (15 < len(text) < 300):
            return False
        
        # Exclude navigation/utility links
        exclude_patterns = [
            '/tag/', '/tags/', '/category/', '/categories/',
            '/author/', '/about', '/contact', '/privacy', '/terms',
            '/login', '/register', '/signup', '/subscribe', '/newsletter',
            '#', 'javascript:', 'mailto:', 'tel:',
            '/feed', '/rss', '/sitemap', '/search',
            '.pdf', '.jpg', '.png', '.gif', '.mp4', '.xml'
        ]
        
        href_lower = href.lower()
        if any(pattern in href_lower for pattern in exclude_patterns):
            return False
        
        # Must be same domain or relative URL
        if href.startswith('http') and domain not in href:
            return False
        
        # Avoid generic/short URLs
        if href in ['/', '#', ''] or len(href) < 5:
            return False
        
        return True
    
    def _is_valid_article(self, article: Dict) -> bool:
        """Comprehensive article validation"""
        # Must have headline and URL
        if not article.get('headline') or not article.get('url'):
            return False
        
        headline = article['headline']
        url = article['url']
        
        # Headline checks
        if len(headline) < 15 or len(headline) > 500:
            return False
        
        # URL checks
        if not url.startswith('http'):
            return False
        
        # Avoid spam patterns in headline
        spam_patterns = [
            r'^\d+$',  # Only numbers
            r'^[A-Z\s]+$',  # All caps (unless reasonable length)
            r'(click here|read more)'  # Generic CTAs
        ]
        
        for pattern in spam_patterns:
            if re.match(pattern, headline, re.I):
                return False
        
        return True
    
    def _enrich_with_deep_content(self, articles: List[Dict], max_workers: int = 15) -> List[Dict]:
        """Extract full content from article pages in parallel"""
        print(f"Starting deep content extraction for {len(articles)} articles...")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_article = {
                executor.submit(self._extract_full_article_content, article): article
                for article in articles[:40]  # Limit to first 40 for performance
            }
            
            enriched = []
            completed = 0
            
            for future in as_completed(future_to_article):
                completed += 1
                try:
                    article = future.result(timeout=10)
                    if article:
                        enriched.append(article)
                except Exception as e:
                    # Keep original on failure
                    enriched.append(future_to_article[future])
                
                if completed % 10 == 0:
                    print(f"  Processed {completed}/{len(future_to_article)} articles")
        
        # Add remaining articles without deep scraping
        enriched.extend(articles[40:])
        
        return enriched
    
    def _extract_full_article_content(self, article: Dict) -> Dict:
        """Extract full content from individual article page using readability algorithm"""
        try:
            response = self.session.get(article['url'], timeout=12)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove noise elements
            noise_selectors = [
                'script', 'style', 'nav', 'footer', 'header', 'aside',
                '[class*="sidebar"]', '[class*="menu"]',
                '[class*="ad"]', '[class*="advertisement"]', '[class*="banner"]',
                '[class*="related"]', '[class*="recommended"]', '[class*="popular"]',
                '[class*="share"]', '[class*="social"]', '[class*="comment"]',
                '[class*="newsletter"]', '[class*="subscribe"]',
                'iframe', 'form', '[role="complementary"]'
            ]
            
            for selector in noise_selectors:
                for elem in soup.select(selector):
                    elem.decompose()
            
            # Also remove comments
            for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
                comment.extract()
            
            # Find main content using readability algorithm
            content = self._extract_content_readability(soup)
            
            if content and len(content) > 100:
                article['full_content'] = content[:1500]  # Store first 1500 chars
                
                # Try to extract metadata
                metadata = self._extract_metadata(soup)
                if metadata:
                    article.update(metadata)
            
            return article
            
        except Exception as e:
            return article
    
    def _extract_content_readability(self, soup: BeautifulSoup) -> str:
        """Extract main content using readability-style algorithm"""
        # Try semantic content selectors first
        content_selectors = [
            'article',
            '[role="main"]',
            'main',
            '[class*="article-content"]',
            '[class*="article-body"]',
            '[class*="post-content"]',
            '[class*="post-body"]',
            '[class*="entry-content"]',
            '[class*="story-body"]',
            '[class*="article__body"]',
            '[itemprop="articleBody"]',
            '#article-body',
            '#content',
            '.content'
        ]
        
        for selector in content_selectors:
            elements = soup.select(selector)
            for elem in elements:
                # Get all paragraphs
                paragraphs = elem.find_all('p')
                if len(paragraphs) >= 3:  # Meaningful article has multiple paragraphs
                    text = ' '.join([p.get_text(strip=True) for p in paragraphs])
                    if len(text) > 200:  # Substantial content
                        return self._clean_text(text)
        
        # Fallback: score all div elements by content density
        best_content = ''
        best_score = 0
        
        for div in soup.find_all('div'):
            paragraphs = div.find_all('p', recursive=False)
            if len(paragraphs) < 2:
                continue
            
            text = ' '.join([p.get_text(strip=True) for p in paragraphs])
            
            # Score based on: text length, number of paragraphs, link density
            score = len(text) + (len(paragraphs) * 50)
            links = div.find_all('a')
            link_text = sum(len(a.get_text(strip=True)) for a in links)
            link_density = link_text / len(text) if len(text) > 0 else 1
            
            if link_density < 0.3:  # Not too many links (navigation)
                score = score * (1 - link_density)
            else:
                score = score * 0.5
            
            if score > best_score and len(text) > 200:
                best_score = score
                best_content = text
        
        if best_content:
            return self._clean_text(best_content)
        
        # Last resort: get all paragraphs
        all_paragraphs = soup.find_all('p')
        if len(all_paragraphs) >= 3:
            text = ' '.join([p.get_text(strip=True) for p in all_paragraphs[:10]])
            return self._clean_text(text)
        
        return ''
    
    def _extract_metadata(self, soup: BeautifulSoup) -> Dict:
        """Extract article metadata (date, author)"""
        metadata = {}
        
        # Extract date
        date_elem = (soup.find('time') or 
                     soup.find(class_=re.compile(r'date|time|published', re.I)) or
                     soup.find(itemprop='datePublished'))
        if date_elem:
            date_text = date_elem.get('datetime') or date_elem.get_text(strip=True)
            if date_text:
                metadata['date'] = date_text[:50]
        
        # Extract author
        author_elem = (soup.find(rel='author') or
                       soup.find(class_=re.compile(r'author', re.I)) or
                       soup.find(itemprop='author'))
        if author_elem:
            author_text = author_elem.get_text(strip=True)
            if author_text and len(author_text) < 100:
                metadata['author'] = author_text
        
        return metadata
    
    def _clean_text(self, text: str) -> str:
        """Clean extracted text"""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove special characters but keep punctuation
        text = re.sub(r'[^\w\s\-.,!?:;()\'"]+', '', text)
        return text.strip()
    
    def _smart_filter_by_relevance(self, articles: List[Dict], query: str) -> List[Dict]:
        """Intelligent relevance filtering with semantic matching"""
        if not query or query.lower() in ['news', 'latest', 'today', 'all']:
            # Don't filter for generic queries
            return articles
        
        # Split query into terms
        query_terms = set(query.lower().split())
        
        # Also create partial matches (for compound terms like "corporate finance")
        query_lower = query.lower()
        
        filtered = []
        
        for article in articles:
            # Combine all text fields for matching
            searchable_text = ' '.join([
                article.get('headline', ''),
                article.get('description', ''),
                article.get('full_content', '')
            ]).lower()
            
            # Scoring system
            score = 0
            
            # Exact query match (highest score)
            if query_lower in searchable_text:
                score += 10
            
            # Individual term matches
            term_matches = sum(1 for term in query_terms if term in searchable_text)
            score += term_matches * 3
            
            # Headline matches (more important)
            headline_lower = article.get('headline', '').lower()
            if query_lower in headline_lower:
                score += 15
            headline_term_matches = sum(1 for term in query_terms if term in headline_lower)
            score += headline_term_matches * 5
            
            # Partial term matching (for words with common roots)
            for term in query_terms:
                if len(term) > 4:  # Only for longer words
                    partial = term[:4]  # Match first 4 chars
                    if partial in searchable_text:
                        score += 1
            
            # Keep article if it has any relevance
            if score > 0:
                article['relevance_score'] = score
                filtered.append(article)
            elif len(query_terms) == 1 and len(query) < 5:
                # For very short single-term queries, be more lenient
                article['relevance_score'] = 0
                filtered.append(article)
        
        # Sort by relevance
        filtered.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
        
        # If no matches found, return all articles (user may have misspelled or query may be too specific)
        if not filtered:
            print(f"⚠ No relevance matches for '{query}', returning all articles")
            return articles
        
        return filtered
    
    def _score_and_deduplicate(self, articles: List[Dict]) -> List[Dict]:
        """Score articles by quality and remove duplicates"""
        seen_urls = set()
        seen_headlines = set()
        unique_articles = []
        
        for article in articles:
            url = article.get('url', '')
            headline = article.get('headline', '').lower()
            
            # Skip duplicates
            if url in seen_urls or headline in seen_headlines:
                continue
            
            # Calculate quality score
            quality_score = 0
            
            # Has description
            if article.get('description') and len(article.get('description', '')) > 50:
                quality_score += 2
            
            # Has full content
            if article.get('full_content') and len(article.get('full_content', '')) > 200:
                quality_score += 3
            
            # Has metadata
            if article.get('date'):
                quality_score += 1
            if article.get('author'):
                quality_score += 1
            
            # Headline quality (not too short, not all caps)
            headline = article.get('headline', '')
            if 20 < len(headline) < 200:
                quality_score += 1
            if not headline.isupper():
                quality_score += 1
            
            article['quality_score'] = quality_score
            
            seen_urls.add(url)
            seen_headlines.add(headline.lower())
            unique_articles.append(article)
        
        # Sort by relevance first, then quality
        unique_articles.sort(
            key=lambda x: (x.get('relevance_score', 0), x.get('quality_score', 0)),
            reverse=True
        )
        
        return unique_articles
    
    def _element_hash(self, elem) -> str:
        """Generate hash for element to detect duplicates"""
        text = elem.get_text(strip=True)[:100]
        return hashlib.md5(text.encode()).hexdigest()
    
    def _build_search_url(self, profile: Dict, query: str) -> str:
        """Build search URL from profile and query"""
        pattern = profile.get('search_pattern', profile['base_url'])
        query_encoded = requests.utils.quote(query)
        
        if '{query}' in pattern:
            return pattern.replace('{query}', query_encoded)
        elif 'q=' in pattern or 's=' in pattern or 'search=' in pattern:
            # Replace existing query parameter
            pattern = re.sub(r'([?&]q=)[^&]*', r'\1' + query_encoded, pattern)
            pattern = re.sub(r'([?&]s=)[^&]*', r'\1' + query_encoded, pattern)
            pattern = re.sub(r'([?&]search=)[^&]*', r'\1' + query_encoded, pattern)
            return pattern
        else:
            # Return as-is (likely homepage or category page)
            return pattern