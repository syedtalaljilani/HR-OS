"""LangGraph job-posting assistant workflow.

A minimal single-node graph that takes a job title + user note/prompt and
produces a draft job description and requirements for human review.
"""
from langgraph.graph import END, START, StateGraph

from ai.nodes.job_assistant import run as run_job_assistant
from ai.schemas.job_state import JobAssistantState


def build() -> StateGraph:
    builder = StateGraph(JobAssistantState)
    builder.add_node("job_assistant", run_job_assistant)
    builder.add_edge(START, "job_assistant")
    builder.add_edge("job_assistant", END)
    return builder


graph = build().compile()
