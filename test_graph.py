import asyncio
import selectors
import uuid

from app.core.database import get_checkpointer, setup_database
from app.graph.workflow import graph

async def main():

    await setup_database()
    checkpointer = await get_checkpointer()

    app = graph.compile(checkpointer=checkpointer)

    initial_state = {
        "messages": [],
        "user_query": """
Should a country transition to electric vehicles by 2035?
""",

        "research_findings": [],
        "risks": [],
        "verifications": [],

        "research_sources": [],
        "research_queries": [],

        "completed_agents": [],
        "next_agent": None,

        "workflow_steps": 0,

        "research_complete": False,
        "risk_analysis_complete": False,

        "needs_more_research": False,
        "missing_information": [],

        "requires_human_review": False,
        "human_decision": None,
        "human_feedback": None,

        "confidence_score": None,
        "final_report": None,
        }

    result = await app.ainvoke(
        initial_state,
        config={
            "configurable": {
                "thread_id" : f"test_{uuid.uuid4()}",
            }
        }
    )

    print("\n===== FINAL STATE =====\n")
    print(result)

    print("\n===== FINAL REPORT =====\n")
    print(result["final_report"])


if __name__ == "__main__":
    asyncio.run(main(),
                loop_factory=lambda: asyncio.SelectorEventLoop(
                    selectors.SelectSelector()
                ))