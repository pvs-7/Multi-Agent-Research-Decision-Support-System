from pathlib import Path
import json
import logging

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import (
    HTMLResponse,
    JSONResponse,
    StreamingResponse,
)
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field, field_validator

from backend import (
    resume_research_agent,
    run_research_agent,
    stream_research_agent,
)


# ============================================================================
# CONFIGURATION
# ============================================================================

BASE_DIR = Path(__file__).resolve().parent

STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

HOST = "127.0.0.1"
PORT = 8000

SSE_MEDIA_TYPE = "text/event-stream"

SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}

VALID_REVIEW_DECISIONS = frozenset(
    {
        "approve",
        "reject",
        "request_more_research",
    }
)


# ============================================================================
# LOGGING
# ============================================================================

logger = logging.getLogger(__name__)


# ============================================================================
# APPLICATION
# ============================================================================

app = FastAPI(
    title="Research Decision Support System",
    description=(
        "Multi-Agent Research System with Guardrails, "
        "Fact Checking, Risk Analysis, and Human-in-the-Loop"
    ),
    version="1.0.0",
)


# ============================================================================
# STATIC FILES / TEMPLATES
# ============================================================================

app.mount(
    "/static",
    StaticFiles(directory=str(STATIC_DIR)),
    name="static",
)

templates = Jinja2Templates(
    directory=str(TEMPLATES_DIR),
)


# ============================================================================
# REQUEST MODELS
# ============================================================================

class ResearchRequest(BaseModel):
    message: str = Field(
        min_length=1,
        description="Research question",
    )

    thread_id: str | None = Field(
        default=None,
        min_length=1,
        description="Existing research thread ID",
    )

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError(
                "Research query cannot be empty."
            )

        return value


class HumanReviewRequest(BaseModel):
    thread_id: str = Field(
        min_length=1,
        description="Research thread ID",
    )

    decision: str = Field(
        min_length=1,
        description="Human review decision",
    )

    feedback: str = Field(
        default="",
        description="Optional human feedback",
    )

    @field_validator("thread_id", "decision")
    @classmethod
    def strip_required_strings(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError(
                "Value cannot be empty."
            )

        return value

    @field_validator("decision")
    @classmethod
    def normalize_decision(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("feedback")
    @classmethod
    def normalize_feedback(cls, value: str) -> str:
        return value.strip()


# ============================================================================
# RESPONSE HELPERS
# ============================================================================

def json_response(
    content: dict,
    status_code: int = 200,
) -> JSONResponse:
    """Create a consistent JSON API response."""
    return JSONResponse(
        status_code=status_code,
        content=content,
    )


def success_response(
    data: dict,
) -> JSONResponse:
    """Create a successful API response."""
    return json_response(
        {
            "success": True,
            **data,
        }
    )


def error_response(
    message: str,
    status_code: int = 500,
) -> JSONResponse:
    """Create a consistent API error response."""
    return json_response(
        {
            "success": False,
            "error": message,
        },
        status_code=status_code,
    )


def sse_event(
    event_type: str,
    **data,
) -> str:
    """
    Build a Server-Sent Events message.

    This is useful for API-level errors because the research service
    already emits SSE events.
    """
    payload = {
        "type": event_type,
        **data,
    }

    return (
        f"data: "
        f"{json.dumps(payload)}"
        f"\n\n"
    )


def streaming_response(
    generator,
) -> StreamingResponse:
    """Create a standardized SSE response."""
    return StreamingResponse(
        generator,
        media_type=SSE_MEDIA_TYPE,
        headers=SSE_HEADERS,
    )


# ============================================================================
# HOME PAGE
# ============================================================================

@app.get(
    "/",
    response_class=HTMLResponse,
)
async def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={},
    )


# ============================================================================
# RESEARCH
# ============================================================================

@app.post("/api/research")
async def research(
    request_data: ResearchRequest,
):
    """
    Run the research workflow and return the final result.

    This endpoint is useful for clients that do not require
    real-time workflow updates.
    """
    try:
        result = await run_research_agent(
            user_input=request_data.message,
            thread_id=request_data.thread_id,
        )

        return success_response(result)

    except ValueError as exc:
        logger.warning(
            "Research validation error: %s",
            exc,
        )

        return error_response(
            str(exc),
            status_code=400,
        )

    except Exception:
        logger.exception(
            "Research request failed."
        )

        return error_response(
            "An unexpected error occurred while processing the research request.",
            status_code=500,
        )


# ============================================================================
# STREAMING RESEARCH
# ============================================================================

@app.post("/api/research/stream")
async def research_stream(
    request_data: ResearchRequest,
):
    """
    Start a research workflow and stream workflow events using SSE.
    """

    async def event_stream():
        try:
            async for event in stream_research_agent(
                user_input=request_data.message,
                thread_id=request_data.thread_id,
            ):
                yield event

        except Exception as exc:
            logger.exception(
                "Research stream failed."
            )

            yield sse_event(
                "error",
                error=str(exc),
            )

    return streaming_response(
        event_stream()
    )


# ============================================================================
# HUMAN REVIEW
# ============================================================================

@app.post("/api/research/review")
async def review_research(
    request_data: HumanReviewRequest,
):
    """
    Resume a paused research workflow after human review.

    The response remains an SSE stream because the workflow may execute
    several additional agents after the review decision.
    """

    decision = request_data.decision

    # ------------------------------------------------------------------------
    # VALIDATE DECISION
    # ------------------------------------------------------------------------

    if decision not in VALID_REVIEW_DECISIONS:
        return error_response(
            (
                "Decision must be one of: "
                "'approve', "
                "'reject', "
                "'request_more_research'."
            ),
            status_code=400,
        )

    # ------------------------------------------------------------------------
    # REJECT REQUIRES FEEDBACK
    # ------------------------------------------------------------------------

    if (
        decision == "reject"
        and not request_data.feedback
    ):
        return error_response(
            "Please provide feedback when rejecting.",
            status_code=400,
        )

    # ------------------------------------------------------------------------
    # STREAM RESUMED WORKFLOW
    # ------------------------------------------------------------------------

    async def event_stream():
        try:
            async for event in resume_research_agent(
                thread_id=request_data.thread_id,
                decision=decision,
                feedback=request_data.feedback,
            ):
                yield event

        except Exception as exc:
            logger.exception(
                "Human review stream failed."
            )

            yield sse_event(
                "error",
                error=str(exc),
            )

    return streaming_response(
        event_stream()
    )


# ============================================================================
# HEALTH CHECK
# ============================================================================

@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "application": (
            "Multi-Agent Research Decision Support System"
        ),
        "features": [
            "input_guardrail",
            "supervisor",
            "research_agent",
            "risk_agent",
            "fact_checker",
            "human_in_the_loop",
            "report_generator",
        ],
    }


# ============================================================================
# FAVICON
# ============================================================================

@app.get("/favicon.ico")
async def favicon():
    return JSONResponse(content={})


# ============================================================================
# APPLICATION ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=HOST,
        port=PORT,
        reload=True,
    )
