"""Research Pipeline — orchestrates all agents in the correct order."""

from __future__ import annotations

import uuid
from typing import Callable

from loguru import logger

from src.agents.analyst import AnalystAgent
from src.agents.fact_checker import FactCheckerAgent
from src.agents.orchestrator import OrchestratorAgent
from src.agents.researcher import ResearcherAgent
from src.agents.writer import WriterAgent
from src.core.memory import ResearchMemory
from src.models.schemas import AgentEvent, AgentRole, FinalReport, ResearchStatus
from src.reports.generator import save_report


class ResearchPipeline:
    """
    The full research pipeline that coordinates all agents:
    
    1. Orchestrator → creates research plan
    2. Researcher → searches web, scrapes, extracts
    3. Orchestrator → synthesizes findings
    4. Analyst → deep analysis
    5. Fact Checker → verifies claims
    6. Writer → produces final report
    """

    def __init__(self, emit_event: Callable):
        self.emit = emit_event
        self.orchestrator = OrchestratorAgent(emit_event)
        self.researcher = ResearcherAgent(emit_event)
        self.analyst = AnalystAgent(emit_event)
        self.fact_checker = FactCheckerAgent(emit_event)
        self.writer = WriterAgent(emit_event)

    async def run(
        self,
        topic: str,
        custom_instructions: str = "",
        research_id: str | None = None,
    ) -> FinalReport:
        """Execute the full research pipeline."""

        research_id = research_id or str(uuid.uuid4())
        memory = ResearchMemory(research_id=research_id, topic=topic)

        logger.info(f"🚀 Starting research pipeline for: '{topic}' (ID: {research_id})")

        try:
            # ── Phase 1: Planning ────────────────────────
            await self._emit_status(research_id, ResearchStatus.PLANNING,
                                    "Phase 1/6: Creating research plan...")

            plan = await self.orchestrator.create_plan(memory, custom_instructions)
            search_queries = []
            # Get search queries from the plan event metadata
            if plan.key_questions:
                search_queries = [f"{topic} {q}" for q in plan.key_questions[:4]]
            # Add the topic itself and some variations
            search_queries = [
                topic,
                f"{topic} latest research",
                f"{topic} statistics data",
            ] + search_queries

            # ── Phase 2: Research ────────────────────────
            await self._emit_status(research_id, ResearchStatus.RESEARCHING,
                                    "Phase 2/6: Searching the web and gathering data...")

            await self.researcher.research(memory, search_queries[:8])

            # ── Phase 3: Synthesis ───────────────────────
            await self._emit_status(research_id, ResearchStatus.ANALYZING,
                                    "Phase 3/6: Synthesizing raw findings...")

            synthesis = await self.orchestrator.synthesize_findings(memory)

            # ── Phase 4: Analysis ────────────────────────
            await self._emit_status(research_id, ResearchStatus.ANALYZING,
                                    "Phase 4/6: Deep analysis of findings...")

            await self.analyst.analyze(memory)

            # ── Phase 5: Fact Checking ───────────────────
            await self._emit_status(research_id, ResearchStatus.FACT_CHECKING,
                                    "Phase 5/6: Verifying claims...")

            claims = synthesis.get("claims_to_verify", [])
            await self.fact_checker.check_facts(memory, claims)

            # ── Phase 6: Report Writing ──────────────────
            await self._emit_status(research_id, ResearchStatus.WRITING,
                                    "Phase 6/6: Writing the final report...")

            report = await self.writer.write_report(memory)

            # ── Save Report ──────────────────────────────
            filepath = save_report(report)

            await self._emit_status(research_id, ResearchStatus.COMPLETED,
                                    f"✅ Research complete! Report saved to: {filepath}")

            await self.emit(AgentEvent(
                research_id=research_id,
                agent=AgentRole.ORCHESTRATOR,
                event_type="complete",
                title="Research Complete",
                content=f"Report generated with {len(report.sections)} sections and {len(report.sources)} sources.",
                metadata={
                    "filepath": filepath,
                    "stats": memory.get_summary_stats(),
                },
            ))

            logger.info(f"✅ Research pipeline complete for: '{topic}'")
            return report

        except Exception as e:
            logger.error(f"❌ Research pipeline failed: {e}")
            await self._emit_status(research_id, ResearchStatus.FAILED,
                                    f"Research failed: {str(e)}")
            raise

    async def _emit_status(self, research_id: str, status: ResearchStatus, message: str):
        """Emit a pipeline-level status update."""
        await self.emit(AgentEvent(
            research_id=research_id,
            agent=AgentRole.ORCHESTRATOR,
            event_type="pipeline_status",
            title=status.value.replace("_", " ").title(),
            content=message,
            metadata={"status": status.value},
        ))
