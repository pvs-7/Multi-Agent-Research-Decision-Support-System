from typing import Annotated, Literal
from typing_extensions import TypedDict
from pydantic import BaseModel, Field
from langgraph.graph.message import add_messages
from operator import add

class Finding(BaseModel):
    claim: str
    evidence: str
    source_url: str
    confidence: float = Field(ge=0, le=1)

class Risk(BaseModel):
    description: str
    severity: Literal["low", "medium", "high"]
    evidence: str
    source_url: str
    confidence: float = Field(ge=0, le=1)

class Verification(BaseModel):
    claim: str
    status: Literal[
        "verified",
        "unverified",
        "conflicting"
    ]

    confidence: float = Field(ge=0, le=1)
    notes: str
    source_url: list[str] = []

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    user_query: str

    research_findings: list[Finding]
    risks: list[Risk]
    verifications: list[Verification]

    research_sources: list[dict]
    research_queries: list[str]
    research_passes: int
    research_exhausted: bool

    completed_agents: Annotated[list[str], add]
    next_agent: str | None

    workflow_steps: int

    research_complete: bool
    risk_analysis_complete: bool
    needs_more_research: bool
    missing_information: list[str]

    fact_check_complete: bool
    research_requests: list[str]

    input_guardrail_allowed: bool
    input_guardrail_category: str
    input_guardrail_reason: str

    requires_human_review: bool
    human_review_items: list[dict]
    human_decision: str | None
    human_feedback: str | None

    confidence_score: float | None
    final_report: str | None