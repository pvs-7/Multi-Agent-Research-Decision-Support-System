from app.graph.state import AgentState
from pydantic import BaseModel
from typing import Literal

from langchain_core.messages import HumanMessage, SystemMessage
from app.core.llm import llm

class SupervisorDecision(BaseModel):
    next_agent: Literal[
        "research_agent",
        #"risk_agent",
        #"fact_checker",
        "report_generator",
        #"human_review"
    ]

final_supervisor_prompt = """
You are the Supervisor Agent in a multi-agent research system.

Your job is to analyze the current state of the research and decide which agent should work next.

Available agents:

research_agent: Finds information and evidence needed to answer the user's question.
risk_agent: Identifies risks, limitations, and counterarguments.
fact_checker: Verifies important claims and detects conflicting or unsupported information.
report_generator: Creates the final response when the research is complete.

Rules:

Choose research_agent when more information is needed.
Choose risk_agent when risks or counterarguments need to be investigated.
Choose fact_checker when findings need verification.
Choose report_generator only when the research is complete and important claims have been checked.
Choose human_review when an important conflict cannot be resolved automatically.
Do not perform research yourself.
Do not repeat unnecessary work.
If information is missing or unreliable, route to the appropriate agent.

Analyze the current state and select the next step.
"""

supervisor_prompt = """
You are the Supervisor Agent in a multi-agent research system.

Your job is to analyze the current state of the research and decide which
agent should work next.

Available agents:

research_agent:
Finds information and evidence needed to answer the user's question.

report_generator:
Creates the final response when the research is complete.

Rules:

- Choose research_agent when more information is needed.
- Choose report_generator when the available research is sufficient to answer
  the user's question.
- Do not choose agents that are not listed as available.
- Do not perform research yourself.
- Do not repeat unnecessary work.
- Analyze the current state and select the next step.
"""

def supervisor_agent(state: AgentState):

    print("\n" + "=" * 60)
    print("🧠 SUPERVISOR STARTED")
    print("=" * 60)

    print("User query:")
    print(state["user_query"])

    print("\nResearch findings:")
    print(state.get("research_findings", []))

    print("\nRisks:")
    print(state.get("risks", []))

    print("\nVerifications:")
    print(state.get("verifications", []))

    print("\nHuman review:")
    print(state.get("requires_human_review", False))

    if state.get("requires_human_review"):
        print("⚠️ Routing to HUMAN REVIEW")

        return {
            "next_agent": "human_review"
        }

    structured_llm = llm.with_structured_output(
        SupervisorDecision
    )

    context = f"""
User Query:
{state["user_query"]}

Research Findings:
{state.get("research_findings", [])}

Risks Identified:
{state.get("risks", [])}

Fact Check Results:
{state.get("verifications", [])}

Human Review Required:
{state.get("requires_human_review", False)}
"""

    print("\n📤 Sending state to supervisor LLM...")

    decision = structured_llm.invoke([
        SystemMessage(content=supervisor_prompt),
        HumanMessage(content=context)
    ])

    print("\n📥 Supervisor decision:")
    print(decision)

    print(f"\n➡️ NEXT AGENT: {decision.next_agent}")

    return {
        "next_agent": decision.next_agent
    }

def route_supervisor(state: AgentState):

    next_agent = state["next_agent"]

    print("\n" + "=" * 60)
    print("🚦 ROUTER")
    print("=" * 60)

    print(f"Supervisor selected: {next_agent}")

    return next_agent