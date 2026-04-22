"""Researcher Agent — searches the web and extracts relevant information."""

from __future__ import annotations

import asyncio
from typing import Callable

from langchain_core.messages import HumanMessage
from loguru import logger

from src.core.llm import get_llm
from src.core.memory import ResearchMemory
from src.core.prompts import RESEARCHER_EXTRACT_PROMPT
from src.models.schemas import AgentEvent, AgentRole, ResearchFinding
from src.tools.scraper import scrape_page
from src.tools.web_search import search_news, search_web


class ResearcherAgent:
    """
    The Researcher searches the web, scrapes pages, and extracts
    relevant information for the research topic.
    """

    def __init__(self, emit_event: Callable):
        self.llm = get_llm(temperature=0.1)
        self.emit = emit_event

    async def research(self, memory: ResearchMemory, search_queries: list[str]) -> None:
        """Execute the full research process: search → scrape → extract."""

        await self.emit(AgentEvent(
            research_id=memory.research_id,
            agent=AgentRole.RESEARCHER,
            event_type="status",
            title="Starting Research",
            content=f"Executing {len(search_queries)} search queries...",
        ))

        # ── Step 1: Web Search ────────────────────────────
        all_results = []
        for i, query in enumerate(search_queries):
            await self.emit(AgentEvent(
                research_id=memory.research_id,
                agent=AgentRole.RESEARCHER,
                event_type="progress",
                title=f"Searching ({i+1}/{len(search_queries)})",
                content=f"🔍 Query: \"{query}\"",
            ))

            results = await search_web(query, max_results=5)
            all_results.extend(results)
            memory.add_search_results(results)

            # Small delay to avoid rate limiting
            await asyncio.sleep(1.0)

        # Also search for recent news
        news_results = await search_news(memory.topic, max_results=5)
        all_results.extend(news_results)
        memory.add_search_results(news_results)

        await self.emit(AgentEvent(
            research_id=memory.research_id,
            agent=AgentRole.RESEARCHER,
            event_type="progress",
            title="Search Complete",
            content=f"📊 Found {len(all_results)} total results across all queries",
        ))

        # ── Step 2: Deduplicate URLs & Select Best ────────
        seen_urls = set()
        unique_results = []
        for r in all_results:
            if r.url and r.url not in seen_urls:
                seen_urls.add(r.url)
                unique_results.append(r)

        # Limit pages to scrape
        pages_to_scrape = unique_results[:8]

        # ── Step 3: Scrape Pages ──────────────────────────
        await self.emit(AgentEvent(
            research_id=memory.research_id,
            agent=AgentRole.RESEARCHER,
            event_type="status",
            title="Scraping Pages",
            content=f"📄 Scraping {len(pages_to_scrape)} web pages for content...",
        ))

        scrape_tasks = []
        for result in pages_to_scrape:
            scrape_tasks.append(self._scrape_and_store(result.url, memory))

        await asyncio.gather(*scrape_tasks, return_exceptions=True)

        await self.emit(AgentEvent(
            research_id=memory.research_id,
            agent=AgentRole.RESEARCHER,
            event_type="progress",
            title="Scraping Complete",
            content=f"✅ Successfully scraped {len(memory.scraped_content)} pages",
        ))

        # ── Step 4: Extract Information with LLM ─────────
        await self.emit(AgentEvent(
            research_id=memory.research_id,
            agent=AgentRole.RESEARCHER,
            event_type="status",
            title="Extracting Information",
            content="🧠 Using AI to extract relevant information from scraped content...",
        ))

        extraction_count = 0
        for url, content in memory.scraped_content.items():
            if not content or len(content) < 100:
                continue

            finding = await self._extract_information(memory.topic, url, content)
            if finding:
                memory.add_finding(finding)
                extraction_count += 1

                await self.emit(AgentEvent(
                    research_id=memory.research_id,
                    agent=AgentRole.RESEARCHER,
                    event_type="finding",
                    title=f"Finding from {self._short_url(url)}",
                    content=finding.content[:300] + "..." if len(finding.content) > 300 else finding.content,
                ))

        await self.emit(AgentEvent(
            research_id=memory.research_id,
            agent=AgentRole.RESEARCHER,
            event_type="progress",
            title="Research Phase Complete",
            content=f"🎯 Extracted {extraction_count} relevant findings from {len(memory.scraped_content)} pages",
        ))

    async def _scrape_and_store(self, url: str, memory: ResearchMemory) -> None:
        """Scrape a page and store in memory."""
        try:
            content = await scrape_page(url)
            if content:
                memory.add_scraped_content(url, content)
        except Exception as e:
            logger.warning(f"Failed to scrape {url}: {e}")

    async def _extract_information(self, topic: str, url: str, content: str) -> ResearchFinding | None:
        """Use LLM to extract relevant information from page content."""
        # Truncate content for LLM context
        if len(content) > 6000:
            content = content[:6000] + "\n[... content truncated ...]"

        prompt = RESEARCHER_EXTRACT_PROMPT.format(
            topic=topic,
            url=url,
            content=content,
        )

        try:
            response = await self.llm.ainvoke([HumanMessage(content=prompt)])
            extracted = response.content.strip()

            if "NOT RELEVANT" in extracted.upper():
                return None

            return ResearchFinding(
                source=self._short_url(url),
                url=url,
                content=extracted,
                relevance_score=0.8,
            )

        except Exception as e:
            logger.warning(f"Extraction failed for {url}: {e}")
            return None

    @staticmethod
    def _short_url(url: str) -> str:
        """Get a short display version of a URL."""
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return parsed.netloc or url[:50]
