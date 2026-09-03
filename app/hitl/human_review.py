from langgraph.types import interrupt
from app.graph.state import AgentState

def human_review(state: AgentState):

    review_items = state.get("human_review_items", [])

    conflicting = sum(
        1 for item in review_items
        if item.get("status") == "conflicting"
    )

    unverified = sum(
        1 for item in review_items
        if item.get("status") == "unverified"
    )

    decision = interrupt({
        "type": "fact_check_review",
        "message": (
            f"Human review required: "
            f"{conflicting} conflicting claim(s), "
            f"{unverified} unverified claim(s)."
        ),
        "items": review_items,
    })

    return {
        "human_decision": decision["decision"],
        "human_feedback": decision.get("feedback"),
        "requires_human_review": False,
    }