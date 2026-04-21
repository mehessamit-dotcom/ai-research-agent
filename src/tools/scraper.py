"""Web scraper — extracts clean text content from web pages."""

from __future__ import annotations

import httpx
from bs4 import BeautifulSoup
from loguru import logger


# Tags that typically contain noise, not content
NOISE_TAGS = {
    "script", "style", "nav", "footer", "header", "aside",
    "form", "button", "iframe", "noscript", "svg", "img",
}

# Common content container tags
CONTENT_TAGS = {"article", "main", "section", "div", "p", "li", "td", "blockquote"}


async def scrape_page(url: str, max_chars: int = 8000) -> str:
    """
    Scrape a web page and return clean text content.
    
    Args:
        url: The URL to scrape.
        max_chars: Maximum characters to return (to keep LLM context manageable).
    
    Returns:
        Clean text content from the page, truncated to max_chars.
    """
    logger.info(f"🌐 Scraping: {url}")

    try:
        async with httpx.AsyncClient(
            timeout=15.0,
            follow_redirects=True,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            },
        ) as client:
            response = await client.get(url)
            response.raise_for_status()

        # Parse HTML
        soup = BeautifulSoup(response.text, "html.parser")

        # Remove noise elements
        for tag in soup.find_all(NOISE_TAGS):
            tag.decompose()

        # Try to find the main content area
        content = None
        for selector in ["article", "main", '[role="main"]', ".content", "#content"]:
            content = soup.select_one(selector)
            if content:
                break

        # Fall back to body
        if not content:
            content = soup.body or soup

        # Extract text
        text = content.get_text(separator="\n", strip=True)

        # Clean up excessive whitespace
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        clean_text = "\n".join(lines)

        # Truncate to max_chars
        if len(clean_text) > max_chars:
            clean_text = clean_text[:max_chars] + "\n\n[... content truncated ...]"

        logger.info(f"✅ Scraped {len(clean_text)} chars from {url}")
        return clean_text

    except httpx.TimeoutException:
        logger.warning(f"⏱️ Timeout scraping {url}")
        return ""
    except httpx.HTTPStatusError as e:
        logger.warning(f"❌ HTTP {e.response.status_code} for {url}")
        return ""
    except Exception as e:
        logger.warning(f"❌ Failed to scrape {url}: {e}")
        return ""


async def scrape_multiple(urls: list[str], max_pages: int = 5) -> dict[str, str]:
    """
    Scrape multiple pages concurrently.
    
    Returns:
        Dict mapping URL → scraped content.
    """
    import asyncio

    urls = urls[:max_pages]
    logger.info(f"🌐 Scraping {len(urls)} pages...")

    tasks = [scrape_page(url) for url in urls]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    scraped = {}
    for url, result in zip(urls, results):
        if isinstance(result, str) and result:
            scraped[url] = result

    logger.info(f"✅ Successfully scraped {len(scraped)}/{len(urls)} pages")
    return scraped
