"""
Example template for your custom crawler/scraper.

Copy this file and implement your custom logic, then update 
app/ingestion/custom_crawler_adapter.py to import from your module.

REQUIRED FUNCTIONS:
1. discover_urls() - Discover links from starting URLs
2. scrape_url_content() - Scrape text content from a single URL
"""

from typing import Callable, Iterable, List, Tuple


def discover_urls(
    urls: Iterable[str],
    *,
    max_depth: int = 3,
    limit_per_domain: int = 100,
    on_discovered: Callable[[str, int], None] | None = None,
) -> List[Tuple[str, int]]:
    """
    Discover URLs by crawling from starting URLs.
    
    Args:
        urls: List of starting URLs to crawl from
        max_depth: Maximum depth to crawl (0 = only starting URLs)
        limit_per_domain: Maximum URLs per domain
        on_discovered: Callback function(url, depth) called for each discovered URL
    
    Returns:
        List of tuples: [(url, depth), ...]
        Example: [("https://example.com", 0), ("https://example.com/about", 1), ...]
    
    Example implementation:
    """
    discovered: List[Tuple[str, int]] = []
    visited = set()
    
    # Your custom crawling logic here
    # For example:
    # for url in urls:
    #     if url not in visited:
    #         visited.add(url)
    #         discovered.append((url, 0))
    #         if on_discovered:
    #             on_discovered(url, 0)
    #         
    #         # Crawl links from this page
    #         links = your_custom_crawl_function(url)
    #         for link, depth in process_links(links, max_depth=max_depth):
    #             if link not in visited:
    #                 visited.add(link)
    #                 discovered.append((link, depth))
    #                 if on_discovered:
    #                     on_discovered(link, depth)
    
    return discovered


def scrape_url_content(url: str) -> str | None:
    """
    Scrape text content from a single URL.
    
    Args:
        url: The URL to scrape
    
    Returns:
        Extracted text content as string, or None if scraping failed
    
    Example implementation:
    """
    # Your custom scraping logic here
    # For example:
    # 
    # try:
    #     # Use your preferred scraping library (Selenium, Scrapy, BeautifulSoup, etc.)
    #     response = your_custom_scraper.get(url)
    #     text = your_custom_scraper.extract_text(response)
    #     return text
    # except Exception as e:
    #     print(f"Failed to scrape {url}: {e}")
    #     return None
    
    return None


# ============================================================================
# INTEGRATION INSTRUCTIONS
# ============================================================================
"""
To integrate your custom crawler:

1. Create your custom crawler file (e.g., my_custom_crawler.py)
2. Implement the two functions above: discover_urls() and scrape_url_content()
3. Update app/ingestion/custom_crawler_adapter.py:
   
   Change this line:
       CUSTOM_CRAWLER_AVAILABLE = False
   
   To:
       from my_custom_crawler import discover_urls, scrape_url_content
       CUSTOM_CRAWLER_AVAILABLE = True
   
   And uncomment/modify the code in discover_links() and scrape_page() functions

4. Place your custom crawler file in the project root or app/ingestion/ directory
5. Restart the server

Your custom crawler will now be used instead of the default implementation!
"""

