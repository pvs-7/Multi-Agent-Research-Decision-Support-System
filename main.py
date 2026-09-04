from pathlib import Path
import traceback

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from backend import run_research_agent, resume_research_agent


BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(
    title="Research Decision Support System",
    description=(
        "Multi-Agent Research System with Guardrails, "
        "Fact Checking, Risk Analysis, and Human-in-the-Loop"
    ),
    version="1.0.0",
)


# ==========================================
# STATIC FILES
# ==========================================

app.mount(
    "/static",
    StaticFiles(directory=str(BASE_DIR / "static")),
    name="static",
)

templates = Jinja2Templates(
    directory=str(BASE_DIR / "templates")
)


# ==========================================
# REQUEST MODELS
# ==========================================

class ResearchRequest(BaseModel):
    message: str
    thread_id: str | None = None


class HumanReviewRequest(BaseModel):
    thread_id: str = Field(min_length=1)
    decision: str
    feedback: str = ""


# ==========================================
# HOME PAGE
# ==========================================

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={},
    )


# ==========================================
# START RESEARCH
# ==========================================

@app.post("/api/research")
async def research(request_data: ResearchRequest):
    try:
        user_message = request_data.message.strip()

        if not user_message:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "error": "Research query cannot be empty.",
                },
            )

        result = await run_research_agent(
            user_input=user_message,
            thread_id=request_data.thread_id,
        )

        return JSONResponse(
            content={
                "success": True,
                **result,
            }
        )

    except Exception as exc:
        print("\n❌ RESEARCH ERROR:")
        print(exc)
        traceback.print_exc()

        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(exc),
            },
        )


# ==========================================
# HUMAN REVIEW
# ==========================================

@app.post("/api/research/review")
async def review_research(request_data: HumanReviewRequest):
    try:
        decision = request_data.decision.strip().lower()

        valid_decisions = [
            "approve",
            "reject",
            "request_more_research",
        ]

        if decision not in valid_decisions:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "error": (
                        "Decision must be 'approve', 'reject', "
                        "or 'request_more_research'."
                    ),
                },
            )

        if (
            decision == "reject"
            and not request_data.feedback.strip()
        ):
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "error": (
                        "Please provide feedback when rejecting."
                    ),
                },
            )

        result = await resume_research_agent(
            thread_id=request_data.thread_id,
            decision=decision,
            feedback=request_data.feedback,
        )

        return JSONResponse(
            content={
                "success": True,
                **result,
            }
        )

    except Exception as exc:
        print("\n❌ HUMAN REVIEW ERROR:")
        print(exc)
        traceback.print_exc()

        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(exc),
            },
        )


# ==========================================
# HEALTH CHECK
# ==========================================

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


# ==========================================
# FAVICON
# ==========================================

@app.get("/favicon.ico")
async def favicon():
    return JSONResponse(content={})


# ==========================================
# RUN
# ==========================================

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
    )
