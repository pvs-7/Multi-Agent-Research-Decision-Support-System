import json

from pydantic import BaseModel
from app.graph.state import Finding
from app.mcp.client import client
from app.graph.state import AgentState
from app.core.llm import llm
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

MAX_SOURCES = 10
MAX_TOOL_CALLS = 4
MAX_TOOL_ROUNDS = 2


class ResearchOutput(BaseModel):
    findings: list[Finding]

research_prompt = """
You are the Research Agent in a multi-agent research system.

Research the user's question using tavily_search.

You have a strict research budget.

Rules:
- Use tavily_search only.
- You have a maximum of 4 searches.
- Usually 2-3 targeted searches are sufficient.
- Do not search again if the existing sources adequately answer
  the question.
- Do not use the same search query repeatedly.
- Prefer academic, government, institutional, and reputable
  industry sources.
- Prefer primary sources over secondary sources.
- Do not invent information.
- Only create findings supported by retrieved sources.
- Do not write the final report.

Research strategy:
1. Start with one broad search to establish the topic.
2. Use subsequent searches only to fill important evidence gaps.
3. Stop searching once you have sufficient evidence across the
   major dimensions of the question.
"""

def compress_tavily_result(result):

    compressed = []

    for item in result:

        if item.get("type") != "text":
            continue

        try:
            data = json.loads(item.get("text", "{}"))
        except json.JSONDecodeError:
            continue

        for tavily_result in data.get("results", []):

            compressed.append({
                "title": tavily_result.get("title", ""),
                "url": tavily_result.get("url", ""),
                "content": tavily_result.get("content", "")[:500],
                "score": tavily_result.get("score")
            })

    return compressed[:5]

async def research_agent(state: AgentState):

    tool_call_count = 0
    tool_round = 0

    print("\n" + "=" * 60)
    print("🔎 RESEARCH AGENT STARTED")
    print("=" * 60)

    print("Query:")
    print(state["user_query"])

    # --------------------------------------------------
    # Get MCP tools
    # --------------------------------------------------

    tools = await client.get_tools()

    print("\n🛠️ MCP TOOLS AVAILABLE:")
    for tool in tools:
        print(f"  - {tool.name}")
    
    search_tool = next(
        tool
        for tool in tools
        if tool.name == "tavily_search"
    )

    llm_with_tools = llm.bind_tools([
        search_tool
    ])

    messages = [
        SystemMessage(content=research_prompt),
        HumanMessage(
            content=f"User Query: {state['user_query']}"
        )
    ]

    research_context = []

    # --------------------------------------------------
    # First LLM call
    # --------------------------------------------------

    print("\n📤 Asking research LLM what to do...")

    response = await llm_with_tools.ainvoke(messages)

    messages.append(response)

    print("\n📥 Research LLM response:")

    print("Content:")
    print(response.content)

    print("\nTool calls:")
    print(response.tool_calls)

    # --------------------------------------------------
    # Tool calling loop
    # --------------------------------------------------

    while response.tool_calls:

        if tool_round >= MAX_TOOL_ROUNDS:
            print("🛑 Maximum tool rounds reached.")
            break

        if tool_call_count >= MAX_TOOL_CALLS:
            print("🛑 Maximum tool calls reached.")
            break

        tool_round += 1

        print(
            f"\n🔄 TOOL ROUND "
            f"{tool_round}/{MAX_TOOL_ROUNDS}"
        )

        tool_results = []

        for tool_call in response.tool_calls:

            if tool_call_count >= MAX_TOOL_CALLS:
                print("🛑 Tool call budget exhausted.")
                break

            tool_call_count += 1

            print(
                f"\n🔧 TOOL CALL "
                f"{tool_call_count}/{MAX_TOOL_CALLS}"
            )

            print("Tool:", tool_call["name"])
            print("Arguments:", tool_call["args"])

            # Since you only bind tavily_search,
            # you can directly use search_tool.
            try:
                print("\n🌐 Calling Tavily MCP...")

                result = await search_tool.ainvoke(
                    tool_call["args"]
                )

            except Exception as e:
                print(f"\n❌ Tavily failed: {e}")

                tool_results.append(
                    ToolMessage(
                        content=json.dumps({
                            "error": "Tavily search failed",
                            "message": str(e)
                        }),
                        tool_call_id=tool_call["id"]
                    )
                )

                continue

            compressed_result = compress_tavily_result(result)

            research_context.extend(compressed_result)

            # Keep only best/first MAX_SOURCES
            research_context = research_context[:MAX_SOURCES]

            print(
                f"\n📚 Total sources collected: "
                f"{len(research_context)}"
            )

            tool_results.append(
                ToolMessage(
                    content=json.dumps(compressed_result),
                    tool_call_id=tool_call["id"]
                )
            )

        messages.extend(tool_results)

        # Don't ask LLM for another round
        # after reaching the budget.
        if tool_call_count >= MAX_TOOL_CALLS:
            print("\n🛑 Tool call budget exhausted.")
            break

        print(
            "\n📤 Sending Tavily results "
            "back to research LLM..."
        )

        response = await llm_with_tools.ainvoke(messages)

        messages.append(response)

        print("\n📥 Research LLM response:")
        print(response.content)

        print("\nAdditional tool calls:")
        print(response.tool_calls)

    # --------------------------------------------------
    # Structured output
    # --------------------------------------------------

    print("\n" + "-" * 60)
    print("🧩 EXTRACTING STRUCTURED FINDINGS")
    print("-" * 60)

    print(
        f"Sending {len(research_context)} sources "
        "to structured-output LLM"
    )

    structured_llm = llm.with_structured_output(
        ResearchOutput
    )

    research_output = await structured_llm.ainvoke([
        SystemMessage(content="""
Extract structured research findings from the provided research results.

Only include claims supported by evidence.

For every finding:
- claim
- evidence
- source_url
- confidence
"""),

        HumanMessage(
            content=json.dumps({
                "user_query": state["user_query"],
                "sources": research_context
            })
        )
    ])

    print("\n📥 STRUCTURED RESEARCH OUTPUT:")
    print(research_output)

    print("\n📊 FINDINGS:")
    for finding in research_output.findings:
        print(f"\nClaim: {finding.claim}")
        print(f"Evidence: {finding.evidence}")
        print(f"Source: {finding.source_url}")
        print(f"Confidence: {finding.confidence}")

    print("\n✅ RESEARCH AGENT FINISHED")

    return {
        "research_findings": research_output.findings,

        "messages": [
            AIMessage(
                content=(
                    f"Research Agent completed research and "
                    f"found {len(research_output.findings)} findings."
                ),
                name="research_agent"
            )
        ]
    }
