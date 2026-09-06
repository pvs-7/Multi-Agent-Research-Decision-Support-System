import uuid
import json
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

def serialize_text_content(value) -> str:
    """
    Convert Gemini/LangChain structured content into plain text.
    """

    if value is None:
        return ""

    # Already plain text
    if isinstance(value, str):
        return value

    # Gemini structured content
    if isinstance(value, list):
        parts = []

        for item in value:

            if isinstance(item, str):
                parts.append(item)

            elif isinstance(item, dict):

                text = item.get("text")

                if isinstance(text, str):
                    parts.append(text)

                elif isinstance(item.get("content"), str):
                    parts.append(item["content"])

            elif hasattr(item, "text"):

                if isinstance(item.text, str):
                    parts.append(item.text)

            elif hasattr(item, "content"):

                if isinstance(item.content, str):
                    parts.append(item.content)

        return "\n\n".join(
            part
            for part in parts
            if part
        )

    # Single structured content block
    if isinstance(value, dict):

        if isinstance(value.get("text"), str):
            return value["text"]

        if isinstance(value.get("content"), str):
            return value["content"]

    # Fallback
    return str(value)

def _serialize_result(result: dict[str, Any], thread_id: str,) -> dict[str, Any]:

    interrupt_payload = _interrupt_payload(result)

    messages = result.get(
        "messages",
        [],
    )

    last_message = ""

    if messages:
        last = messages[-1]
        last_message = serialize_text_content(
            getattr(
                last,
                "content",
                "",
            )
        )

    final_report = serialize_text_content(
        result.get("final_report")
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
        "research_exhausted": result.get(
            "research_exhausted",
            False,
        ),
        "ui_status": result.get(
            "ui_status"
        ),

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

"""
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
"""

async def resume_research_agent(
    thread_id: str,
    decision: str,
    feedback: str = "",
):
    if not thread_id:
        raise ValueError("thread_id is required.")

    app = await get_research_app()

    config = {
        "configurable": {
            "thread_id": thread_id,
        }
    }

    command = Command(
        resume={
            "decision": decision,
            "feedback": feedback.strip(),
        }
    )

    workflow_agents = {
        "input_guardrail",
        "supervisor",
        "research_agent",
        "risk_agent",
        "fact_checker_agent",
        "human_review",
        "report_generator",
    }

    # =========================================================
    # RESUME THE PAUSED GRAPH
    # =========================================================

    async for event in app.astream_events(
        command,
        config=config,
        version="v2",
    ):
        event_type = event.get("event")

        metadata = event.get(
            "metadata",
            {},
        )

        node_name = metadata.get(
            "langgraph_node"
        )

        if node_name not in workflow_agents:
            continue

        # =====================================================
        # AGENT STARTED
        # =====================================================

        if event_type == "on_chain_start":

            payload = {
                "type": "agent_started",
                "agent": node_name,
                "thread_id": thread_id,
            }

            yield (
                f"data: "
                f"{json.dumps(payload)}"
                f"\n\n"
            )

        # =====================================================
        # AGENT FINISHED
        # =====================================================

        elif event_type == "on_chain_end":

            output = (
                event
                .get("data", {})
                .get("output")
            )

            if output is None:
                output = {}

            serialized_output = (
                serialize_stream_update(output)
            )

            payload = {
                "type": "agent_update",
                "agent": node_name,
                "thread_id": thread_id,
                "update": serialized_output,
            }

            yield (
                f"data: "
                f"{json.dumps(payload)}"
                f"\n\n"
            )

            # ==========================================
            # WORKFLOW STATUS
            # ==========================================

            if isinstance(output, dict):

                ui_status = output.get("ui_status")
                if ui_status:
                    status_payload = {
                        "type": "workflow_status",
                        "thread_id": thread_id,
                        "status": ui_status,
                    }

                    yield (
                        f"data: "
                        f"{json.dumps(status_payload)}"
                        f"\n\n"
                    )

    # =========================================================
    # CHECK WHETHER GRAPH PAUSED AGAIN
    # =========================================================

    snapshot = await app.aget_state(config)

    interrupt_payload = (
        _snapshot_interrupt_payload(snapshot)
    )

    if interrupt_payload:

        hitl_payload = {
            "type": "human_review_required",
            "agent": "human_review",
            "thread_id": thread_id,

            "human_review_type": (
                interrupt_payload.get(
                    "type",
                    "fact_check_review",
                )
            ),

            "human_review_message": (
                interrupt_payload.get(
                    "message",
                    "Please review the research results.",
                )
            ),

            "human_review_items": [
                serialize_item(item)
                for item in interrupt_payload.get(
                    "items",
                    [],
                )
            ],
        }

        yield (
            f"data: "
            f"{json.dumps(hitl_payload)}"
            f"\n\n"
        )

        return

    # =========================================================
    # WORKFLOW REALLY FINISHED
    # =========================================================

    result = snapshot.values

    serialized = _serialize_result(
        result,
        thread_id,
    )

    payload = {
        "type": "complete",
        "data": serialized,
    }

    yield (
        f"data: "
        f"{json.dumps(payload)}"
        f"\n\n"
    )

"""
async def stream_research_agent(
    user_input: str,
    thread_id: str | None = None
):

    if not user_input or not user_input.strip():
        raise ValueError("Research query cannot be empty")

    if not thread_id:
        thread_id = f"research_{uuid.uuid4().hex}"

    app = await get_research_app()

    config = {
        "configurable": {
            "thread_id": thread_id
        }
    }

    initial_state = {

        "messages": [
            HumanMessage(content=user_input)
        ],

        "user_query": user_input,

        "research_findings": [],
        "research_sources": [],
        "research_queries": [],
        "research_passes": 0,
        "research_exhausted": False,
        "research_complete": False,
        "needs_more_research": False,
        "missing_information": [],
        "research_requests": [],

        "risks": [],
        "risk_analysis_complete": False,

        "verifications": [],
        "fact_check_complete": False,

        "completed_agents": [],
        "next_agent": None,
        "workflow_steps": 0,

        "input_guardrail_allowed": False,
        "input_guardrail_category": "",
        "input_guardrail_reason": "",

        "requires_human_review": False,
        "human_review_items": [],
        "human_decision": None,
        "human_feedback": None,

        "confidence_score": None,
        "final_report": None,
    }

    # Only these are actual workflow nodes.
    workflow_agents = {
        "input_guardrail",
        "supervisor",
        "research_agent",
        "risk_agent",
        "fact_checker_agent",
        "human_review",
        "report_generator",
    }

    async for event in app.astream_events(
        initial_state,
        config=config,
        version="v2"
    ):

        event_type = event.get("event")

        metadata = event.get(
            "metadata",
            {}
        )

        # LangGraph node name
        node_name = metadata.get(
            "langgraph_node"
        )

        if (
            node_name not in workflow_agents
        ):
            continue


        # ==========================================
        # AGENT STARTED
        # ==========================================

        if event_type == "on_chain_start":

            payload = {
                "type": "agent_started",
                "agent": node_name,
                "thread_id": thread_id,
            }

            yield (
                f"data: "
                f"{json.dumps(payload)}"
                f"\n\n"
            )


        # ==========================================
        # AGENT FINISHED
        # ==========================================

        elif event_type == "on_chain_end":

            output = (
                event
                .get("data", {})
                .get("output")
            )

            if output is None:
                output = {}

            payload = {
                "type": "agent_update",
                "agent": node_name,
                "thread_id": thread_id,
                "update": serialize_stream_update(
                    output
                ),
            }

            yield (
                f"data: "
                f"{json.dumps(payload)}"
                f"\n\n"
            )


    # ==========================================
    # GET FINAL GRAPH STATE
    # ==========================================

    final_state = await app.aget_state(
        config
    )

    result = final_state.values

    serialized = _serialize_result(
        result,
        thread_id,
    )

    payload = {
        "type": "complete",
        "data": serialized,
    }

    yield (
        f"data: "
        f"{json.dumps(payload)}"
        f"\n\n"
    )
"""
async def stream_research_agent(
    user_input: str,
    thread_id: str | None = None,
):
    if not user_input or not user_input.strip():
        raise ValueError("Research query cannot be empty")

    if not thread_id:
        thread_id = f"research_{uuid.uuid4().hex}"

    app = await get_research_app()

    config = {
        "configurable": {
            "thread_id": thread_id,
        }
    }

    initial_state = {
        "messages": [
            HumanMessage(content=user_input)
        ],

        "user_query": user_input,

        "research_findings": [],
        "research_sources": [],
        "research_queries": [],
        "research_passes": 0,
        "research_exhausted": False,
        "research_complete": False,
        "needs_more_research": False,
        "missing_information": [],
        "research_requests": [],

        "risks": [],
        "risk_analysis_complete": False,

        "verifications": [],
        "fact_check_complete": False,

        "completed_agents": [],
        "next_agent": None,
        "workflow_steps": 0,

        "input_guardrail_allowed": False,
        "input_guardrail_category": "",
        "input_guardrail_reason": "",

        "requires_human_review": False,
        "human_review_items": [],
        "human_decision": None,
        "human_feedback": None,

        "confidence_score": None,
        "final_report": None,
    }

    workflow_agents = {
        "input_guardrail",
        "supervisor",
        "research_agent",
        "risk_agent",
        "fact_checker_agent",
        "human_review",
        "report_generator",
    }

    # =========================================================
    # STREAM THE GRAPH
    # =========================================================

    async for event in app.astream_events(
        initial_state,
        config=config,
        version="v2",
    ):
        event_type = event.get("event")

        metadata = event.get(
            "metadata",
            {},
        )

        node_name = metadata.get(
            "langgraph_node"
        )

        if node_name not in workflow_agents:
            continue

        # =====================================================
        # AGENT STARTED
        # =====================================================

        if event_type == "on_chain_start":

            payload = {
                "type": "agent_started",
                "agent": node_name,
                "thread_id": thread_id,
            }

            yield (
                f"data: "
                f"{json.dumps(payload)}"
                f"\n\n"
            )

        # =====================================================
        # AGENT FINISHED
        # =====================================================

        elif event_type == "on_chain_end":

            output = (
                event
                .get("data", {})
                .get("output")
            )

            if output is None:
                output = {}

            serialized_output = (
                serialize_stream_update(output)
            )

            payload = {
                "type": "agent_update",
                "agent": node_name,
                "thread_id": thread_id,
                "update": serialized_output,
            }

            yield (
                f"data: "
                f"{json.dumps(payload)}"
                f"\n\n"
            )

            # =====================================================
            # WORKFLOW STATUS
            # =====================================================

            if isinstance(output, dict):

                ui_status = output.get("ui_status")

                if ui_status:

                    status_payload = {
                        "type": "workflow_status",
                        "thread_id": thread_id,
                        "status": ui_status,
                    }

                    yield (
                        f"data: "
                        f"{json.dumps(status_payload)}"
                        f"\n\n"
                    )

    # =========================================================
    # THE GRAPH HAS STOPPED / PAUSED
    # =========================================================

    snapshot = await app.aget_state(config)

    interrupt_payload = (
        _snapshot_interrupt_payload(snapshot)
    )

    # =========================================================
    # HUMAN REVIEW REQUIRED
    # =========================================================

    if interrupt_payload:

        hitl_payload = {
            "type": "human_review_required",
            "agent": "human_review",
            "thread_id": thread_id,

            "human_review_type": (
                interrupt_payload.get(
                    "type",
                    "fact_check_review",
                )
            ),

            "human_review_message": (
                interrupt_payload.get(
                    "message",
                    "Please review the research results.",
                )
            ),

            "human_review_items": [
                serialize_item(item)
                for item in interrupt_payload.get(
                    "items",
                    [],
                )
            ],
        }

        yield (
            f"data: "
            f"{json.dumps(hitl_payload)}"
            f"\n\n"
        )

        # VERY IMPORTANT:
        # Do NOT emit complete.
        #
        # LangGraph is now checkpointed and waiting
        # for Command(resume=...).
        return

    # =========================================================
    # TRUE WORKFLOW COMPLETION
    # =========================================================

    result = snapshot.values

    serialized = _serialize_result(
        result,
        thread_id,
    )

    payload = {
        "type": "complete",
        "data": serialized,
    }

    yield (
        f"data: "
        f"{json.dumps(payload)}"
        f"\n\n"
    )

def serialize_stream_update(value):

    if isinstance(value, dict):

        return {
            key: serialize_stream_update(
                item
            )
            for key, item in value.items()
        }

    if isinstance(value, list):

        return [
            serialize_stream_update(
                item
            )
            for item in value
        ]

    if hasattr(value, "model_dump"):

        return value.model_dump()

    if hasattr(value, "content"):

        return {
            "type": (
                getattr(
                    value,
                    "type",
                    "message"
                )
            ),
            "content": value.content,
        }

    return value


def _snapshot_interrupt_payload(snapshot) -> dict[str, Any] | None:
    """
    Extract the LangGraph interrupt payload from a StateSnapshot.

    LangGraph exposes pending interrupts on the snapshot itself.
    Fall back to __interrupt__ in values for compatibility.
    """

    interrupts = getattr(snapshot, "interrupts", None)

    if interrupts:
        first_interrupt = interrupts[0]

        payload = getattr(
            first_interrupt,
            "value",
            first_interrupt,
        )

        if isinstance(payload, dict):
            return payload

        return {"value": payload}

    # Compatibility fallback
    values = getattr(snapshot, "values", {}) or {}

    return _interrupt_payload(values)