"""Web search tool using DuckDuckGo (free, no API key needed)."""

from __future__ import annotations

from duckduckgo_search import DDGS
from loguru import logger

from src.core.config import settings
from src.models.schemas import SearchResult


async def search_web(query: str, max_results: int | None = None) -> list[SearchResult]:
    """
    Search the web using DuckDuckGo.
    
    Args:
        query: The search query.
        max_results: Maximum number of results to return.
    
    Returns:
        A list of SearchResult objects.
    """
    if max_results is None:
        max_results = settings.MAX_SEARCH_RESULTS

    logger.info(f"🔍 Searching: '{query}' (max {max_results} results)")

    try:
        results = []
        with DDGS() as ddgs:
            search_results = ddgs.text(query, max_results=max_results, backend="html")
            for r in search_results:
                results.append(SearchResult(
                    title=r.get("title", ""),
                    url=r.get("href", r.get("link", "")),
                    snippet=r.get("body", r.get("snippet", "")),
                ))

        logger.info(f"✅ Found {len(results)} results for '{query}'")
        return results

    except Exception as e:
        logger.error(f"❌ Search failed for '{query}': {e}")
        return []


async def search_news(query: str, max_results: int = 5) -> list[SearchResult]:
    """Search for recent news articles on a topic."""
    logger.info(f"📰 Searching news: '{query}'")

    try:
        results = []
        with DDGS() as ddgs:
            news_results = ddgs.news(query, max_results=max_results)
            for r in news_results:
                results.append(SearchResult(
                    title=r.get("title", ""),
                    url=r.get("url", r.get("link", "")),
                    snippet=r.get("body", r.get("snippet", "")),
                ))

        logger.info(f"✅ Found {len(results)} news results")
        return results

    except Exception as e:
        logger.error(f"❌ News search failed: {e}")
        return []
