import uuid
from typing import Any

from langgraph.types import Command
from langchain_core.messages import HumanMessage

from app.graph.workflow import graph

from app.core.database import (
    setup_database,
    get_checkpointer,
)

_app = None

async def get_research_app():
    """
    Initialize and compile the LangGraph application once.
    """

    global _app

    if _app is None:

        await setup_database()

        checkpointer = await get_checkpointer()

        _app = graph.compile(
            checkpointer=checkpointer
        )

    return _app


def _interrupt_payload(result: dict[str, Any]) -> dict[str, Any] | None:

    interrupts = result.get(
        "__interrupt__",
        []
    )

    if not interrupts:
        return None

    first_interrupt = interrupts[0]

    payload = getattr(first_interrupt, "value", first_interrupt)

    if isinstance(payload, dict):
        return payload

    return {"value": payload}


def serialize_item(item):

    if hasattr(item, "model_dump"):
        return item.model_dump()

    return item


def _serialize_result(result: dict[str, Any], thread_id: str,) -> dict[str, Any]:

    interrupt_payload = _interrupt_payload(result)

    messages = result.get(
        "messages",
        [],
    )

    last_message = ""

    if messages:
        last = messages[-1]
        last_message = getattr(
            last,
            "content",
            "",
        )
    final_report = (
        result.get("final_report")
        or ""
    )

    return {
        # ============================
        # THREAD
        # ============================
        "thread_id": thread_id,


        # ============================
        # STATUS
        # ============================
        "next_agent": result.get("next_agent"),
        "workflow_steps": result.get("workflow_steps",0,),
        "research_passes": result.get("research_passes",0,),
        "completed_agents": result.get("completed_agents", [],),


        # ============================
        # FINAL
        # ============================
        "final_report": final_report,
        "last_message": last_message,


        # ============================
        # GUARDRAIL
        # ============================
        "guardrail_allowed": result.get("input_guardrail_allowed", True,),
        "guardrail_category": result.get("input_guardrail_category", "",),
        "guardrail_reason": result.get("input_guardrail_reason","",),


        # ============================
        # RESEARCH
        # ============================
        "research_complete": result.get("research_complete", False,),
        "needs_more_research": result.get("needs_more_research", False,),
        "research_findings": [
            serialize_item(item)
            for item in result.get(
                "research_findings",
                [],
            )
        ],
        "research_sources": result.get("research_sources", []),
        "research_queries": result.get("research_queries", [],),
        "missing_information": result.get("missing_information", [],),


        # ============================
        # RISKS
        # ============================
        "risk_analysis_complete": result.get("risk_analysis_complete",False,),
        "risks": [
            serialize_item(item)
            for item in result.get(
                "risks",
                [],
            )
        ],


        # ============================
        # FACT CHECK
        # ============================
        "fact_check_complete": result.get("fact_check_complete", False,),
        "verifications": [
            serialize_item(item)
            for item in result.get(
                "verifications",
                [],
            )
        ],


        # ============================
        # HUMAN REVIEW
        # ============================
        "requires_human_review": (interrupt_payload is not None),

        "human_review_type": (
            interrupt_payload.get(
                "type",
                "",
            )
            if interrupt_payload
            else ""
        ),

        "human_review_items": (
            interrupt_payload.get(
                "items",
                [],
            )

            if interrupt_payload
            else [
                serialize_item(item)
                for item in result.get(
                    "human_review_items",
                    [],
                )
            ]
        ),

        "human_review_message": (
            interrupt_payload.get(
                "message",
                "",
            )

            if interrupt_payload
            else ""
        ),

        "human_decision": result.get("human_decision"),
        "human_feedback": result.get("human_feedback","",),


        # ============================
        # CONFIDENCE
        # ============================
        "confidence_score": result.get("confidence_score"),
    }


async def run_research_agent(user_input: str, thread_id: str | None = None,):

    if not user_input or not user_input.strip():
        raise ValueError("Research query cannot be empty.")

    if not thread_id:
        thread_id = (f"research_{uuid.uuid4().hex}")

    app = await get_research_app()

    config = {
        "configurable": {
            "thread_id": thread_id,
        }
    }

    initial_state = {

        # ============================
        # CORE
        # ============================
        "messages": [HumanMessage(content=user_input)],
        "user_query": user_input,


        # ============================
        # RESEARCH
        # ============================
        "research_findings": [],
        "research_sources": [],
        "research_queries": [],
        "research_passes": 0,
        "research_exhausted": False,
        "research_complete": False,
        "needs_more_research": False,
        "missing_information": [],
        "research_requests": [],


        # ============================
        # RISKS
        # ============================
        "risks": [],
        "risk_analysis_complete": False,


        # ============================
        # FACT CHECK
        # ============================
        "verifications": [],
        "fact_check_complete": False,


        # ============================
        # WORKFLOW
        # ============================
        "completed_agents": [],
        "next_agent": None,
        "workflow_steps": 0,


        # ============================
        # GUARDRAIL
        # ============================
        "input_guardrail_allowed": False,
        "input_guardrail_category": "",
        "input_guardrail_reason": "",


        # ============================
        # HUMAN REVIEW
        # ============================
        "requires_human_review": False,
        "human_review_items": [],
        "human_decision": None,
        "human_feedback": None,


        # ============================
        # FINAL
        # ============================
        "confidence_score": None,
        "final_report": None,
    }

    result = await app.ainvoke(
        initial_state,
        config=config,
    )

    return _serialize_result(
        result,
        thread_id,
    )


async def resume_research_agent(thread_id: str, decision: str, feedback: str = "",):

    if not thread_id:
        raise ValueError("thread_id is required.")

    app = await get_research_app()

    config = {
        "configurable": {
            "thread_id": thread_id,
        }
    }

    result = await app.ainvoke(
        Command(
            resume={
                "decision": decision,
                "feedback": feedback.strip(),
            }
        ),
        config=config,
    )

    return _serialize_result(
        result,
        thread_id,
    )


