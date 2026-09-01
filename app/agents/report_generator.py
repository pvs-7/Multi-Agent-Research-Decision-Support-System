from app.graph.state import AgentState
from langchain_core.messages import HumanMessage, SystemMessage
from app.core.llm import llm

report_generator_prompt = """
You are the Report Generator Agent in a multi-agent research system.

Your job is to create a clear, accurate, and well-structured final report based ONLY on the provided research findings, risks, and verification results.

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

def report_generator(state: AgentState):

    print("\n" + "=" * 60)
    print("📝 REPORT GENERATOR STARTED")
    print("=" * 60)

    print("\nUser query:")
    print(state["user_query"])

    print("\nResearch findings:")
    for finding in state.get("research_findings", []):
        print(f"  - {finding}")

    print("\nRisks:")
    print(state.get("risks", []))

    print("\nVerifications:")
    print(state.get("verifications", []))

    verified_claims = [
        verification
        for verification in state.get("verifications", [])
        if verification["status"] == "verified"
    ]

    print("\n✅ Verified claims:")
    print(verified_claims)

    conflicting_claims = [
        verification
        for verification in state.get("verifications", [])
        if verification["status"] != "verified"
    ]

    print("\n⚠️ Conflicting/unverified claims:")
    print(conflicting_claims)

    context = f"""
User Query:
{state["user_query"]}

Research Findings:
{state.get("research_findings", [])}

Risks:
{state.get("risks", [])}

Verified Claims:
{verified_claims}

Conflicting or Unverified Claims:
{conflicting_claims}
"""

    print("\n📤 Sending information to report LLM...")

    response = llm.invoke([
        SystemMessage(content=report_generator_prompt),
        HumanMessage(content=context)
    ])

    print("\n📥 GENERATED REPORT:")
    print("-" * 60)
    print(response.content)
    print("-" * 60)

    print("\n✅ REPORT GENERATOR FINISHED")

    return {
        "final_report": response.content
    }