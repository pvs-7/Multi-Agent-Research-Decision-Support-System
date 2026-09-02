import json

from pydantic import BaseModel

from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage
)

from app.core.llm import llm
from app.graph.state import AgentState, Risk

class RiskOutput(BaseModel):
    risks: list[Risk]
    needs_more_research: bool = False
    missing_information: list[str] = []

risk_prompt = """
You are the Risk Agent in a multi-agent research system.

Your job is to analyze the research findings and identify
important risks, limitations, trade-offs, uncertainties,
and potential negative consequences.

Rules:

- Only identify risks supported by the provided research findings.
- Do not invent information.
- Do not perform additional research.
- Do not create risks without evidence.
- Avoid duplicate risks.
- Focus on risks relevant to the user's question.

If the available research does not contain enough evidence
to analyze important risks, identify the missing information.

For every risk provide:

description:
A clear explanation of the risk.

severity:
One of:
- low
- medium
- high

evidence:
Evidence supporting the risk.

source_url:
The URL of the source supporting the risk.

confidence:
A number between 0 and 1.

Also determine:

needs_more_research:
True if important risk areas cannot be analyzed with the
available research.

missing_information:
A list of important information or evidence gaps.
"""

async def risk_agent(state: AgentState):

    workflow_steps = state.get("workflow_steps", 0) + 1

    print("\n" + "=" * 60)
    print("⚠️ RISK AGENT STARTED")
    print("=" * 60)

    print("\nUser query:")
    print(state["user_query"])

    print("\nResearch findings:")
    print(state["research_findings"])

    # ----------------------------------------------
    # Convert findings to JSON-safe dictionaries
    # ----------------------------------------------

    findings = [finding.model_dump()
                for finding in state.get("research_findings", [])
    ]

    context = {
        "user_query": state["user_query"],
        "research_findings": findings
    }

    # ----------------------------------------------
    # Structured LLM
    # ----------------------------------------------

    structured_llm = llm.with_structured_output(RiskOutput)

    print("\n📤 Sending research findings to Risk Agent...")

    risk_output = await structured_llm.ainvoke(
        [
            SystemMessage(content=risk_prompt),
            HumanMessage(content=json.dumps(context))
        ]
    )

    # ----------------------------------------------
    # Debug output
    # ----------------------------------------------

    print("\n📥 RISKS IDENTIFIED:")

    for risk in risk_output.risks:

        print("\nDescription:")
        print(risk.description)

        print("Severity:")
        print(risk.severity)

        print("Evidence:")
        print(risk.evidence)

        print("Source:")
        print(risk.source_url)

        print("Confidence:")
        print(risk.confidence)

    print("\n⚠️ RISK AGENT FINISHED")

    # ----------------------------------------------
    # Return state update
    # ----------------------------------------------

    return {
        "risks": risk_output.risks,
        "risk_analysis_complete": True,
        "needs_more_research": risk_output.needs_more_research,
        "missing_information": risk_output.missing_information,
        "completed_agents": ["risk_agent"],
        "workflow_steps": workflow_steps,
        "messages": [
            AIMessage(
                content=(
                    f"Risk Agent completed risk analysis and "
                    f"found {len(risk_output.risks)} risks."
                ),
                name="risk_agent"
            )
        ]
    }

    