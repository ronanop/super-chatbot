from __future__ import annotations

import logging
import re
import sys
import time
from collections import defaultdict, deque
from typing import Callable, Iterable, List, Sequence, Set, Tuple
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Try to import Selenium
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, WebDriverException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    logger.warning("Selenium not available - will use requests only")

from app.ingestion.text_splitter import split_text
from app.ingestion.types import DocumentChunk, IngestedDocument

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
MAX_CONTENT_LENGTH = 1_000_000  # 1 MB
REQUEST_TIMEOUT = 30
SELENIUM_TIMEOUT = 30

# Global browser instance (lazy-loaded)
_driver = None


class CrawlError(RuntimeError):
    pass


def _get_driver():
    """Get or create a Selenium Chrome driver instance."""
    global _driver
    if not SELENIUM_AVAILABLE:
        logger.warning("Selenium not available - falling back to HTTP requests")
        return None
    if _driver is None:
        try:
            logger.info("Starting Selenium Chrome driver...")
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument(f"--user-agent={USER_AGENT}")
            
            _driver = webdriver.Chrome(options=chrome_options)
            _driver.set_page_load_timeout(SELENIUM_TIMEOUT)
            logger.info("Selenium Chrome driver started successfully")
        except Exception as e:
            logger.error(f"Failed to start Selenium driver: {e}", exc_info=True)
            _driver = None
    return _driver


def cleanup_browser() -> None:
    """Clean up browser resources."""
    global _driver
    if _driver:
        try:
            _driver.quit()
        except Exception:
            pass
        _driver = None


def _extract_text_from_html(html: str) -> str:
    """Extract clean text from HTML using BeautifulSoup, preserving structure."""
    try:
        soup = BeautifulSoup(html, 'html.parser')
        
        # Remove unwanted elements (but keep structure elements)
        for element in soup(["script", "style", "nav", "header", "footer", "aside", "meta", "link", "noscript", "iframe", "svg"]):
            element.decompose()
        
        # Find main content area
        main_content = soup.find(['main', 'article', 'div'], class_=re.compile(r'content|main|article|post|entry', re.I))
        if not main_content:
            main_content = soup.find('body')
        if not main_content:
            main_content = soup
        
        # Extract text while preserving structure
        def extract_structured_text(element):
            """Recursively extract text preserving structure."""
            # Handle text nodes
            if not hasattr(element, 'name') or element.name is None:
                if hasattr(element, 'string') and element.string:
                    return element.string.strip()
                return ""
            
            # Skip unwanted tags
            if element.name in ['script', 'style', 'meta', 'link', 'noscript', 'iframe', 'svg']:
                return ""
            
            result = []
            
            # Handle headings - add extra line breaks for structure
            if element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                text = element.get_text(separator=' ', strip=True)
                if text:
                    result.append(f"\n\n{text}\n")
            
            # Handle paragraphs - preserve as separate blocks
            elif element.name == 'p':
                text = element.get_text(separator=' ', strip=True)
                if text and len(text) > 5:
                    result.append(f"{text}\n")
            
            # Handle lists - preserve structure with bullets
            elif element.name in ['ul', 'ol']:
                items = element.find_all('li', recursive=False)
                for item in items:
                    item_text = item.get_text(separator=' ', strip=True)
                    if item_text:
                        result.append(f"• {item_text}\n")
                if result:
                    result.append("\n")
            
            # Handle list items individually
            elif element.name == 'li':
                text = element.get_text(separator=' ', strip=True)
                if text:
                    result.append(f"• {text}\n")
            
            # Handle line breaks
            elif element.name == 'br':
                result.append("\n")
            
            # Handle block containers - process children recursively
            elif element.name in ['div', 'section', 'article', 'main', 'body']:
                # Process all children recursively
                for child in element.children:
                    child_text = extract_structured_text(child)
                    if child_text:
                        result.append(child_text)
            
            # For other block elements, process children
            elif element.name in ['header', 'footer', 'aside', 'nav']:
                # Skip these containers but process their text content
                text = element.get_text(separator=' ', strip=True)
                if text and len(text) > 20:
                    result.append(f"{text}\n")
            
            # For inline elements and others, get text and process children
            else:
                # Check if element has children that need processing
                has_children = any(hasattr(child, 'name') and child.name for child in element.children)
                if has_children:
                    # Process children
                    for child in element.children:
                        child_text = extract_structured_text(child)
                        if child_text:
                            result.append(child_text)
                else:
                    # Leaf node, just get text
                    text = element.get_text(separator=' ', strip=True)
                    if text and len(text) > 10:
                        result.append(f"{text}\n")
            
            return "".join(result)
        
        # Extract structured text
        structured_text = extract_structured_text(main_content)
        
        # Clean up excessive whitespace while preserving structure
        # Replace multiple newlines (3+) with double newline
        structured_text = re.sub(r'\n{3,}', '\n\n', structured_text)
        # Clean up spaces around newlines
        structured_text = re.sub(r' +\n', '\n', structured_text)
        structured_text = re.sub(r'\n +', '\n', structured_text)
        # Remove excessive spaces (3+) but keep single spaces
        structured_text = re.sub(r' {2,}', ' ', structured_text)
        
        # Remove duplicate consecutive lines (but preserve structure)
        lines = structured_text.split('\n')
        cleaned_lines = []
        prev_line = None
        for line in lines:
            line = line.strip()
            if not line:
                # Keep single empty lines for structure
                if cleaned_lines and cleaned_lines[-1]:
                    cleaned_lines.append("")
                continue
            # Skip if same as previous line
            if line == prev_line:
                continue
            # Skip very short lines unless they're bullets or headings
            if len(line) < 5 and not line.startswith('•') and not any(line.startswith(f'H{i}') for i in range(1, 7)):
                continue
            cleaned_lines.append(line)
            prev_line = line
        
        result = '\n'.join(cleaned_lines)
        
        # Final cleanup
        result = result.strip()
        
        # Ensure minimum length
        if len(result) < 10:
            return ""
        
        return result
        
    except Exception as e:
        logger.error(f"Error extracting structured text from HTML: {e}")
        # Fallback to simple extraction
        try:
            soup = BeautifulSoup(html, 'html.parser')
            for element in soup(["script", "style", "nav", "header", "footer", "aside", "meta", "link", "noscript"]):
                element.decompose()
            text = soup.get_text(separator='\n', strip=True)
            # Clean up
            lines = [line.strip() for line in text.splitlines() if line.strip() and len(line.strip()) > 10]
            return '\n'.join(lines)
        except Exception:
            return ""


def _fetch_with_selenium(url: str) -> tuple[str, list[str]] | None:
    """Fetch URL content using Selenium (handles JavaScript)."""
    driver = _get_driver()
    if not driver:
        return None
    
    try:
        logger.info(f"Selenium: Loading {url}")
        driver.get(url)
        
        # Wait for page to load
        WebDriverWait(driver, SELENIUM_TIMEOUT).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        time.sleep(2)  # Additional wait for JavaScript content
        
        # Get page source and extract text
        html = driver.page_source
        text = _extract_text_from_html(html)
        
        # Require at least 10 characters
        if not text or len(text.strip()) < 10:
            logger.warning(f"Selenium: Text too short for {url}: {len(text.strip()) if text else 0} chars")
            return None
        
        # Extract links using BeautifulSoup
        links = _extract_links_from_html(html, url)
        
        logger.info(f"Selenium: Successfully scraped {url}: {len(text)} chars, {len(links)} links")
        return text, links
    except TimeoutException:
        logger.warning(f"Selenium timeout for {url}")
        return None
    except Exception as e:
        logger.error(f"Selenium error for {url}: {e}", exc_info=True)
        return None


def is_image_url(url: str) -> bool:
    """Check if URL points to an image file."""
    parsed = urlparse(url)
    path_lower = parsed.path.lower()
    image_extensions = ['.png', '.jpg', '.jpeg', '.webp', '.gif', '.svg', '.bmp', '.ico']
    return any(path_lower.endswith(ext) for ext in image_extensions)


def _extract_links_from_html(html: str, base_url: str) -> list[str]:
    """Extract links from HTML using BeautifulSoup."""
    links = set()
    try:
        soup = BeautifulSoup(html, 'html.parser')
        for link in soup.find_all('a', href=True):
            href = link['href']
            try:
                absolute_url = urljoin(base_url, href)
                parsed = urlparse(absolute_url)
                # Only keep http/https URLs
                if parsed.scheme in ['http', 'https'] and parsed.netloc:
                    # Skip image URLs
                    if is_image_url(absolute_url):
                        continue
                    # Remove fragments, normalize
                    clean = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
                    if parsed.query:
                        clean += f"?{parsed.query}"
                    links.add(clean.rstrip('/'))
            except Exception:
                continue
    except Exception as e:
        logger.warning(f"Error extracting links: {e}")
    return list(links)


def _normalize_domain(url: str) -> str:
    """Normalize domain for comparison (remove www, convert to lowercase)."""
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def _is_same_domain(root: str, candidate: str) -> bool:
    """Check if candidate URL is from the same domain as root."""
    root_domain = _normalize_domain(root)
    candidate_domain = _normalize_domain(candidate)
    return root_domain == candidate_domain


def _should_visit(url: str, robots_cache: dict[str, RobotFileParser | None]) -> bool:
    parsed = urlparse(url)
    base = f"{parsed.scheme}://{parsed.netloc}"

    if base not in robots_cache:
        robots = RobotFileParser()
        robots.set_url(urljoin(base, "/robots.txt"))
        try:
            robots.read()
        except Exception:
            robots = None
        robots_cache[base] = robots

    robots = robots_cache.get(base)
    if not robots:
        return True

    return robots.can_fetch(USER_AGENT, url)


def _fetch(url: str) -> tuple[str, list[str]] | None:
    """Fetch URL content. Uses Selenium for JavaScript sites, falls back to requests for simple sites."""
    # Try Selenium first (handles JavaScript)
    if SELENIUM_AVAILABLE:
        result = _fetch_with_selenium(url)
        if result:
            return result
    
    # Fallback to simple HTTP request for static sites
    headers = {"User-Agent": USER_AGENT}
    try:
        logger.info(f"HTTP: Fetching {url}")
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT, allow_redirects=True)
        response.raise_for_status()
        
        if len(response.content) > MAX_CONTENT_LENGTH:
            return None
        
        html = response.text
        text = _extract_text_from_html(html)
        
        # Require at least 10 characters (very lenient)
        if not text or len(text.strip()) < 10:
            logger.warning(f"HTTP: Text too short for {url}: {len(text.strip()) if text else 0} chars")
            return None
        
        # Extract links using BeautifulSoup
        links = _extract_links_from_html(html, url)
        
        logger.info(f"HTTP: Successfully scraped {url}: {len(text)} chars, {len(links)} links")
        return text, links
    except Exception as e:
        logger.error(f"HTTP fetch error for {url}: {e}", exc_info=True)
        return None


def discover_links(
    urls: Iterable[str],
    *,
    limit_per_domain: int = 100,
    max_depth: int = 3,
    on_discovered: Callable[[str, int], None] | None = None,
) -> List[Tuple[str, int]]:
    """Breadth-first crawl that discovers same-domain links."""
    visited: set[str] = set()
    robots_cache: dict[str, RobotFileParser | None] = {}

    # queue entries: (url, depth, root_reference)
    queue: deque[Tuple[str, int, str]] = deque()
    for url in urls:
        normalized = url.rstrip("/")
        # Skip image URLs
        if is_image_url(normalized):
            logger.info(f"Skipping image URL: {normalized}")
            continue
        queue.append((normalized, 0, normalized))

    discovered: List[Tuple[str, int]] = []
    pages_per_domain: dict[str, int] = {}

    while queue:
        current, depth, root = queue.popleft()
        
        # Skip if already visited or too deep
        if current in visited:
            continue
        if depth > max_depth:
            continue
            
        visited.add(current)

        parsed = urlparse(current)
        domain_key = _normalize_domain(current)
        pages_per_domain.setdefault(domain_key, 0)
        if pages_per_domain[domain_key] >= limit_per_domain:
            continue

        if not _should_visit(current, robots_cache):
            continue

        discovered.append((current, depth))
        if on_discovered:
            try:
                on_discovered(current, depth)
            except Exception:
                pass

        fetched = _fetch(current)
        if not fetched:
            continue

        _, discovered_links = fetched
        pages_per_domain[domain_key] += 1

        # Add discovered links to queue
        for link in discovered_links:
            # Normalize link
            normalized_link = link.rstrip("/")
            # Skip image URLs
            if is_image_url(normalized_link):
                continue
            if not _is_same_domain(root, normalized_link):
                continue
            if normalized_link in visited:
                continue
            # Avoid adding duplicates to queue
            if not any(q[0] == normalized_link for q in queue):
                queue.append((normalized_link, depth + 1, root))

        time.sleep(0.3)  # Reduced delay for faster crawling

    return discovered


def scrape_urls(
    urls: Sequence[str],
    *,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
    progress_callback: Callable[[int, int, str, bool], None] | None = None,
) -> list[IngestedDocument]:
    unique_urls = []
    seen = set()
    for url in urls:
        if url not in seen:
            unique_urls.append(url)
            seen.add(url)

    results: list[IngestedDocument] = []
    total = len(unique_urls)
    processed = 0

    for url in unique_urls:
        fetched = _fetch(url)
        success = fetched is not None
        if success:
            extracted_text, _ = fetched
            chunks: list[DocumentChunk] = split_text(
                text=extracted_text,
                source=url,
                metadata={"url": url},
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            )
            results.append(IngestedDocument(path=None, source=url, chunks=chunks))
        processed += 1

        if progress_callback:
            try:
                progress_callback(processed, total, url, success)
            except Exception:
                pass

        time.sleep(0.5)

    return results


def scrape_page(
    url: str,
    *,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> tuple[str | None, list[DocumentChunk]]:
    # Skip image URLs
    if is_image_url(url):
        logger.info(f"Skipping image URL: {url}")
        return None, []
    
    fetched = _fetch(url)
    if not fetched:
        return None, []
    extracted_text, _ = fetched
    chunks: list[DocumentChunk] = split_text(
        text=extracted_text,
        source=url,
        metadata={"url": url},
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    return extracted_text, chunks


def crawl_urls(
    urls: Iterable[str],
    *,
    limit_per_domain: int = 100,
    max_depth: int = 3,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> list[IngestedDocument]:
    discovered = discover_links(
        urls,
        limit_per_domain=limit_per_domain,
        max_depth=max_depth,
    )
    ordered_urls = [url for url, _depth in discovered]
    return scrape_urls(
        ordered_urls,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
