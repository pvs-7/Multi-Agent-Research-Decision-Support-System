from app.graph.state import AgentState

MAX_WORKFLOW_STEPS = 12
MAX_RESEARCH_PASSES = 3

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

    fact_check_complete = state.get(
        "fact_check_complete", 
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

    requires_human_review = state.get(
        "requires_human_review",
        False
    )

    human_decision = state.get("human_decision")


    print(f"Workflow step: {workflow_steps}")
    print(f"Research passes: {research_passes}")
    print(f"Research complete: {research_complete}")
    print(f"Needs more research: {needs_more_research}")
    print(f"Research exhausted: {research_exhausted}")
    print(f"Risk complete: {risk_analysis_complete}")
    print(f"Fact check complete:  {fact_check_complete}")
    print(f"Requires human review:  {requires_human_review}")
    print(f"Human decision: {human_decision}")

    # ========================================================
    # PROCESS HUMAN DECISION
    # ========================================================

    if human_decision == "approve":

        print("\n✅ Human approved.")
        print("➡️ Proceeding to report.")

        return {
            "next_agent": "report_generator",
            "workflow_steps": workflow_steps,
            "requires_human_review": False,
        }

    if human_decision == "request_more_research":

        print("\n🔄 Human requested more research.")

        if research_passes < MAX_RESEARCH_PASSES:

            print(
                f"➡️ Running additional research pass "
                f"{research_passes + 1}/{MAX_RESEARCH_PASSES}."
            )

            return {
                "next_agent": "research_agent",
                "workflow_steps": workflow_steps,
                "requires_human_review": False,
                "human_decision": None,
                "ui_status": {
                    "type": "research_requested",
                    "message": (
                        f"Running additional research pass "
                        f"{research_passes + 1}/{MAX_RESEARCH_PASSES}."
                    ),
                },
            }

        print("\n🛑 Maximum research passes reached.")
        print("➡️ Proceeding directly to final report.")

        return {
            "next_agent": "report_generator",
            "workflow_steps": workflow_steps,
            "requires_human_review": False,
            "human_decision": None,
            "research_exhausted": True,
            "ui_status": {
                "type": "research_limit_reached",
                "message": (
                    "Maximum research passes reached. "
                    "Proceeding to final report."
                ),
            },
        }

    if human_decision == "reject":

        print("\n❌ Human rejected the analysis.")

        return {
            "next_agent": "report_generator",
            "workflow_steps": workflow_steps,
            "requires_human_review": False,
        }

    # ========================================================
    # HITL
    # ========================================================

    if requires_human_review and not human_decision:

        print("\n⚠️ Human review required.")
        print("➡️ Routing to human review.")

        return {
            "next_agent": "human_review",
            "workflow_steps": workflow_steps,
        }
    # ========================================================
    # WORKFLOW LIMIT
    # ========================================================

    if workflow_steps >= MAX_WORKFLOW_STEPS:

        print("\n🛑 Maximum workflow steps reached.")

        # ----------------------------------------------------
        # FACT CHECKER MUST RUN AT LEAST ONCE
        # ----------------------------------------------------

        if not fact_check_complete:

            print("⚠️ Fact checking has not run yet.")
            print("➡️ Forcing one fact-checking pass before report.")

            return {
                "next_agent": "fact_checker_agent",
                "workflow_steps": workflow_steps,
                "requires_human_review": False,
                "ui_status": {
                    "type": "workflow_limit_reached",
                    "message": (
                        "Workflow limit reached. "
                        "Running a final fact-check before completing the report."
                    ),
                },
            }

        # ----------------------------------------------------
        # FACT CHECKER ALREADY RAN
        # ----------------------------------------------------

        print("➡️ Fact checking already completed.")
        print("➡️ Proceeding to report generator.")

        return {
            "next_agent": "report_generator",
            "workflow_steps": workflow_steps,
            "requires_human_review": False,
            "ui_status": {
                "type": "workflow_limit_reached",
                "message": (
                    "Maximum workflow steps reached. "
                    "Proceeding to the final report."
                ),
            },
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

        print("\n🛑 Maximum research passes reached.")
        print("➡️ Accepting remaining evidence gaps.")

        return {
            "next_agent": "risk_agent",
            "workflow_steps": workflow_steps,
            "research_exhausted": True,
            "ui_status": {
                "type": "research_limit_reached",
                "message": (
                    "Maximum research passes reached. "
                    "Proceeding with the available evidence."
                ),
            },
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
    # MORE RESEARCH REQUIRED
    # ========================================================

    if needs_more_research and not research_exhausted:

        if research_passes < MAX_RESEARCH_PASSES:

            print("\n🔄 More research required.")
            print("➡️ Returning to research agent.")

            return {
                "next_agent": "research_agent",
                "workflow_steps": workflow_steps,
            }

        print("\n🛑 Maximum research passes reached.")
        print("➡️ Accepting remaining evidence gaps.")

        return {
            "next_agent": "report_generator",
            "workflow_steps": workflow_steps,
            "research_exhausted": True,
        }

    # ========================================================
    # FACT CHECKING
    # ========================================================

    if not fact_check_complete:

        return {
            "next_agent": "fact_checker_agent",
            "workflow_steps": workflow_steps,
        }

    # ========================================================
    # REPORT
    # ========================================================

    print("\n➡️ Research complete.")
    print("➡️ Risk analysis complete.")
    print("➡️ Fact checking complete.")
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