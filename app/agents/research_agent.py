import json
from pydantic import BaseModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from app.graph.state import Finding, AgentState
from app.mcp.client import client
from app.core.llm import llm, llm2

MAX_TOOL_CALLS_PER_PASS = 4
MAX_RESULTS_PER_SEARCH = 3
MAX_PLANNING_SOURCES = 5
MAX_CONTEXT_SOURCES = 8


class ResearchOutput(BaseModel):
    findings: list[Finding]
    research_complete: bool
    missing_information: list[str]


research_prompt = """
You are the Research Agent in a multi-agent research system.

Your job is to gather reliable evidence needed to answer
the user's question.

You may be called multiple times as the workflow gathers
additional evidence.

============================================================
TOOL USAGE
============================================================

You may ONLY use the `tavily_search` tool.

Every tavily_search call MUST include:

- query: a non-empty string containing the search query

Optional parameters include:

- max_results
- search_depth
- include_raw_content
- time_range
- include_domains
- exclude_domains
- country

IMPORTANT:

- Never call tavily_search without a `query`.
- Never use parameters named `cursor`.
- Never use parameters named `id`.
- Never invent tool parameters.
- Only use parameters supported by the tavily_search schema.
- Formulate the search query before calling the tool.

Example valid search query:

"electric vehicle battery supply chain bottlenecks"

============================================================
FIRST RESEARCH PASS
============================================================

- Identify the major dimensions of the user's question.
- Perform one broad search to understand the topic.
- Perform targeted searches for important dimensions.
- Build a reliable evidence base.

============================================================
FOLLOW-UP RESEARCH PASS
============================================================

Inspect:

- existing findings
- identified risks
- missing information
- research requests
- previous searches

Identify weak, unsupported, or missing evidence.

Search ONLY for evidence gaps.

Do NOT repeat previous searches.

Prioritize explicit research requests from the Fact Checker.

============================================================
FACT CHECKER RESEARCH REQUESTS
============================================================

research_requests are explicit evidence gaps identified by
the Fact Checker.

Treat these as high-priority research tasks.

For each request:

- Identify the actual evidence needed.
- Create a specific search query.
- Search for authoritative sources that directly address
  the evidence gap.

Do not simply repeat the wording of the research request.

============================================================
SEARCH STRATEGY
============================================================

- Cover all important dimensions of the user's question.
- Prefer authoritative and primary sources.
- Use government sources when relevant.
- Use academic research when relevant.
- Use official organizations and reputable institutions.
- Use different searches for different evidence gaps.
- Avoid redundant searches.

============================================================
RULES
============================================================

- Use tavily_search only.
- Maximum 4 searches per invocation.
- Do not repeat previous queries.
- Do not perform unnecessary searches.
- Do not invent information.
- Only create findings supported by search results.
- Do not write the final report.
- Do not claim research is complete if important evidence
  gaps remain.

============================================================
COMPLETION
============================================================

Research is complete only when the available evidence
sufficiently covers the important dimensions of the question.

If important evidence is missing:

research_complete = false

missing_information = a list of specific evidence gaps.

If evidence is sufficient:

research_complete = true

missing_information = []

During follow-up research prioritize:

1. research_requests from the Fact Checker
2. missing_information
3. weakly supported dimensions
4. risks identified by the Risk Agent
5. important dimensions without evidence
"""


def compress_tavily_result(result):
    sources = []
    for item in result:
        if item.get("type") != "text":
            continue
        try:
            data = json.loads(item.get("text", "{}"))
        except json.JSONDecodeError:
            continue
        for r in data.get("results", []):
            sources.append({
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "content": r.get("content", "")[:600],
                "score": r.get("score", 0)
            })
    return sources[:MAX_RESULTS_PER_SEARCH]


def add_sources(existing, new_sources):
    existing_urls = {s.get("url") for s in existing}
    for source in new_sources:
        url = source.get("url")
        if url and url not in existing_urls:
            existing.append(source)
            existing_urls.add(url)
    return existing


def select_sources(sources, limit):
    if len(sources) <= limit:
        return list(sources)
    return sorted(
        sources,
        key=lambda s: s.get("score") or 0,
        reverse=True
    )[:limit]


def merge_findings(existing, new):
    merged = list(existing)
    claims = {f.claim.strip().lower() for f in merged}

    for finding in new:
        claim = finding.claim.strip().lower()
        if claim not in claims:
            merged.append(finding)
            claims.add(claim)

    return merged

def compact_findings(findings, limit=6):
    return [
        {
            "claim": f.claim[:300],
            "confidence": f.confidence
        }
        for f in findings[-limit:]
    ]


async def research_agent(state: AgentState):
    workflow_steps = state.get("workflow_steps", 0) + 1
    research_passes = state.get("research_passes", 0) + 1
    tool_call_count = 0

    print("\n" + "=" * 60)
    print("🔎 RESEARCH AGENT STARTED")
    print("=" * 60)
    print(f"Research pass: {research_passes}")
    print("Query:", state["user_query"])

    existing_findings = [
        f.model_dump() for f in state.get("research_findings", [])
    ]
    existing_risks = [
        r.model_dump() for r in state.get("risks", [])
    ]
    existing_sources = list(state.get("research_sources", []))
    existing_queries = list(state.get("research_queries", []))
    missing_information = list(state.get("missing_information", []))
    research_requests = list(state.get("research_requests", []))

    print(f"\n📚 Existing findings: {len(existing_findings)}")
    print(f"⚠️ Existing risks: {len(existing_risks)}")
    print(f"📄 Existing sources: {len(existing_sources)}")
    print(f"🔎 Previous searches: {len(existing_queries)}")
    print(f"❓ Missing information: {missing_information}")
    print(f"🎯 Research requests: {research_requests}")

    tools = await client.get_tools()
    for tool in tools:
        print("\n" + "=" * 60)
        print("NAME:", tool.name)
        print("DESCRIPTION:", tool.description)
        print("ARGS SCHEMA:", tool.args_schema)
    search_tool = next(t for t in tools if t.name == "tavily_search")
    llm_with_tools = llm.bind_tools([search_tool])

    research_context = list(existing_sources)

    planning_context = {
        "user_query": state["user_query"],
        "research_pass": research_passes,
        "existing_findings": compact_findings(
        state.get("research_findings", []),
        6
    ),
        "existing_risks": existing_risks,
        "missing_information": missing_information,
        "research_requests": research_requests,
        "previous_search_queries": existing_queries,
    }

    messages = [
        SystemMessage(content=research_prompt),
        HumanMessage(content=json.dumps(planning_context))
    ]

    print("\n📤 Asking research LLM what to do...")
    response = await llm_with_tools.ainvoke(messages)
    messages.append(response)

    print("\n📥 Research LLM response:")
    print("Content:", response.content)
    print("Tool calls:", response.tool_calls)

    while response.tool_calls and tool_call_count < MAX_TOOL_CALLS_PER_PASS:
        tool_results = []

        for tool_call in response.tool_calls:
            if tool_call_count >= MAX_TOOL_CALLS_PER_PASS:
                break

            tool_call_count += 1
            args = tool_call["args"]

            print(
                f"\n🔧 TOOL CALL "
                f"{tool_call_count}/{MAX_TOOL_CALLS_PER_PASS}"
            )
            print("Tool:", tool_call["name"])
            print("Arguments:", args)

            query = args.get("query")
            if query:
                normalized = query.strip().lower()
                previous = {q.strip().lower() for q in existing_queries}
                if normalized in previous:
                    print("⚠️ Duplicate query skipped.")
                    continue
                existing_queries.append(query)

            try:
                print("\n🌐 Calling Tavily MCP...")
                result = await search_tool.ainvoke(args)
                compressed = compress_tavily_result(result)
                research_context = add_sources(
                    research_context,
                    compressed
                )
            except Exception as e:
                print(f"\n❌ Tavily failed: {e}")
                compressed = [{
                    "error": "Tavily search failed",
                    "message": str(e)
                }]

            print(
                f"📚 Total sources collected: "
                f"{len(research_context)}"
            )

            tool_results.append(
                ToolMessage(
                    content=json.dumps(compressed),
                    tool_call_id=tool_call["id"]
                )
            )

        messages.extend(tool_results)

        if tool_call_count >= MAX_TOOL_CALLS_PER_PASS:
            print("\n🛑 Tool call budget exhausted.")
            break

        print("\n📤 Sending Tavily results back to research LLM...")
        response = await llm_with_tools.ainvoke(messages)
        messages.append(response)

        print("\n📥 Research LLM response:")
        print("Content:", response.content)
        print("Additional tool calls:", response.tool_calls)

    print("\n" + "-" * 60)
    print("🧩 EXTRACTING STRUCTURED FINDINGS")
    print("-" * 60)

    llm_sources = select_sources(
        research_context,
        MAX_CONTEXT_SOURCES
    )

    structured_prompt = """
Extract the research findings from the supplied sources.

Return only findings that are directly supported by the sources.

For each finding:
- claim: factual claim
- evidence: concise supporting evidence
- source_url: supporting URL
- confidence: number from 0 to 1

Also determine whether the research is complete.

Re-evaluate the previous missing_information list.

Remove a missing-information item if the supplied evidence now resolves it.

Keep an item only if important evidence is still missing.

If new important evidence gaps exist, add them.

If all important evidence gaps are resolved:
research_complete = true
missing_information = []

Otherwise:
research_complete = false
missing_information = [remaining specific evidence gaps]

Do not invent facts.
Do not return JSON as strings.
"""

    structured_input = {
        "user_query": state["user_query"],
        "previous_findings": compact_findings(
        state.get("research_findings", []),
        6
        ),
        "previous_risks": existing_risks,
        "previous_missing_information": missing_information[:5],
        "sources": [
        {
            "title": s["title"],
            "url": s["url"],
            "content": s["content"][:600]
        }
        for s in llm_sources[:8]
    ]
    }

    print("\n📤 Sending sources to structured LLM...")
    print(f"Sources sent: {len(llm_sources)}")

    structured_llm = llm2.with_structured_output(ResearchOutput, method="json_schema")

    research_output = await structured_llm.ainvoke([
        SystemMessage(content=structured_prompt),
        HumanMessage(content=json.dumps(structured_input))
    ])

    merged_findings = merge_findings(
        state.get("research_findings", []),
        research_output.findings
    )

    research_complete = (
        research_output.research_complete
    )

    needs_more_research = (
        not research_complete
    )

    print("\n📥 RESEARCH OUTPUT:")
    print(
        f"Research pass: "
        f"{research_passes}"
    )

    print(
        f"New findings: "
        f"{len(research_output.findings)}"
    )

    print(
        f"Total findings: "
        f"{len(merged_findings)}"
    )

    print(
        f"Research complete: "
        f"{research_complete}"
    )

    print(
        f"Missing information: "
        f"{research_output.missing_information}"
    )

    return {
        "research_findings": merged_findings,
        "research_sources": research_context,
        "research_queries": existing_queries,
        # New research invalidates previous downstream analysis
        "risk_analysis_complete": False,
        "fact_check_complete": False,
        "needs_more_research":  needs_more_research,
        "research_complete": research_output.research_complete,
        "missing_information": research_output.missing_information,
        "research_passes": research_passes,
        "research_requests" : research_output.missing_information,
        "completed_agents": ["research_agent"],
        "workflow_steps": workflow_steps,
        "messages": [
            AIMessage(
                content=(
                    "Research Agent completed "
                    f"research pass "
                    f"{research_passes} and found "
                    f"{len(research_output.findings)} "
                    "new findings."
                ),
                name="research_agent"
            )
        ]
    }