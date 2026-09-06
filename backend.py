import json
import uuid
from typing import Any, AsyncIterator

from langchain_core.messages import HumanMessage
from langgraph.types import Command

from app.core.database import get_checkpointer, setup_database
from app.graph.workflow import graph


# ============================================================================
# CONSTANTS
# ============================================================================

WORKFLOW_AGENTS = frozenset(
    {
        "input_guardrail",
        "supervisor",
        "research_agent",
        "risk_agent",
        "fact_checker_agent",
        "human_review",
        "report_generator",
    }
)


# ============================================================================
# APPLICATION INITIALIZATION
# ============================================================================

_app = None


async def get_research_app():
    """
    Initialize and compile the LangGraph application once.

    The compiled graph is reused for subsequent requests.
    """
    global _app

    if _app is None:
        await setup_database()

        checkpointer = await get_checkpointer()

        _app = graph.compile(
            checkpointer=checkpointer,
        )

    return _app


# ============================================================================
# CONFIG / STATE
# ============================================================================

def _make_config(thread_id: str) -> dict[str, Any]:
    """Create the LangGraph configuration for a thread."""
    return {
        "configurable": {
            "thread_id": thread_id,
        }
    }


def _make_initial_state(user_input: str) -> dict[str, Any]:
    """
    Create the initial research workflow state.

    Keeping this in one place prevents run_research_agent() and
    stream_research_agent() from drifting apart.
    """
    return {
        # ------------------------------------------------------------------
        # CORE
        # ------------------------------------------------------------------
        "messages": [
            HumanMessage(content=user_input),
        ],
        "user_query": user_input,

        # ------------------------------------------------------------------
        # RESEARCH
        # ------------------------------------------------------------------
        "research_findings": [],
        "research_sources": [],
        "research_queries": [],
        "research_passes": 0,
        "research_exhausted": False,
        "research_complete": False,
        "needs_more_research": False,
        "missing_information": [],
        "research_requests": [],

        # ------------------------------------------------------------------
        # RISKS
        # ------------------------------------------------------------------
        "risks": [],
        "risk_analysis_complete": False,

        # ------------------------------------------------------------------
        # FACT CHECK
        # ------------------------------------------------------------------
        "verifications": [],
        "fact_check_complete": False,

        # ------------------------------------------------------------------
        # WORKFLOW
        # ------------------------------------------------------------------
        "completed_agents": [],
        "next_agent": None,
        "workflow_steps": 0,

        # ------------------------------------------------------------------
        # GUARDRAIL
        # ------------------------------------------------------------------
        "input_guardrail_allowed": False,
        "input_guardrail_category": "",
        "input_guardrail_reason": "",

        # ------------------------------------------------------------------
        # HUMAN REVIEW
        # ------------------------------------------------------------------
        "requires_human_review": False,
        "human_review_items": [],
        "human_decision": None,
        "human_feedback": None,

        # ------------------------------------------------------------------
        # FINAL
        # ------------------------------------------------------------------
        "confidence_score": None,
        "final_report": None,
    }


def _get_thread_id(thread_id: str | None) -> str:
    """Return an existing thread ID or generate a new one."""
    return thread_id or f"research_{uuid.uuid4().hex}"


# ============================================================================
# SERIALIZATION
# ============================================================================

def serialize_item(value: Any) -> Any:
    """
    Convert Pydantic-style objects into dictionaries.

    Everything else is returned unchanged.
    """
    if hasattr(value, "model_dump"):
        return value.model_dump()

    return value


def serialize_text_content(value: Any) -> str:
    """
    Convert LangChain/Gemini structured message content into plain text.
    """
    if value is None:
        return ""

    if isinstance(value, str):
        return value

    if isinstance(value, list):
        parts: list[str] = []

        for item in value:
            if isinstance(item, str):
                parts.append(item)
                continue

            if isinstance(item, dict):
                text = item.get("text")

                if isinstance(text, str):
                    parts.append(text)
                    continue

                content = item.get("content")

                if isinstance(content, str):
                    parts.append(content)
                    continue

            text = getattr(item, "text", None)

            if isinstance(text, str):
                parts.append(text)
                continue

            content = getattr(item, "content", None)

            if isinstance(content, str):
                parts.append(content)

        return "\n\n".join(
            part for part in parts if part
        )

    if isinstance(value, dict):
        text = value.get("text")

        if isinstance(text, str):
            return text

        content = value.get("content")

        if isinstance(content, str):
            return content

    return str(value)


def serialize_stream_update(value: Any) -> Any:
    """
    Recursively serialize graph event output so it can safely be JSON encoded.
    """
    if isinstance(value, dict):
        return {
            key: serialize_stream_update(item)
            for key, item in value.items()
        }

    if isinstance(value, list):
        return [
            serialize_stream_update(item)
            for item in value
        ]

    if hasattr(value, "model_dump"):
        return serialize_stream_update(
            value.model_dump()
        )

    if hasattr(value, "content"):
        return {
            "type": getattr(
                value,
                "type",
                "message",
            ),
            "content": serialize_stream_update(
                value.content
            ),
        }

    return value


# ============================================================================
# INTERRUPTS
# ============================================================================

def _extract_interrupt_payload(
    interrupts: Any,
) -> dict[str, Any] | None:
    """
    Convert a LangGraph interrupt collection into a normalized dictionary.
    """
    if not interrupts:
        return None

    first_interrupt = interrupts[0]

    payload = getattr(
        first_interrupt,
        "value",
        first_interrupt,
    )

    if isinstance(payload, dict):
        return payload

    return {"value": payload}


def _interrupt_payload(
    result: dict[str, Any],
) -> dict[str, Any] | None:
    """
    Extract an interrupt payload from a graph result.
    """
    return _extract_interrupt_payload(
        result.get("__interrupt__", [])
    )


def _snapshot_interrupt_payload(
    snapshot: Any,
) -> dict[str, Any] | None:
    """
    Extract pending interrupt information from a LangGraph StateSnapshot.

    Uses snapshot.interrupts first and falls back to __interrupt__ in values
    for compatibility with different LangGraph versions/configurations.
    """
    interrupts = getattr(
        snapshot,
        "interrupts",
        None,
    )

    if interrupts:
        return _extract_interrupt_payload(
            interrupts
        )

    values = getattr(
        snapshot,
        "values",
        {},
    ) or {}

    return _interrupt_payload(values)


# ============================================================================
# RESULT SERIALIZATION
# ============================================================================

def _serialize_result(
    result: dict[str, Any],
    thread_id: str,
) -> dict[str, Any]:
    """
    Convert the complete LangGraph state into the API response format.
    """
    interrupt_payload = _interrupt_payload(result)

    messages = result.get("messages", [])

    last_message = ""

    if messages:
        last_message = serialize_text_content(
            getattr(
                messages[-1],
                "content",
                "",
            )
        )

    return {
        # ------------------------------------------------------------------
        # THREAD
        # ------------------------------------------------------------------
        "thread_id": thread_id,

        # ------------------------------------------------------------------
        # STATUS
        # ------------------------------------------------------------------
        "next_agent": result.get("next_agent"),
        "workflow_steps": result.get("workflow_steps", 0),
        "research_passes": result.get("research_passes", 0),
        "completed_agents": result.get(
            "completed_agents",
            [],
        ),
        "research_exhausted": result.get(
            "research_exhausted",
            False,
        ),
        "ui_status": result.get("ui_status"),

        # ------------------------------------------------------------------
        # FINAL
        # ------------------------------------------------------------------
        "final_report": serialize_text_content(
            result.get("final_report")
        ),
        "last_message": last_message,

        # ------------------------------------------------------------------
        # GUARDRAIL
        # ------------------------------------------------------------------
        "guardrail_allowed": result.get(
            "input_guardrail_allowed",
            True,
        ),
        "guardrail_category": result.get(
            "input_guardrail_category",
            "",
        ),
        "guardrail_reason": result.get(
            "input_guardrail_reason",
            "",
        ),

        # ------------------------------------------------------------------
        # RESEARCH
        # ------------------------------------------------------------------
        "research_complete": result.get(
            "research_complete",
            False,
        ),
        "needs_more_research": result.get(
            "needs_more_research",
            False,
        ),
        "research_findings": [
            serialize_item(item)
            for item in result.get(
                "research_findings",
                [],
            )
        ],
        "research_sources": result.get(
            "research_sources",
            [],
        ),
        "research_queries": result.get(
            "research_queries",
            [],
        ),
        "missing_information": result.get(
            "missing_information",
            [],
        ),

        # ------------------------------------------------------------------
        # RISKS
        # ------------------------------------------------------------------
        "risk_analysis_complete": result.get(
            "risk_analysis_complete",
            False,
        ),
        "risks": [
            serialize_item(item)
            for item in result.get(
                "risks",
                [],
            )
        ],

        # ------------------------------------------------------------------
        # FACT CHECK
        # ------------------------------------------------------------------
        "fact_check_complete": result.get(
            "fact_check_complete",
            False,
        ),
        "verifications": [
            serialize_item(item)
            for item in result.get(
                "verifications",
                [],
            )
        ],

        # ------------------------------------------------------------------
        # HUMAN REVIEW
        # ------------------------------------------------------------------
        "requires_human_review": (
            interrupt_payload is not None
        ),

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

        "human_decision": result.get(
            "human_decision"
        ),
        "human_feedback": result.get(
            "human_feedback",
            "",
        ),

        # ------------------------------------------------------------------
        # CONFIDENCE
        # ------------------------------------------------------------------
        "confidence_score": result.get(
            "confidence_score"
        ),
    }


# ============================================================================
# SSE HELPERS
# ============================================================================

def _sse(payload: dict[str, Any]) -> str:
    """
    Convert a dictionary into a Server-Sent Events message.
    """
    return f"data: {json.dumps(payload)}\n\n"


def _agent_started_event(
    agent: str,
    thread_id: str,
) -> str:
    return _sse(
        {
            "type": "agent_started",
            "agent": agent,
            "thread_id": thread_id,
        }
    )


def _agent_update_event(
    agent: str,
    thread_id: str,
    output: Any,
) -> str:
    return _sse(
        {
            "type": "agent_update",
            "agent": agent,
            "thread_id": thread_id,
            "update": serialize_stream_update(
                output
            ),
        }
    )


def _workflow_status_event(
    thread_id: str,
    status: Any,
) -> str:
    return _sse(
        {
            "type": "workflow_status",
            "thread_id": thread_id,
            "status": status,
        }
    )


def _human_review_event(
    thread_id: str,
    payload: dict[str, Any],
) -> str:
    return _sse(
        {
            "type": "human_review_required",
            "agent": "human_review",
            "thread_id": thread_id,
            "human_review_type": payload.get(
                "type",
                "fact_check_review",
            ),
            "human_review_message": payload.get(
                "message",
                "Please review the research results.",
            ),
            "human_review_items": [
                serialize_item(item)
                for item in payload.get(
                    "items",
                    [],
                )
            ],
        }
    )


def _complete_event(
    thread_id: str,
    result: dict[str, Any],
) -> str:
    return _sse(
        {
            "type": "complete",
            "data": _serialize_result(
                result,
                thread_id,
            ),
        }
    )


# ============================================================================
# EVENT PROCESSING
# ============================================================================

def _event_node_name(event: dict[str, Any]) -> str | None:
    """Extract the LangGraph node name from an event."""
    metadata = event.get(
        "metadata",
        {}
    )

    return metadata.get(
        "langgraph_node"
    )


def _event_output(event: dict[str, Any]) -> Any:
    """Extract node output from a LangGraph event."""
    return (
        event
        .get("data", {})
        .get("output")
    )


def _is_workflow_agent(
    node_name: str | None,
) -> bool:
    return node_name in WORKFLOW_AGENTS


# ============================================================================
# RUN ONCE
# ============================================================================

async def run_research_agent(
    user_input: str,
    thread_id: str | None = None,
) -> dict[str, Any]:
    """
    Execute the research graph synchronously and return its final state.

    If the graph pauses for human review, the returned result contains
    requires_human_review=True and the relevant review payload.
    """
    if not user_input or not user_input.strip():
        raise ValueError(
            "Research query cannot be empty."
        )

    thread_id = _get_thread_id(thread_id)

    app = await get_research_app()

    config = _make_config(thread_id)

    result = await app.ainvoke(
        _make_initial_state(user_input),
        config=config,
    )

    return _serialize_result(
        result,
        thread_id,
    )


# ============================================================================
# STREAM RESEARCH
# ============================================================================

async def stream_research_agent(
    user_input: str,
    thread_id: str | None = None,
) -> AsyncIterator[str]:
    """
    Stream research workflow events using Server-Sent Events.

    Events:
        agent_started
        agent_update
        workflow_status
        human_review_required
        complete
    """
    if not user_input or not user_input.strip():
        raise ValueError(
            "Research query cannot be empty."
        )

    thread_id = _get_thread_id(thread_id)

    app = await get_research_app()

    config = _make_config(thread_id)

    # ------------------------------------------------------------------------
    # STREAM GRAPH
    # ------------------------------------------------------------------------

    async for event in app.astream_events(
        _make_initial_state(user_input),
        config=config,
        version="v2",
    ):
        event_type = event.get("event")

        node_name = _event_node_name(event)

        if not _is_workflow_agent(node_name):
            continue

        # --------------------------------------------------------------------
        # AGENT START
        # --------------------------------------------------------------------

        if event_type == "on_chain_start":
            yield _agent_started_event(
                node_name,
                thread_id,
            )
            continue

        # --------------------------------------------------------------------
        # AGENT END
        # --------------------------------------------------------------------

        if event_type != "on_chain_end":
            continue

        output = _event_output(event)

        if output is None:
            output = {}

        yield _agent_update_event(
            node_name,
            thread_id,
            output,
        )

        # --------------------------------------------------------------------
        # WORKFLOW STATUS
        # --------------------------------------------------------------------

        if isinstance(output, dict):
            ui_status = output.get(
                "ui_status"
            )

            if ui_status:
                yield _workflow_status_event(
                    thread_id,
                    ui_status,
                )

    # ------------------------------------------------------------------------
    # CHECK FINAL STATE
    # ------------------------------------------------------------------------

    snapshot = await app.aget_state(
        config
    )

    interrupt_payload = (
        _snapshot_interrupt_payload(snapshot)
    )

    # ------------------------------------------------------------------------
    # HUMAN REVIEW
    # ------------------------------------------------------------------------

    if interrupt_payload:
        yield _human_review_event(
            thread_id,
            interrupt_payload,
        )

        # IMPORTANT:
        # Do not emit "complete".
        #
        # The graph is checkpointed and waiting for
        # Command(resume=...).
        return

    # ------------------------------------------------------------------------
    # COMPLETED
    # ------------------------------------------------------------------------

    result = snapshot.values

    yield _complete_event(
        thread_id,
        result,
    )


# ============================================================================
# RESUME AFTER HUMAN REVIEW
# ============================================================================

async def resume_research_agent(
    thread_id: str,
    decision: str,
    feedback: str = "",
) -> AsyncIterator[str]:
    """
    Resume a paused research workflow after human review.

    The workflow continues from the LangGraph checkpoint associated
    with thread_id.
    """
    if not thread_id:
        raise ValueError(
            "thread_id is required."
        )

    if not decision or not decision.strip():
        raise ValueError(
            "Human review decision is required."
        )

    app = await get_research_app()

    config = _make_config(thread_id)

    command = Command(
        resume={
            "decision": decision.strip(),
            "feedback": feedback.strip(),
        }
    )

    # ------------------------------------------------------------------------
    # RESUME GRAPH
    # ------------------------------------------------------------------------

    async for event in app.astream_events(
        command,
        config=config,
        version="v2",
    ):
        event_type = event.get("event")

        node_name = _event_node_name(event)

        if not _is_workflow_agent(node_name):
            continue

        # --------------------------------------------------------------------
        # AGENT START
        # --------------------------------------------------------------------

        if event_type == "on_chain_start":
            yield _agent_started_event(
                node_name,
                thread_id,
            )
            continue

        # --------------------------------------------------------------------
        # AGENT END
        # --------------------------------------------------------------------

        if event_type != "on_chain_end":
            continue

        output = _event_output(event)

        if output is None:
            output = {}

        yield _agent_update_event(
            node_name,
            thread_id,
            output,
        )

        # --------------------------------------------------------------------
        # WORKFLOW STATUS
        # --------------------------------------------------------------------

        if isinstance(output, dict):
            ui_status = output.get(
                "ui_status"
            )

            if ui_status:
                yield _workflow_status_event(
                    thread_id,
                    ui_status,
                )

    # ------------------------------------------------------------------------
    # CHECK WHETHER GRAPH PAUSED AGAIN
    # ------------------------------------------------------------------------

    snapshot = await app.aget_state(
        config
    )

    interrupt_payload = (
        _snapshot_interrupt_payload(snapshot)
    )

    if interrupt_payload:
        yield _human_review_event(
            thread_id,
            interrupt_payload,
        )

        return

    # ------------------------------------------------------------------------
    # WORKFLOW COMPLETED
    # ------------------------------------------------------------------------

    yield _complete_event(
        thread_id,
        snapshot.values,
    )
