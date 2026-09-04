import json

from app.graph.state import AgentState
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from app.core.llm import llm


report_generator_prompt = """
You are the Report Generator Agent in a multi-agent research system.

Your job is to create a clear, accurate, and well-structured
final report based ONLY on the provided research findings,
risks, and verification results.

Rules:
- Do not invent information.
- Do not include claims that are marked as unverified.
- Clearly mention conflicting information when relevant.
- Present risks and limitations objectively.
- Base your conclusions only on the provided information.

Structure your report as follows:

# Overview
Briefly answer the user's query.

# Key Findings
Summarize the most important verified findings.

# Risks and Limitations
Describe the identified risks and counterarguments.

# Verification Status
Summarize any conflicting or uncertain information.

# Conclusion
Provide a balanced conclusion based on the available evidence.
"""


async def report_generator(state: AgentState):

    print("\n" + "=" * 60)
    print("📝 REPORT GENERATOR STARTED")
    print("=" * 60)

    print("\nUser query:")
    print(state["user_query"])

    # --------------------------------------------------
    # Get state data
    # --------------------------------------------------

    findings = state.get("research_findings", [])
    risks = state.get("risks", [])
    verifications = state.get("verifications", [])

    # --------------------------------------------------
    # Filter verification results
    # --------------------------------------------------

    verified_claims = [
        verification
        for verification in verifications
        if verification.status == "verified"
    ]

    conflicting_claims = [
        verification
        for verification in verifications
        if verification.status != "verified"
    ]

    print("\n✅ Verified claims:")
    for verification in verified_claims:
        print(verification)

    print("\n⚠️ Conflicting/unverified claims:")
    for verification in conflicting_claims:
        print(verification)

    # --------------------------------------------------
    # Convert Pydantic models to dictionaries
    # --------------------------------------------------

    context = {
        "user_query": state["user_query"],

        "research_findings": [
            finding.model_dump()
            for finding in findings
        ],

        "risks": [
            risk.model_dump()
            for risk in risks
        ],

        "verified_claims": [
            verification.model_dump()
            for verification in verified_claims
        ],

        "conflicting_or_unverified_claims": [
            verification.model_dump()
            for verification in conflicting_claims
        ],

        "needs_more_research": state.get(
            "needs_more_research",
            False
        ),

        "missing_information": state.get(
            "missing_information",
            []
        )
    }

    print("\n📤 Sending information to report LLM...")

    response = await llm.ainvoke([
        SystemMessage(content=report_generator_prompt),

        HumanMessage(
            content=json.dumps(
                context,
                indent=2
            )
        )
    ])

    print("\n📥 GENERATED REPORT:")
    print("-" * 60)
    print(response.content)
    print("-" * 60)

    print("\n✅ REPORT GENERATOR FINISHED")

    return {
    "final_report": response.content,

    "messages": [
        AIMessage(
            content=(
                "📝 Report Generator completed. "
                "Final report is ready."
            ),
            name="report_generator"
        )
    ]
}