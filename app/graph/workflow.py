from dotenv import load_dotenv

load_dotenv()

from langgraph.graph import StateGraph, START, END

from app.graph.state import AgentState
from app.agents.supervisor import supervisor_agent, route_supervisor
from app.agents.research_agent import research_agent
from app.agents.report_generator import report_generator
from app.agents.risk_agent import risk_agent
from app.agents.fact_checker import fact_checker_agent
from app.guardrails.input_guardrails import input_guardrail, route_input_guardrail
from app.hitl.human_review import human_review

graph = StateGraph(AgentState)

graph.add_node("input_guardrail", input_guardrail)
graph.add_node("supervisor", supervisor_agent)
graph.add_node("research_agent", research_agent)
graph.add_node("report_generator", report_generator)
graph.add_node("fact_checker_agent", fact_checker_agent)
graph.add_node("risk_agent", risk_agent)
graph.add_node("human_review", human_review)

graph.add_edge(START, "input_guardrail")

graph.add_conditional_edges(
    "input_guardrail",
    route_input_guardrail,
    {
        "supervisor": "supervisor",
        "rejected": END
    })

graph.add_conditional_edges(
    "supervisor",
    route_supervisor,
    {
        "research_agent": "research_agent",
        "risk_agent": "risk_agent",
        "fact_checker_agent": "fact_checker_agent",
        "report_generator": "report_generator",
        "human_review": "human_review"
    }
)

graph.add_edge("research_agent", "supervisor")
graph.add_edge("risk_agent", "supervisor")
graph.add_edge("fact_checker_agent", "supervisor")
graph.add_edge("human_review","supervisor")
graph.add_edge("report_generator", END)

