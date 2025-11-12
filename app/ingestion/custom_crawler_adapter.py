"""
Adapter for integrating custom Python crawler/scraper applications.

To use your custom crawler:
1. Create a Python script/module that implements the functions below
2. Update the imports in this file to point to your custom module
3. The system will automatically use your custom implementation
"""

from __future__ import annotations

import logging
from typing import Callable, Iterable, List, Tuple

from app.ingestion.text_splitter import split_text
from app.ingestion.types import DocumentChunk

logger = logging.getLogger(__name__)

# ============================================================================
# CUSTOM CRAWLER INTEGRATION POINT
# ============================================================================
# Replace these imports with your custom crawler module
# Example:
#   from your_custom_crawler import discover_urls, scrape_url_content

# ============================================================================
# IMPORT YOUR CUSTOM CRAWLER HERE
# ============================================================================
# Custom crawler is disabled - using default implementation
# To enable custom crawler, uncomment the code below:
#
# try:
#     from my_custom_crawler import discover_urls as custom_discover_urls, scrape_url_content
#     CUSTOM_CRAWLER_AVAILABLE = True
#     _custom_discover_urls = custom_discover_urls
#     _custom_scrape_url_content = scrape_url_content
#     logger.info("Custom crawler loaded successfully from my_custom_crawler.py")
# except ImportError as e:
#     CUSTOM_CRAWLER_AVAILABLE = False
#     _custom_discover_urls = None
#     _custom_scrape_url_content = None
#     logger.warning(f"Custom crawler not found, using default: {e}")
# except Exception as e:
#     CUSTOM_CRAWLER_AVAILABLE = False
#     _custom_discover_urls = None
#     _custom_scrape_url_content = None
#     logger.error(f"Error loading custom crawler: {e}", exc_info=True)

CUSTOM_CRAWLER_AVAILABLE = False
_custom_discover_urls = None
_custom_scrape_url_content = None
logger.info("Using default crawler implementation")


def discover_links(
    urls: Iterable[str],
    *,
    limit_per_domain: int = 100,
    max_depth: int = 3,
    on_discovered: Callable[[str, int], None] | None = None,
) -> List[Tuple[str, int]]:
    """
    Discover links from starting URLs.
    
    Expected interface from custom crawler:
    - Input: List of starting URLs
    - Output: List of tuples (url, depth)
    - Callback: Call on_discovered(url, depth) for each discovered URL
    
    Returns:
        List of tuples: [(url, depth), ...]
    """
    if CUSTOM_CRAWLER_AVAILABLE and _custom_discover_urls:
        try:
            logger.info("Using custom crawler for link discovery")
            discovered = _custom_discover_urls(
                urls,
                max_depth=max_depth,
                limit_per_domain=limit_per_domain,
                on_discovered=on_discovered
            )
            logger.info(f"Custom crawler discovered {len(discovered)} URLs")
            return discovered
        except Exception as e:
            logger.error(f"Custom crawler failed, falling back to default: {e}", exc_info=True)
    
    # Fallback to default implementation
    logger.info("Using default crawler for link discovery")
    from app.ingestion.crawler import discover_links as default_discover
    return default_discover(urls, limit_per_domain=limit_per_domain, max_depth=max_depth, on_discovered=on_discovered)


def scrape_page(
    url: str,
    *,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> tuple[str | None, list[DocumentChunk]]:
    """
    Scrape a single URL and return text content + chunks.
    
    Expected interface from custom scraper:
    - Input: URL string
    - Output: Tuple of (text_content, chunks_list)
      - text_content: str | None - The extracted text
      - chunks_list: list[DocumentChunk] - Text chunks ready for embedding
    
    Returns:
        Tuple: (extracted_text, chunks)
    """
    if CUSTOM_CRAWLER_AVAILABLE and _custom_scrape_url_content:
        try:
            logger.info(f"Using custom scraper for: {url}")
            text_content = _custom_scrape_url_content(url)
            if text_content and len(text_content.strip()) > 10:
                chunks = split_text(
                    text=text_content,
                    source=url,
                    metadata={"url": url},
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                )
                logger.info(f"Custom scraper succeeded: {len(text_content)} chars, {len(chunks)} chunks")
                return text_content, chunks
            else:
                logger.warning(f"Custom scraper returned insufficient text for {url}: {len(text_content) if text_content else 0} chars")
                return None, []
        except Exception as e:
            logger.error(f"Custom scraper failed for {url}, falling back to default: {e}", exc_info=True)
    
    # Fallback to default implementation
    logger.info(f"Using default scraper for: {url}")
    from app.ingestion.crawler import scrape_page as default_scrape
    return default_scrape(url, chunk_size=chunk_size, chunk_overlap=chunk_overlap)

