"""Research memory — stores and retrieves findings during a research session."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from loguru import logger

from src.models.schemas import (
    AnalysisResult,
    FactCheckResult,
    FinalReport,
    ResearchFinding,
    ResearchPlan,
    SearchResult,
)


@dataclass
class ResearchMemory:
    """
    In-memory store for all data collected during a single research session.
    
    Each research job gets its own ResearchMemory instance that accumulates
    findings, analysis results, and fact-checks as agents work.
    """

    research_id: str
    topic: str

    # Research plan from orchestrator
    plan: Optional[ResearchPlan] = None

    # Raw search results
    search_results: list[SearchResult] = field(default_factory=list)

    # Scraped page contents: url → content
    scraped_content: dict[str, str] = field(default_factory=dict)

    # Extracted findings from researcher
    findings: list[ResearchFinding] = field(default_factory=list)

    # Analysis from analyst
    analysis: Optional[AnalysisResult] = None

    # Fact-check results
    fact_checks: list[FactCheckResult] = field(default_factory=list)

    # Final report
    report: Optional[FinalReport] = None

    def add_search_results(self, results: list[SearchResult]) -> None:
        """Add search results to memory."""
        self.search_results.extend(results)
        logger.debug(f"Memory: {len(self.search_results)} total search results")

    def add_scraped_content(self, url: str, content: str) -> None:
        """Add scraped page content to memory."""
        self.scraped_content[url] = content
        logger.debug(f"Memory: {len(self.scraped_content)} scraped pages")

    def add_finding(self, finding: ResearchFinding) -> None:
        """Add a research finding."""
        self.findings.append(finding)
        logger.debug(f"Memory: {len(self.findings)} findings")

    def get_findings_text(self) -> str:
        """Get all findings as a formatted text block for LLM consumption."""
        if not self.findings:
            return "No findings collected yet."

        parts = []
        for i, f in enumerate(self.findings, 1):
            source_info = f"[Source: {f.source}]"
            if f.url:
                source_info += f" ({f.url})"
            parts.append(f"--- Finding {i} {source_info} ---\n{f.content}")

        return "\n\n".join(parts)

    def get_all_sources(self) -> list[str]:
        """Get all unique source URLs."""
        sources = set()
        for sr in self.search_results:
            if sr.url:
                sources.add(sr.url)
        for f in self.findings:
            if f.url:
                sources.add(f.url)
        return sorted(sources)

    def get_summary_stats(self) -> dict:
        """Get summary statistics about the research."""
        return {
            "search_results": len(self.search_results),
            "pages_scraped": len(self.scraped_content),
            "findings": len(self.findings),
            "fact_checks": len(self.fact_checks),
            "has_analysis": self.analysis is not None,
            "has_report": self.report is not None,
        }
