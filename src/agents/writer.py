"""Writer Agent — produces the final structured research report."""

from __future__ import annotations

import json
from typing import Callable

from langchain_core.messages import HumanMessage
from loguru import logger

from src.core.llm import get_llm
from src.core.memory import ResearchMemory
from src.core.prompts import WRITER_PROMPT
from src.models.schemas import (
    AgentEvent, AgentRole, FinalReport, ReportSection,
)


class WriterAgent:
    def __init__(self, emit_event: Callable):
        self.llm = get_llm(temperature=0.4, max_tokens=8000)
        self.emit = emit_event

    async def write_report(self, memory: ResearchMemory) -> FinalReport:
        await self.emit(AgentEvent(
            research_id=memory.research_id, agent=AgentRole.WRITER,
            event_type="status", title="Writing Report",
            content="✍️ Composing comprehensive research report...",
        ))

        # Prepare context for the writer
        plan_text = ""
        if memory.plan:
            plan_text = f"Objectives: {', '.join(memory.plan.objectives)}\nQuestions: {', '.join(memory.plan.key_questions)}"

        analysis_text = ""
        if memory.analysis:
            analysis_text = (
                f"Insights: {json.dumps(memory.analysis.key_insights)}\n"
                f"Statistics: {json.dumps(memory.analysis.statistics)}\n"
                f"Patterns: {json.dumps(memory.analysis.patterns)}\n"
                f"Summary: {memory.analysis.summary}"
            )

        fc_text = ""
        if memory.fact_checks:
            fc_items = [f"- {fc.claim}: {fc.verdict} ({fc.confidence:.0%})" for fc in memory.fact_checks]
            fc_text = "\n".join(fc_items)

        findings_text = memory.get_findings_text()
        if len(findings_text) > 10000:
            findings_text = findings_text[:10000] + "\n[... truncated ...]"

        sources = memory.get_all_sources()
        sources_text = "\n".join(f"- {s}" for s in sources[:20])

        prompt = WRITER_PROMPT.format(
            topic=memory.topic,
            plan=plan_text or "No formal plan.",
            analysis=analysis_text or "No analysis available.",
            fact_checks=fc_text or "No fact checks performed.",
            findings=findings_text,
            sources=sources_text or "No sources.",
        )

        try:
            response = await self.llm.ainvoke([HumanMessage(content=prompt)])
            result = self._parse_json(response.content)

            sections = []
            for s in result.get("sections", []):
                sections.append(ReportSection(
                    title=s.get("title", "Untitled"),
                    content=s.get("content", ""),
                    sources=[],
                ))

            report = FinalReport(
                research_id=memory.research_id,
                topic=memory.topic,
                executive_summary=result.get("executive_summary", ""),
                sections=sections,
                key_findings=result.get("key_findings_list", []),
                sources=sources,
            )

            memory.report = report

            await self.emit(AgentEvent(
                research_id=memory.research_id, agent=AgentRole.WRITER,
                event_type="progress", title="Report Complete",
                content=f"📄 Report generated with {len(sections)} sections and {len(sources)} sources",
            ))

            return report

        except Exception as e:
            logger.error(f"Report writing failed: {e}")
            await self.emit(AgentEvent(
                research_id=memory.research_id, agent=AgentRole.WRITER,
                event_type="error", title="Writing Error", content=str(e),
            ))
            return FinalReport(
                research_id=memory.research_id, topic=memory.topic,
                executive_summary="Report generation encountered an error.",
            )

    def _parse_json(self, text: str) -> dict:
        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        if text.startswith("json"):
            text = text[4:].strip()
        try:
            return json.loads(text, strict=False)
        except json.JSONDecodeError:
            start = text.find("{")
            end = text.rfind("}") + 1
            if start != -1 and end > start:
                return json.loads(text[start:end], strict=False)
            raise
