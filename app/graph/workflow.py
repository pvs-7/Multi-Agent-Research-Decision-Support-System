from langgraph.graph import StateGraph, START, END
from app.graph.state import AgentState
from app.agents.supervisor import supervisor_agent, route_supervisor
from app.agents.research_agent import research_agent
from app.agents.report_generator import report_generator

graph = StateGraph(AgentState)

graph.add_node("supervisor", supervisor_agent)
graph.add_node("research_agent", research_agent)
graph.add_node("report_generator", report_generator)

graph.add_edge(START, "supervisor")

graph.add_conditional_edges(
    "supervisor",
    route_supervisor,
    {
        "research_agent": "research_agent",
        "report_generator": "report_generator"
    }
)

graph.add_edge("research_agent", "supervisor")
graph.add_edge("report_generator", END)

test = graph.compile()