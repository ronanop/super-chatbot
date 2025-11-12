# Custom Crawler Integration Guide

This guide explains how to integrate your custom Python crawler/scraper into the application.

## Quick Start

1. **Create your custom crawler file** (e.g., `my_custom_crawler.py`)
2. **Implement two required functions** (see template below)
3. **Update the adapter** to use your crawler
4. **Restart the server**

## Required Functions

Your custom crawler must provide these two functions:

### 1. `discover_urls()`

**Purpose:** Discover URLs by crawling from starting URLs

**Signature:**
```python
def discover_urls(
    urls: Iterable[str],
    *,
    max_depth: int = 3,
    limit_per_domain: int = 100,
    on_discovered: Callable[[str, int], None] | None = None,
) -> List[Tuple[str, int]]:
```

**Parameters:**
- `urls`: List of starting URLs to crawl from
- `max_depth`: Maximum crawl depth (0 = only starting URLs)
- `limit_per_domain`: Maximum URLs per domain
- `on_discovered`: Optional callback function(url, depth) called for each discovered URL

**Returns:**
- List of tuples: `[(url, depth), ...]`
- Example: `[("https://example.com", 0), ("https://example.com/about", 1)]`

**Example:**
```python
def discover_urls(urls, *, max_depth=3, limit_per_domain=100, on_discovered=None):
    discovered = []
    visited = set()
    
    for url in urls:
        if url not in visited:
            visited.add(url)
            discovered.append((url, 0))
            if on_discovered:
                on_discovered(url, 0)
            
            # Your crawling logic here
            links = crawl_page_for_links(url)
            for link in links:
                if link not in visited:
                    discovered.append((link, 1))
                    if on_discovered:
                        on_discovered(link, 1)
    
    return discovered
```

### 2. `scrape_url_content()`

**Purpose:** Scrape text content from a single URL

**Signature:**
```python
def scrape_url_content(url: str) -> str | None:
```

**Parameters:**
- `url`: The URL to scrape

**Returns:**
- Extracted text content as string, or `None` if scraping failed

**Example:**
```python
def scrape_url_content(url: str) -> str | None:
    try:
        # Your scraping logic here
        response = requests.get(url)
        html = response.text
        text = extract_text_from_html(html)  # Your extraction method
        return text
    except Exception as e:
        print(f"Failed to scrape {url}: {e}")
        return None
```

## Integration Steps

### Step 1: Create Your Custom Crawler

Create a file (e.g., `my_custom_crawler.py`) with your implementation:

```python
# my_custom_crawler.py

def discover_urls(urls, *, max_depth=3, limit_per_domain=100, on_discovered=None):
    # Your implementation
    pass

def scrape_url_content(url: str) -> str | None:
    # Your implementation
    pass
```

### Step 2: Update the Adapter

Edit `app/ingestion/custom_crawler_adapter.py`:

1. **Change the import:**
   ```python
   # Replace this:
   CUSTOM_CRAWLER_AVAILABLE = False
   
   # With this:
   from my_custom_crawler import discover_urls as custom_discover_urls, scrape_url_content
   CUSTOM_CRAWLER_AVAILABLE = True
   ```

2. **Update the `discover_links()` function:**
   ```python
   def discover_links(...):
       if CUSTOM_CRAWLER_AVAILABLE:
           try:
               logger.info("Using custom crawler for link discovery")
               discovered = custom_discover_urls(
                   urls,
                   max_depth=max_depth,
                   limit_per_domain=limit_per_domain,
                   on_discovered=on_discovered
               )
               return discovered
           except Exception as e:
               logger.error(f"Custom crawler failed: {e}")
       # Fallback to default...
   ```

3. **Update the `scrape_page()` function:**
   ```python
   def scrape_page(url, *, chunk_size=None, chunk_overlap=None):
       if CUSTOM_CRAWLER_AVAILABLE:
           try:
               logger.info(f"Using custom scraper for: {url}")
               text_content = scrape_url_content(url)
               if text_content:
                   from app.ingestion.text_splitter import split_text
                   from app.ingestion.types import DocumentChunk
                   
                   chunks = split_text(
                       text=text_content,
                       source=url,
                       metadata={"url": url},
                       chunk_size=chunk_size,
                       chunk_overlap=chunk_overlap,
                   )
                   return text_content, chunks
               return None, []
           except Exception as e:
               logger.error(f"Custom scraper failed: {e}")
       # Fallback to default...
   ```

### Step 3: Place Your File

Place your custom crawler file in one of these locations:
- Project root: `C:\Users\risha\Downloads\finalbot\my_custom_crawler.py`
- Or in the ingestion folder: `C:\Users\risha\Downloads\finalbot\app\ingestion\my_custom_crawler.py`

### Step 4: Restart Server

Restart your FastAPI server:
```powershell
taskkill /IM uvicorn.exe /F
cd C:\Users\risha\Downloads\finalbot
.\.venv\Scripts\activate
uvicorn app.main:app --host 0.0.0.0 --reload
```

## Testing Your Custom Crawler

Test your functions independently:

```python
# test_custom_crawler.py
from my_custom_crawler import discover_urls, scrape_url_content

# Test discovery
urls = ["https://example.com"]
discovered = discover_urls(urls, max_depth=2)
print(f"Discovered {len(discovered)} URLs")

# Test scraping
text = scrape_url_content("https://example.com")
print(f"Scraped {len(text) if text else 0} characters")
```

## Notes

- Your custom crawler can use **any Python library** (Selenium, Scrapy, BeautifulSoup, etc.)
- The system will automatically chunk the text you return
- If your crawler fails, it falls back to the default implementation
- Check server logs to see which implementation is being used

## Troubleshooting

**Import Error:**
- Make sure your file is in the correct location
- Check that function names match exactly

**Function Not Called:**
- Verify `CUSTOM_CRAWLER_AVAILABLE = True` in the adapter
- Check server logs for error messages

**Scraping Fails:**
- Ensure `scrape_url_content()` returns a string (not None) with actual text
- Minimum 10 characters required

## Example: Using Selenium

```python
# my_custom_crawler.py
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

def discover_urls(urls, *, max_depth=3, limit_per_domain=100, on_discovered=None):
    # Your Selenium-based crawling logic
    pass

def scrape_url_content(url: str) -> str | None:
    options = Options()
    options.add_argument('--headless')
    driver = webdriver.Chrome(options=options)
    try:
        driver.get(url)
        text = driver.find_element("tag name", "body").text
        return text
    finally:
        driver.quit()
```

