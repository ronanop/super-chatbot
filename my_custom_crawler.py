import requests
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from collections import defaultdict, deque
import time
from typing import Iterable, List, Tuple, Callable, Set, Dict
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UniversalWebScraper:
    def __init__(self, headless: bool = True, timeout: int = 30, delay: float = 1.0):
        """
        Initialize the universal web scraper with Selenium for JavaScript-heavy sites.
        
        Args:
            headless: Run browser in headless mode
            timeout: Page load timeout in seconds
            delay: Delay between requests in seconds
        """
        self.timeout = timeout
        self.delay = delay
        self.driver = None
        self.setup_driver(headless)
        
    def setup_driver(self, headless: bool = True):
        """Setup Chrome driver with optimal settings for scraping."""
        try:
            chrome_options = Options()
            if headless:
                chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--disable-images")  # Speed up loading
            chrome_options.add_argument("--disable-javascript")  # Disable JS for faster text-only scraping
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
            
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.set_page_load_timeout(self.timeout)
        except Exception as e:
            logger.warning(f"Failed to setup Selenium driver: {e}. Falling back to requests.")
            self.driver = None

    def is_valid_url(self, url: str) -> bool:
        """Check if URL is valid and has http/https scheme."""
        try:
            result = urlparse(url)
            return all([result.scheme in ['http', 'https'], result.netloc])
        except:
            return False

    def normalize_url(self, url: str) -> str:
        """Normalize URL by removing fragments and sorting query parameters."""
        try:
            parsed = urlparse(url)
            # Remove fragment and normalize
            normalized = parsed._replace(fragment='', query='').geturl()
            return normalized.rstrip('/')
        except:
            return url

    def get_domain(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            return urlparse(url).netloc
        except:
            return ""

    def extract_links_selenium(self, url: str) -> Set[str]:
        """Extract links using Selenium (for JavaScript-heavy sites)."""
        links = set()
        try:
            self.driver.get(url)
            time.sleep(2)  # Wait for page to load
            
            # Find all anchor elements
            anchor_elements = self.driver.find_elements(By.TAG_NAME, "a")
            
            for element in anchor_elements:
                try:
                    href = element.get_attribute("href")
                    if href and self.is_valid_url(href):
                        normalized_url = self.normalize_url(href)
                        links.add(normalized_url)
                except:
                    continue
                    
        except Exception as e:
            logger.error(f"Error extracting links from {url} with Selenium: {e}")
            
        return links

    def extract_links_requests(self, html: str, base_url: str) -> Set[str]:
        """Extract links using requests and BeautifulSoup."""
        soup = BeautifulSoup(html, 'html.parser')
        links = set()
        
        for link in soup.find_all('a', href=True):
            href = link['href']
            try:
                absolute_url = urljoin(base_url, href)
                if self.is_valid_url(absolute_url):
                    normalized_url = self.normalize_url(absolute_url)
                    links.add(normalized_url)
            except:
                continue
        
        return links

    def extract_text_selenium(self, url: str) -> str:
        """Extract text content using Selenium."""
        try:
            if not self.driver:
                return self.extract_text_requests_fallback(url)
                
            self.driver.get(url)
            WebDriverWait(self.driver, self.timeout).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Get page source and extract text
            page_source = self.driver.page_source
            return self.clean_text_from_html(page_source)
            
        except TimeoutException:
            logger.warning(f"Timeout loading {url} with Selenium")
            return self.extract_text_requests_fallback(url)
        except Exception as e:
            logger.error(f"Error with Selenium for {url}: {e}")
            return self.extract_text_requests_fallback(url)

    def extract_text_requests_fallback(self, url: str) -> str:
        """Fallback text extraction using requests."""
        try:
            response = requests.get(
                url, 
                timeout=self.timeout,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
            )
            response.raise_for_status()
            return self.clean_text_from_html(response.text)
        except Exception as e:
            logger.error(f"Error with requests fallback for {url}: {e}")
            return ""

    def clean_text_from_html(self, html: str) -> str:
        """Extract and clean text from HTML content."""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Remove unwanted elements
            for element in soup(["script", "style", "nav", "header", "footer", "aside", "meta", "link"]):
                element.decompose()
            
            # Get text from main content areas first
            main_content = soup.find(['main', 'article', 'div'], class_=re.compile(r'content|main|article', re.I))
            if main_content:
                text = main_content.get_text(separator=' ', strip=True)
            else:
                text = soup.get_text(separator=' ', strip=True)
            
            # Clean up the text
            lines = []
            for line in text.splitlines():
                line = line.strip()
                if line and len(line) > 10:  # Filter out very short lines
                    lines.append(line)
            
            # Remove duplicate lines while preserving order
            seen = set()
            unique_lines = []
            for line in lines:
                if line not in seen and len(line) > 10:
                    seen.add(line)
                    unique_lines.append(line)
            
            cleaned_text = '\n'.join(unique_lines)
            
            # Final cleanup of extra whitespace
            cleaned_text = re.sub(r'\s+', ' ', cleaned_text)
            cleaned_text = re.sub(r'\n\s*\n', '\n', cleaned_text)
            
            return cleaned_text.strip()
            
        except Exception as e:
            logger.error(f"Error cleaning text from HTML: {e}")
            return ""

    def discover_urls(
        self,
        urls: Iterable[str],
        *,
        max_depth: int = 3,
        limit_per_domain: int = 100,
        on_discovered: Callable[[str, int], None] | None = None
    ) -> List[Tuple[str, int]]:
        """
        Discover URLs by crawling from starting URLs using BFS approach.
        Works with both static and JavaScript-heavy websites.
        """
        discovered = []
        visited = set()
        domain_count = defaultdict(int)
        queue = deque()
        
        # Initialize queue with starting URLs
        for url in urls:
            normalized_url = self.normalize_url(url)
            if (self.is_valid_url(normalized_url) and 
                normalized_url not in visited and 
                domain_count[self.get_domain(normalized_url)] < limit_per_domain):
                
                queue.append((normalized_url, 0))
                visited.add(normalized_url)
                discovered.append((normalized_url, 0))
                domain_count[self.get_domain(normalized_url)] += 1
                
                if on_discovered:
                    on_discovered(normalized_url, 0)
        
        # BFS crawling
        while queue:
            current_url, depth = queue.popleft()
            
            if depth >= max_depth:
                continue
            
            try:
                logger.info(f"Crawling: {current_url} (depth: {depth})")
                
                # Try Selenium first for JavaScript sites, fallback to requests
                if self.driver:
                    links = self.extract_links_selenium(current_url)
                else:
                    response = requests.get(current_url, timeout=self.timeout)
                    links = self.extract_links_requests(response.text, current_url)
                
                # Process discovered links
                for link in links:
                    normalized_link = self.normalize_url(link)
                    domain = self.get_domain(normalized_link)
                    
                    if (self.is_valid_url(normalized_link) and 
                        normalized_link not in visited and 
                        domain_count[domain] < limit_per_domain):
                        
                        visited.add(normalized_link)
                        discovered.append((normalized_link, depth + 1))
                        domain_count[domain] += 1
                        queue.append((normalized_link, depth + 1))
                        
                        if on_discovered:
                            on_discovered(normalized_link, depth + 1)
                
                time.sleep(self.delay)  # Be polite
                
            except Exception as e:
                logger.error(f"Error crawling {current_url}: {e}")
                continue
        
        return discovered

    def scrape_url_content(self, url: str) -> str | None:
        """
        Scrape text content from a single URL.
        Uses Selenium for JavaScript-heavy sites, falls back to requests.
        """
        try:
            logger.info(f"Scraping content from: {url}")
            
            # Try Selenium first for better JavaScript support
            if self.driver:
                text_content = self.extract_text_selenium(url)
            else:
                text_content = self.extract_text_requests_fallback(url)
            
            # Validate we got meaningful content
            if text_content and len(text_content.strip()) > 50:  # At least 50 characters
                return text_content
            else:
                logger.warning(f"Insufficient content from {url}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to scrape {url}: {e}")
            return None

    def close(self):
        """Clean up resources."""
        if self.driver:
            self.driver.quit()


# Create global instance for the required functions
_scraper = UniversalWebScraper()

def discover_urls(
    urls: Iterable[str],
    *,
    max_depth: int = 3,
    limit_per_domain: int = 100,
    on_discovered: Callable[[str, int], None] | None = None
) -> List[Tuple[str, int]]:
    """Public interface for URL discovery."""
    return _scraper.discover_urls(
        urls=urls,
        max_depth=max_depth,
        limit_per_domain=limit_per_domain,
        on_discovered=on_discovered
    )

def scrape_url_content(url: str) -> str | None:
    """Public interface for content scraping."""
    return _scraper.scrape_url_content(url)

# Example usage and test
if __name__ == "__main__":
    # Test the scraper
    test_urls = ["https://example.com"]
    
    print("Testing URL discovery...")
    discovered_urls = discover_urls(test_urls, max_depth=1, limit_per_domain=10)
    print(f"Discovered {len(discovered_urls)} URLs:")
    for url, depth in discovered_urls[:5]:  # Show first 5
        print(f"  Depth {depth}: {url}")
    
    print("\nTesting content scraping...")
    if discovered_urls:
        test_url = discovered_urls[0][0]
        content = scrape_url_content(test_url)
        if content:
            print(f"Scraped content sample (first 500 chars):")
            print(content[:500] + "..." if len(content) > 500 else content)
        else:
            print("Failed to scrape content")
    
    # Clean up
    _scraper.close()