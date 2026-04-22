"""Analyst Agent — analyzes research findings to extract insights and patterns."""

from __future__ import annotations

import json
from typing import Callable

from langchain_core.messages import HumanMessage
from loguru import logger

from src.core.llm import get_llm
from src.core.memory import ResearchMemory
from src.core.prompts import ANALYST_PROMPT
from src.models.schemas import AgentEvent, AgentRole, AnalysisResult


class AnalystAgent:
    """
    The Analyst takes raw research findings and performs deep analysis:
    extracting insights, statistics, patterns, and identifying gaps.
    """

    def __init__(self, emit_event: Callable):
        self.llm = get_llm(temperature=0.2)
        self.emit = emit_event

    async def analyze(self, memory: ResearchMemory) -> AnalysisResult:
        """Analyze all research findings and produce structured insights."""

        await self.emit(AgentEvent(
            research_id=memory.research_id,
            agent=AgentRole.ANALYST,
            event_type="status",
            title="Starting Analysis",
            content=f"📊 Analyzing {len(memory.findings)} research findings...",
        ))

        findings_text = memory.get_findings_text()

        # Truncate if too long
        if len(findings_text) > 12000:
            findings_text = findings_text[:12000] + "\n\n[... additional findings truncated ...]"

        prompt = ANALYST_PROMPT.format(
            topic=memory.topic,
            findings=findings_text,
        )

        try:
            response = await self.llm.ainvoke([HumanMessage(content=prompt)])
            result = self._parse_json(response.content)

            analysis = AnalysisResult(
                key_insights=result.get("key_insights", []),
                statistics=result.get("statistics", []),
                patterns=result.get("patterns", []),
                summary=result.get("summary", ""),
            )

            memory.analysis = analysis

            await self.emit(AgentEvent(
                research_id=memory.research_id,
                agent=AgentRole.ANALYST,
                event_type="progress",
                title="Analysis Complete",
                content=(
                    f"🔑 {len(analysis.key_insights)} key insights found\n"
                    f"📈 {len(analysis.statistics)} statistics extracted\n"
                    f"🔄 {len(analysis.patterns)} patterns identified"
                ),
            ))

            # Emit individual insights
            for insight in analysis.key_insights[:5]:
                await self.emit(AgentEvent(
                    research_id=memory.research_id,
                    agent=AgentRole.ANALYST,
                    event_type="finding",
                    title="Key Insight",
                    content=insight,
                ))

            logger.info(f"Analysis complete: {len(analysis.key_insights)} insights")
            return analysis

        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            await self.emit(AgentEvent(
                research_id=memory.research_id,
                agent=AgentRole.ANALYST,
                event_type="error",
                title="Analysis Error",
                content=f"Analysis encountered an error: {str(e)}",
            ))
            return AnalysisResult(summary="Analysis could not be completed.")

    def _parse_json(self, text: str) -> dict:
        """Parse JSON from LLM response."""
        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        if text.startswith("json"):
            text = text[4:].strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            start = text.find("{")
            end = text.rfind("}") + 1
            if start != -1 and end > start:
                return json.loads(text[start:end])
            raise
