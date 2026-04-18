"""Pydantic models and schemas for the AI Research Agent."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ─── Enums ────────────────────────────────────────────────

class AgentRole(str, Enum):
    ORCHESTRATOR = "orchestrator"
    RESEARCHER = "researcher"
    ANALYST = "analyst"
    FACT_CHECKER = "fact_checker"
    WRITER = "writer"


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class ResearchStatus(str, Enum):
    INITIALIZING = "initializing"
    PLANNING = "planning"
    RESEARCHING = "researching"
    ANALYZING = "analyzing"
    FACT_CHECKING = "fact_checking"
    WRITING = "writing"
    COMPLETED = "completed"
    FAILED = "failed"


# ─── Request / Response Models ────────────────────────────

class ResearchRequest(BaseModel):
    """Incoming research request from the user."""
    topic: str = Field(..., min_length=3, max_length=500, description="The research topic")
    depth: str = Field(default="standard", description="Research depth: quick, standard, deep")
    custom_instructions: Optional[str] = Field(default=None, description="Additional instructions")


class ResearchResponse(BaseModel):
    """Response when a research job is started."""
    research_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    topic: str
    status: ResearchStatus = ResearchStatus.INITIALIZING
    message: str = "Research job started"


# ─── Agent Event Models (for WebSocket) ──────────────────

class AgentEvent(BaseModel):
    """Real-time event emitted by agents during research."""
    research_id: str
    agent: AgentRole
    event_type: str  # "status", "progress", "finding", "error"
    title: str
    content: str
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    metadata: dict = Field(default_factory=dict)


# ─── Research Sub-Task ────────────────────────────────────

class ResearchSubTask(BaseModel):
    """A subtask assigned by the orchestrator to a specific agent."""
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    description: str
    assigned_to: AgentRole
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[str] = None


class ResearchPlan(BaseModel):
    """The orchestrator's plan for the research."""
    topic: str
    objectives: list[str] = Field(default_factory=list)
    subtasks: list[ResearchSubTask] = Field(default_factory=list)
    key_questions: list[str] = Field(default_factory=list)


# ─── Research Findings ────────────────────────────────────

class SearchResult(BaseModel):
    """A single web search result."""
    title: str
    url: str
    snippet: str
    content: Optional[str] = None


class ResearchFinding(BaseModel):
    """A finding from the research process."""
    source: str
    url: Optional[str] = None
    content: str
    relevance_score: float = 0.0
    verified: bool = False


class AnalysisResult(BaseModel):
    """Result from the analyst agent."""
    key_insights: list[str] = Field(default_factory=list)
    statistics: list[str] = Field(default_factory=list)
    patterns: list[str] = Field(default_factory=list)
    summary: str = ""


class FactCheckResult(BaseModel):
    """Result from the fact checker agent."""
    claim: str
    verdict: str  # "verified", "disputed", "unverifiable"
    confidence: float
    evidence: str
    sources: list[str] = Field(default_factory=list)


# ─── Final Report ─────────────────────────────────────────

class ReportSection(BaseModel):
    """A section of the final report."""
    title: str
    content: str
    sources: list[str] = Field(default_factory=list)


class FinalReport(BaseModel):
    """The complete research report."""
    research_id: str
    topic: str
    executive_summary: str = ""
    sections: list[ReportSection] = Field(default_factory=list)
    key_findings: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    generated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    metadata: dict = Field(default_factory=dict)
