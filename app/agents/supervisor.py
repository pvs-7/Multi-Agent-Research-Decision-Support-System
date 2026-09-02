from app.graph.state import AgentState
from pydantic import BaseModel, Field
from typing import Literal

MAX_WORKFLOW_STEPS = 8
MAX_RESEARCH_PASSES = 3

class SupervisorDecision(BaseModel):
    next_agent: Literal[
        "research_agent",
        "risk_agent",
        #"fact_checker",
        "report_generator",
        #"human_review"
    ]

    reasoning: str = Field(
        description=(
            "Brief explanation for why this agent "
            "should run next."
        )
    )

supervisor_prompt = """
You are the Supervisor Agent in a dynamic multi-agent
research system.

Your job is to inspect the CURRENT STATE and decide which
agent should work next.

Available agents:

research_agent:
Collects additional factual evidence.

risk_agent:
Analyzes risks, limitations, trade-offs, uncertainties,
and counterarguments using available research.

report_generator:
Creates the final answer.

Decision rules:

Choose research_agent when:
- important information is missing
- needs_more_research is true
- evidence is insufficient
- the current research does not adequately answer the user

Choose risk_agent when:
- research findings exist
- risk analysis is incomplete
- risks, limitations, or counterarguments are important
  for answering the user's question

Choose report_generator when:
- research is sufficient
- risk analysis is complete when relevant
- no important information is missing
- needs_more_research is false

Important rules:

- Analyze the CURRENT STATE, not assumptions.
- Do not repeat work unnecessarily.
- Do not select research_agent unless additional research
  is genuinely needed.
- Do not select risk_agent if risk analysis is already
  sufficient.
- Select exactly one agent.
"""

async def supervisor_agent(state: AgentState):

    workflow_steps = state.get("workflow_steps", 0) + 1
    research_passes = state.get("research_passes", 0)

    print("\n" + "=" * 60)
    print("🧠 SUPERVISOR STARTED")
    print("=" * 60)

    research_complete = state.get(
        "research_complete",
        False
    )

    risk_analysis_complete = state.get(
        "risk_analysis_complete",
        False
    )

    needs_more_research = state.get(
        "needs_more_research",
        False
    )

    research_exhausted = state.get(
        "research_exhausted",
        False
    )

    print(f"Workflow step: {workflow_steps}")
    print(f"Research passes: {research_passes}")
    print(f"Research complete: {research_complete}")
    print(f"Needs more research: {needs_more_research}")
    print(f"Research exhausted: {research_exhausted}")
    print(f"Risk complete: {risk_analysis_complete}")

    # ========================================================
    # WORKFLOW LIMIT
    # ========================================================

    if workflow_steps >= MAX_WORKFLOW_STEPS:

        print("\n🛑 Maximum workflow steps reached.")

        return {
            "next_agent": "report_generator",
            "workflow_steps": workflow_steps,
            "requires_human_review": True,
        }

    # ========================================================
    # RESEARCH
    # ========================================================

    if not research_complete and not research_exhausted:

        if research_passes < MAX_RESEARCH_PASSES:

            print(
                f"\n➡️ Research required."
                f" Pass {research_passes + 1}/"
                f"{MAX_RESEARCH_PASSES}"
            )

            return {
                "next_agent": "research_agent",
                "workflow_steps": workflow_steps,
            }

        # ----------------------------------------------------
        # RESEARCH LIMIT REACHED
        # ----------------------------------------------------

        print(
            "\n🛑 Maximum research passes reached."
        )

        print(
            "➡️ Accepting remaining evidence gaps."
        )

        return {
            "next_agent": "risk_agent",
            "workflow_steps": workflow_steps,
            "research_exhausted": True,
        }

    # ========================================================
    # RISK ANALYSIS
    # ========================================================

    if not risk_analysis_complete:

        print("\n➡️ Risk analysis required.")

        return {
            "next_agent": "risk_agent",
            "workflow_steps": workflow_steps,
        }

    # ========================================================
    # REPORT
    # ========================================================

    print("\n➡️ Research complete.")
    print("➡️ Risk analysis complete.")
    print("➡️ Generating final report.")

    return {
        "next_agent": "report_generator",
        "workflow_steps": workflow_steps,
    }

def route_supervisor(state: AgentState):

    next_agent = state["next_agent"]

    print("\n" + "=" * 60)
    print("🚦 ROUTER")
    print("=" * 60)

    print(f"Supervisor selected: {next_agent}")

    return next_agent