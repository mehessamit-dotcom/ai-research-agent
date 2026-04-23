"""Fact Checker Agent — verifies claims using evidence from research."""

from __future__ import annotations

import json
from typing import Callable

from langchain_core.messages import HumanMessage
from loguru import logger

from src.core.llm import get_llm
from src.core.memory import ResearchMemory
from src.core.prompts import FACT_CHECKER_PROMPT
from src.models.schemas import AgentEvent, AgentRole, FactCheckResult


class FactCheckerAgent:
    def __init__(self, emit_event: Callable):
        self.llm = get_llm(temperature=0.1)
        self.emit = emit_event

    async def check_facts(self, memory: ResearchMemory, claims: list[str]) -> list[FactCheckResult]:
        if not claims:
            await self.emit(AgentEvent(
                research_id=memory.research_id, agent=AgentRole.FACT_CHECKER,
                event_type="progress", title="Fact Check Skipped",
                content="No specific claims to verify.",
            ))
            return []

        await self.emit(AgentEvent(
            research_id=memory.research_id, agent=AgentRole.FACT_CHECKER,
            event_type="status", title="Starting Fact Check",
            content=f"✅ Verifying {len(claims)} claims against evidence...",
        ))

        claims_text = "\n".join(f"{i+1}. {c}" for i, c in enumerate(claims))
        evidence_text = memory.get_findings_text()
        if len(evidence_text) > 10000:
            evidence_text = evidence_text[:10000] + "\n[... truncated ...]"

        prompt = FACT_CHECKER_PROMPT.format(claims=claims_text, evidence=evidence_text)

        try:
            response = await self.llm.ainvoke([HumanMessage(content=prompt)])
            result = self._parse_json(response.content)
            fact_checks = []

            for fc in result.get("fact_checks", []):
                fact_check = FactCheckResult(
                    claim=fc.get("claim", ""),
                    verdict=fc.get("verdict", "unverifiable"),
                    confidence=fc.get("confidence", 0.5),
                    evidence=fc.get("reasoning", "") + "\n" + fc.get("supporting_evidence", ""),
                    sources=[],
                )
                fact_checks.append(fact_check)
                memory.fact_checks.append(fact_check)

                emoji = {"verified": "✅", "partially_verified": "⚠️", "disputed": "❌"}.get(fact_check.verdict, "❓")
                await self.emit(AgentEvent(
                    research_id=memory.research_id, agent=AgentRole.FACT_CHECKER,
                    event_type="finding",
                    title=f"{emoji} {fact_check.verdict.replace('_', ' ').title()}",
                    content=f"**Claim:** {fact_check.claim}\n**Confidence:** {fact_check.confidence:.0%}",
                ))

            verified = sum(1 for r in fact_checks if r.verdict == "verified")
            disputed = sum(1 for r in fact_checks if r.verdict == "disputed")
            await self.emit(AgentEvent(
                research_id=memory.research_id, agent=AgentRole.FACT_CHECKER,
                event_type="progress", title="Fact Check Complete",
                content=f"✅ Verified: {verified} | ❌ Disputed: {disputed} | Total: {len(fact_checks)}",
            ))
            return fact_checks

        except Exception as e:
            logger.error(f"Fact checking failed: {e}")
            await self.emit(AgentEvent(
                research_id=memory.research_id, agent=AgentRole.FACT_CHECKER,
                event_type="error", title="Fact Check Error", content=str(e),
            ))
            return []

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
            return json.loads(text)
        except json.JSONDecodeError:
            start = text.find("{")
            end = text.rfind("}") + 1
            if start != -1 and end > start:
                return json.loads(text[start:end])
            raise
