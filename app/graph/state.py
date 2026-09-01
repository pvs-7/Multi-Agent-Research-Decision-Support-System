from typing import Annotated, Literal
from typing_extensions import TypedDict
from pydantic import BaseModel, Field
from langgraph.graph.message import add_messages

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

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    user_query: str

    research_findings: list[Finding]
    risks: list[Risk]
    verifications: list[Verification]

    next_agent: str | None

    requires_human_review: bool
    human_decision: str | None
    human_feedback: str | None

    confidence_score: float | None
    final_report: str | None