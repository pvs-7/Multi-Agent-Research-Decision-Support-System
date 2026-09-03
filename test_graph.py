import asyncio
import selectors
import uuid

from langgraph.types import Command

from app.core.database import get_checkpointer, setup_database
from app.graph.workflow import graph


async def run_cli():

    # ---------------------------------------------------------
    # Setup
    # ---------------------------------------------------------

    await setup_database()
    checkpointer = await get_checkpointer()

    app = graph.compile(checkpointer=checkpointer)

    thread_id = f"cli_{uuid.uuid4()}"

    config = {
        "configurable": {
            "thread_id": thread_id,
        }
    }

    # ---------------------------------------------------------
    # Initial state
    # ---------------------------------------------------------

    initial_state = {
        "messages": [],

        "user_query": (
            "Analyze the evidence supporting the claim that NVIDIA stock will increase by at least 50% over the next 12 months. Determine whether this prediction can be verified using currently available evidence."
        ),

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

        "fact_check_complete": False,
        "research_requests": [],

        "input_guardrail_allowed": False,
        "input_guardrail_category": "ambiguous",
        "input_guardrail_reason": "",

        "requires_human_review": False,
        "human_review_items": [],
        "human_decision": None,
        "human_feedback": None,

        "confidence_score": None,
        "final_report": None,
    }

    # ---------------------------------------------------------
    # Start graph
    # ---------------------------------------------------------

    print("\n" + "=" * 60)
    print("🚀 STARTING RESEARCH WORKFLOW")
    print("=" * 60)

    result = await app.ainvoke(
        initial_state,
        config=config,
    )

    # ---------------------------------------------------------
    # HITL LOOP
    # ---------------------------------------------------------

    while True:

        state = await app.aget_state(config)

        # -----------------------------------------------------
        # Check if graph is waiting for human input
        # -----------------------------------------------------

        if state.interrupts:

            interrupt_data = state.interrupts[0]

            print("\n" + "=" * 60)
            print("👤 HUMAN REVIEW REQUIRED")
            print("=" * 60)

            review = interrupt_data.value

            print(f"\nMessage:")
            print(review.get("message"))

            items = review.get("items", [])

            for i, item in enumerate(items, start=1):

                print("\n" + "-" * 60)
                print(f"CLAIM {i}")
                print("-" * 60)

                print(
                    f"Claim: "
                    f"{item.get('claim', '')}"
                )

                print(
                    f"Status: "
                    f"{item.get('status', '')}"
                )

                print(
                    f"Confidence: "
                    f"{item.get('confidence', '')}"
                )

                print(
                    f"Notes: "
                    f"{item.get('notes', '')}"
                )

                sources = item.get("sources", [])

                if sources:
                    print("\nSources:")

                    for source in sources:
                        print(
                            f"  - {source.get('title', '')}"
                        )
                        print(
                            f"    {source.get('url', '')}"
                        )
                        print(
                            f"    {source.get('content', '')[:500]}"
                        )

            # -------------------------------------------------
            # Ask human
            # -------------------------------------------------

            print("\n" + "-" * 60)
            print("What would you like to do?")
            print("  [a] Approve")
            print("  [r] Request more research")
            print("  [x] Reject")
            print("-" * 60)

            while True:

                choice = input(
                    "\nYour decision: "
                ).strip().lower()

                if choice in ("a", "r", "x"):
                    break

                print(
                    "Please enter: "
                    "a, r, or x."
                )

            feedback = input(
                "Feedback (optional): "
            ).strip()

            if choice == "a":
                decision = "approve"

            elif choice == "r":
                decision = "request_more_research"

            else:
                decision = "reject"

            human_response = {
                "decision": decision,
                "feedback": feedback or None,
            }

            print(
                f"\n➡️ Resuming workflow with: "
                f"{decision}"
            )

            # -------------------------------------------------
            # Resume SAME thread
            # -------------------------------------------------

            result = await app.ainvoke(
                Command(
                    resume=human_response
                ),
                config=config,
            )

            continue

        # -----------------------------------------------------
        # No interrupt → workflow finished
        # -----------------------------------------------------

        break

    # ---------------------------------------------------------
    # Final state
    # ---------------------------------------------------------

    print("\n" + "=" * 60)
    print("✅ WORKFLOW COMPLETE")
    print("=" * 60)

    print("\n===== FINAL REPORT =====\n")

    print(
        result.get(
            "final_report",
            "No final report generated."
        )
    )


if __name__ == "__main__":
    asyncio.run(
        run_cli(),
        loop_factory=lambda: asyncio.SelectorEventLoop(
            selectors.SelectSelector()
        ),
    )