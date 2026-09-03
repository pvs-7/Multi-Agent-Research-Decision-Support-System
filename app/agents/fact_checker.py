import json

from pydantic import BaseModel

from app.graph.state import Verification, AgentState
from app.core.llm import llm2

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

class FactCheckOutput(BaseModel):
    verifications: list[Verification]
    fact_check_complete: bool
    needs_more_research: bool
    missing_information: list[str]

def select_findings_for_fact_check(findings, limit=8):
    return [
        {
            "claim": f.claim,
            "evidence": f.evidence,
            "source_url": f.source_url,
            "confidence": f.confidence
        }
        for f in findings[:limit]
    ]

def compact_findings_for_fact_check(findings, limit=8):
    return [
        {
            "claim": f.claim[:500],
            "evidence": f.evidence[:700],
            "source_url": f.source_url,
            "confidence": f.confidence
        }
        for f in findings[:limit]
    ]

def compact_risks_for_fact_check(risks, limit=8):
    return [
        {
            "description": r.description[:500],
            "severity": r.severity,
            "evidence": r.evidence[:700],
            "source_url": r.source_url,
            "confidence": r.confidence
        }
        for r in risks[:limit]
    ]

def build_human_review_package(verifications, research_sources):
    sources_by_url = {
        s.get("url"): s
        for s in research_sources
        if s.get("url")
    }

    review_items = []

    for verification in verifications:

        if verification.status not in (
            "conflicting",
            "unverified",
        ):
            continue

        relevant_sources = []

        for url in verification.source_url:
            source = sources_by_url.get(url)

            if source:
                relevant_sources.append({
                    "title": source.get("title", ""),
                    "url": url,
                    "content": source.get("content", "")[:2000],
                })

        if verification.status == "conflicting":
            reason = "Sources materially disagree."

        else:
            reason = (
                "Available evidence is insufficient "
                "to verify this claim."
            )

        review_items.append({
            "claim": verification.claim,
            "status": verification.status,
            "reason": reason,
            "confidence": verification.confidence,
            "notes": verification.notes,
            "sources": relevant_sources,
        })

    return review_items

fact_check_prompt = """
You are the Fact Checker Agent in a multi-agent
research system.

Your job is to evaluate whether important research findings
and risk claims are supported by the available evidence.

You MUST NOT invent evidence.
You MUST NOT perform additional research.

The input contains two types of items:

FINDINGS:
Each finding contains:
- claim
- evidence
- source_url
- confidence

RISKS:
Each risk contains:
- description
- severity
- evidence
- source_url
- confidence

For findings:
Use the provided "claim" as the claim being evaluated.

For risks:
Use the provided "description" as the claim being evaluated.

For every item determine whether it is:

verified:
The available evidence reasonably supports the claim.

unverified:
There is insufficient evidence to confirm the claim.

conflicting:
Available evidence contradicts the claim or sources
materially disagree.

For every verification return:

claim:
The exact finding claim or risk description being evaluated.

status:
One of:
- verified
- unverified
- conflicting

confidence:
A number between 0 and 1.

notes:
Brief explanation of why the item received this status.

source_url:
A list of URLs from the provided sources that are relevant
to evaluating this claim.

For conflicting claims, include ALL relevant sources
that disagree or materially support different conclusions.

Use ONLY URLs provided in the input.

SOURCE URL RULES:

- Use ONLY source URLs provided in the input.
- Do NOT invent URLs.
- Do NOT create new URLs.
- If no source URL supports the verification, return null.

IMPORTANT RULES:

- Evaluate only the evidence actually provided.
- Do not assume a claim is true because it has a source.
- Check whether the provided evidence reasonably supports
  the claim.
- Distinguish between correlation and causation.
- Identify exaggerated or overly broad claims.
- Identify outdated or weak evidence when relevant.
- Do not perform new research.
- If evidence is insufficient, mark the claim unverified.

COMPLETION:

Fact checking is complete when the important findings and
risks have been evaluated.

If important claims cannot be verified because evidence is
missing:

needs_more_research = true

missing_information must contain specific evidence gaps.
"""

async def fact_checker_agent(state: AgentState):

    workflow_steps = state.get("workflow_steps", 0) + 1

    print("\n" + "=" * 60)
    print("🔍 FACT CHECKER STARTED")
    print("=" * 60)

    findings = state.get("research_findings", [])
    risks = state.get("risks", [])

    print(f"Findings available: {len(findings)}")
    print(f"Risks available: {len(risks)}")

    fact_check_input = {
        "user_query": state.get("user_query", ""),
        "findings": compact_findings_for_fact_check(findings),
        "risks": compact_risks_for_fact_check(risks),
        "research_sources": [
            {
                "title": s.get("title", ""),
                "url": s.get("url", ""),
                "content": s.get("content", "")[:600]
            } for s in state.get("research_sources", [])[:8]
        ]
    }

    print(
        "\n📤 Sending claims "
        "to Fact Checker..."
    )

    fact_checker_llm = llm2.with_structured_output(FactCheckOutput)

    output = await fact_checker_llm.ainvoke(
        [
            SystemMessage(content=fact_check_prompt),
            HumanMessage(content=json.dumps(fact_check_input))
        ]
    )

    print("\n📥 FACT CHECK RESULTS")

    for verification in output.verifications:
        print(f"\nClaim: {verification.claim}")
        print(f"Status: {verification.status}")
        print(f"Confidence: {verification.confidence}")

    print(f"\nNeeds more research: {output.needs_more_research}")
    print(f"Missing information: {output.missing_information}")

    human_review_items = build_human_review_package(output.verifications, state.get("research_sources", []))



    return {
        "verifications": output.verifications,
        "fact_check_complete": output.fact_check_complete,
        "needs_more_research": output.needs_more_research,
        "missing_information": output.missing_information,
        "research_requests": output.missing_information,
        "completed_agents": ["fact_checker"],
        "workflow_steps": workflow_steps,
        "requires_human_review": bool(human_review_items),
        "human_review_items": human_review_items,
        "messages": [
            AIMessage(
                content=(
                    "Fact Checker completed "
                    f"{len(output.verifications)} "
                    "verifications."
                ),

                name="fact_checker"
            )

        ]
    }