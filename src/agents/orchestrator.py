"""Orchestrator Agent — the brain that plans research and coordinates other agents."""

from __future__ import annotations

import json
from typing import Callable

from langchain_core.messages import HumanMessage
from loguru import logger

from src.core.llm import get_llm
from src.core.memory import ResearchMemory
from src.core.prompts import ORCHESTRATOR_PLAN_PROMPT, ORCHESTRATOR_SYNTHESIZE_PROMPT
from src.models.schemas import AgentEvent, AgentRole, ResearchPlan


class OrchestratorAgent:
    """
    The Orchestrator breaks down a research topic into a structured plan,
    then coordinates the other agents to execute it.
    """

    def __init__(self, emit_event: Callable):
        self.llm = get_llm(temperature=0.2)
        self.emit = emit_event

    async def create_plan(self, memory: ResearchMemory, custom_instructions: str = "") -> ResearchPlan:
        """Create a research plan from the topic."""
        await self.emit(AgentEvent(
            research_id=memory.research_id,
            agent=AgentRole.ORCHESTRATOR,
            event_type="status",
            title="Creating Research Plan",
            content=f"Analyzing topic: '{memory.topic}' and breaking it into subtasks...",
        ))

        instructions = ""
        if custom_instructions:
            instructions = f"\nADDITIONAL INSTRUCTIONS: {custom_instructions}"

        prompt = ORCHESTRATOR_PLAN_PROMPT.format(
            topic=memory.topic,
            custom_instructions=instructions,
        )

        try:
            response = await self.llm.ainvoke([HumanMessage(content=prompt)])
            result = self._parse_json(response.content)

            plan = ResearchPlan(
                topic=memory.topic,
                objectives=result.get("objectives", []),
                key_questions=result.get("key_questions", []),
            )

            # Store search queries in plan metadata for the researcher
            plan_data = {
                "search_queries": result.get("search_queries", []),
            }

            memory.plan = plan

            await self.emit(AgentEvent(
                research_id=memory.research_id,
                agent=AgentRole.ORCHESTRATOR,
                event_type="progress",
                title="Research Plan Created",
                content=(
                    f"📋 {len(plan.objectives)} objectives defined\n"
                    f"❓ {len(plan.key_questions)} key questions identified\n"
                    f"🔍 {len(plan_data['search_queries'])} search queries planned"
                ),
                metadata=plan_data,
            ))

            logger.info(f"Research plan created with {len(plan.objectives)} objectives")
            return plan

        except Exception as e:
            logger.error(f"Failed to create research plan: {e}")
            await self.emit(AgentEvent(
                research_id=memory.research_id,
                agent=AgentRole.ORCHESTRATOR,
                event_type="error",
                title="Planning Failed",
                content=f"Error creating research plan: {str(e)}",
            ))
            # Return a basic plan as fallback
            return ResearchPlan(
                topic=memory.topic,
                objectives=[f"Research {memory.topic} comprehensively"],
                key_questions=[f"What is {memory.topic}?", f"Why is {memory.topic} important?"],
            )

    async def synthesize_findings(self, memory: ResearchMemory) -> dict:
        """Review all raw findings and synthesize key takeaways."""
        await self.emit(AgentEvent(
            research_id=memory.research_id,
            agent=AgentRole.ORCHESTRATOR,
            event_type="status",
            title="Synthesizing Findings",
            content="Reviewing all research findings and identifying key takeaways...",
        ))

        objectives_text = "\n".join(f"- {obj}" for obj in (memory.plan.objectives if memory.plan else []))
        findings_text = memory.get_findings_text()

        # Truncate if too long for context window
        if len(findings_text) > 15000:
            findings_text = findings_text[:15000] + "\n\n[... additional findings truncated ...]"

        prompt = ORCHESTRATOR_SYNTHESIZE_PROMPT.format(
            topic=memory.topic,
            objectives=objectives_text,
            findings=findings_text,
        )

        try:
            response = await self.llm.ainvoke([HumanMessage(content=prompt)])
            result = self._parse_json(response.content)

            await self.emit(AgentEvent(
                research_id=memory.research_id,
                agent=AgentRole.ORCHESTRATOR,
                event_type="progress",
                title="Synthesis Complete",
                content=(
                    f"🔑 {len(result.get('key_findings', []))} key findings identified\n"
                    f"✅ {len(result.get('claims_to_verify', []))} claims to fact-check\n"
                    f"📊 Coverage: {result.get('coverage_assessment', 'N/A')}"
                ),
            ))

            return result

        except Exception as e:
            logger.error(f"Synthesis failed: {e}")
            return {
                "key_findings": [],
                "claims_to_verify": [],
                "coverage_assessment": "Unable to synthesize — using raw findings.",
            }

    def _parse_json(self, text: str) -> dict:
        """Parse JSON from LLM response, handling common formatting issues."""
        # Strip markdown code blocks if present
        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        # Remove 'json' language identifier
        if text.startswith("json"):
            text = text[4:].strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Try to find JSON object in the text
            start = text.find("{")
            end = text.rfind("}") + 1
            if start != -1 and end > start:
                return json.loads(text[start:end])
            raise
