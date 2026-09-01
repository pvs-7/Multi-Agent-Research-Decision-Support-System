import asyncio

from app.graph.workflow import test


async def main():

    initial_state = {
        "user_query": "What are the main risks and opportunities of electric vehicles?",
        "messages": [],
        "research_findings": [],
        "risks": [],
        "verifications": [],
        "requires_human_review": False,
        "human_decision": None,
        "human_feedback": None,
        "confidence_score": None,
        "final_report": None,
        "next_agent": None,
    }

    result = await test.ainvoke(
        initial_state
    )

    print("\n===== FINAL STATE =====\n")
    print(result)

    print("\n===== FINAL REPORT =====\n")
    print(result["final_report"])


if __name__ == "__main__":
    asyncio.run(main())