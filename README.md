# Multi-Agent Research Decision Support System

An async FastAPI application that runs a LangGraph research workflow. A submitted question is checked for relevance and safety, researched with Tavily, analyzed for risks, fact checked, optionally reviewed by a person, and used to generate a final report.

## UI Preview

The browser interface provides live workflow updates and presents the research results, risks, verification status, human-review steps, and final report in one place.

| Research progress | Research findings |
| --- | --- |
| ![Research progress and status](images/research%20and%20status.png) | ![Research findings](images/research%20findings.png) |

| Risks and trade-offs | Fact checking and human review |
| --- | --- |
| ![Risks](images/risks.png) | ![Fact checking and human-in-the-loop review](images/fact%20checking%20and%20hitl.png) |

| Input guardrails | Generated report |
| --- | --- |
| ![Input guardrails](images/guardrails.png) | ![Generated report](images/report.png) |

## How It Works

The workflow is defined in `app/graph/workflow.py`:

1. `input_guardrail` classifies the request with a local Ollama model. Only requests classified as relevant continue.
2. `supervisor` chooses the next workflow node.
3. `research_agent` uses the Tavily MCP server to search for evidence. It can run up to three research passes and makes at most four tool calls per pass.
4. `risk_agent` identifies evidence-supported risks, limitations, trade-offs, and uncertainties.
5. `fact_checker_agent` marks findings and risks as `verified`, `unverified`, or `conflicting`.
6. Unverified or conflicting claims are packaged for human review. The graph pauses until the review is submitted.
7. `report_generator` creates a Markdown report from the findings, risks, and verification results.

LangGraph state is persisted with `AsyncPostgresSaver`. Each request receives a thread ID, which is also used to resume a paused human-review workflow.

## Requirements

- Python 3.13 or newer (`.python-version` and `pyproject.toml` specify 3.13).
- A PostgreSQL database reachable through `DATABASE_URL`.
- A Groq API key for the research and report model.
- Ollama running locally at `http://localhost:11434` with the `ministral-3:3b` model available.
- A Tavily API key. The application passes it to the Tavily MCP endpoint.

The project declares its Python dependencies in `pyproject.toml` and `requirements.txt`. `uv.lock` is also checked in and contains the resolved dependency set.

## Configuration

Create a `.env` file in the project root. The application calls `load_dotenv()` and reads these variables:

```dotenv
DATABASE_URL=postgresql://user:password@host:5432/database
GROQ_API_KEY=your-groq-api-key
TAVILY_API_KEY=your-tavily-api-key
```

`DATABASE_URL` is modified at runtime to add `sslmode=require` when no `sslmode` parameter is present. Keep `.env` private; it is excluded by `.gitignore`.

The active model configuration is:

- Groq: `openai/gpt-oss-120b`, temperature `0`, used for research tool calls and report generation.
- Ollama: `ministral-3:3b`, temperature `0`, context size `32768`, used for the guardrail, risk analysis, and fact checking.
- Tavily MCP: `https://mcp.tavily.com/mcp/` with the API key added as a query parameter.

A Gemini configuration is present but commented out in `app/core/llm.py`; it is not part of the active runtime path.

## Installation

From the project root, create or activate a Python 3.13+ environment and install the declared requirements:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

The repository also contains `pyproject.toml` and `uv.lock` for uv-based environments:

```powershell
uv sync
```

Before starting the application, make sure PostgreSQL is reachable, Ollama is running with `ministral-3:3b`, and the values in `.env` are set.

## Run the Web Application

Start the development server with:

```powershell
python main.py
```

This starts Uvicorn with reload enabled at [http://127.0.0.1:8000](http://127.0.0.1:8000). The browser interface is served at `/`.

The server also exposes:

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/` | Serves the Jinja-rendered browser UI. |
| `GET` | `/health` | Returns the application status and workflow feature names. |
| `POST` | `/api/research` | Runs a research request and returns one JSON response. |
| `POST` | `/api/research/stream` | Runs a research request and streams Server-Sent Events. This is the endpoint used by the browser UI. |
| `POST` | `/api/research/review` | Resumes a paused workflow and streams its events. |

### Research request

The research endpoints accept JSON with a required `message` and an optional `thread_id`:

```json
{
	"message": "What are the risks and benefits of adopting AI in healthcare?",
	"thread_id": null
}
```

An empty message returns HTTP 400. When no thread ID is supplied, the backend creates one with the `research_` prefix.

The streaming endpoints return `text/event-stream` data. Events include `agent_started`, `agent_update`, `workflow_status`, `human_review_required`, and `complete`; failures are emitted as `error` events by the review stream.

### Human review request

When fact checking finds conflicting or unverified claims, the graph pauses and the client can resume it with:

```json
{
	"thread_id": "research_<thread-id>",
	"decision": "approve",
	"feedback": ""
}
```

Valid decisions are `approve`, `reject`, and `request_more_research`. A rejection requires non-empty feedback. A request for more research can trigger another research pass until the configured research-pass limit is reached.


The harness uses the same PostgreSQL checkpointer and can resume the same thread after each review decision.

## Project Layout

```text
main.py                    FastAPI application and HTTP routes
backend.py                 Graph compilation, request execution, serialization, and SSE events
app/graph/state.py         Typed workflow state and Pydantic result models
app/graph/workflow.py      LangGraph nodes and routing edges
app/agents/                Supervisor, research, risk, fact-check, and report agents
app/core/database.py       PostgreSQL connection pool and LangGraph checkpointer setup
app/core/llm.py            Active Groq and Ollama model configuration
app/mcp/client.py          Tavily MCP client configuration
app/guardrails/             Input relevance and safety guardrail
app/hitl/                   LangGraph human-review interrupt
templates/index.html       Browser UI markup
static/app.js              Browser requests, SSE handling, and result rendering
static/style.css            Browser UI styles
test_graph.py              Interactive workflow harness
pyproject.toml              Project metadata and dependency declarations
requirements.txt            Pip dependency list
uv.lock                    Resolved uv dependency lockfile
```

## Notes

- Research and report generation depend on external Groq and Tavily services.
- Guardrail, risk, and fact-check stages depend on the local Ollama server and model named above.
- The database checkpointer is initialized lazily on the first research request.
- There are no automated tests defined in the repository.
- The frontend uses the CDN-hosted `marked` library to render the final Markdown report.

## License

This project is licensed under the Apache License 2.0. See [LICENSE](LICENSE).
