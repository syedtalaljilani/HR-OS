"""LangGraph email-writing workflow.

Single-node graph that drafts a recruitment email (subject + body) for human
review. Used both for pipeline emails and the HR email-writing assistant.
"""
from langgraph.graph import END, START, StateGraph

from ai.nodes.email import run as run_email
from ai.schemas.email_state import EmailAgentState


def build() -> StateGraph:
    builder = StateGraph(EmailAgentState)
    builder.add_node("email", run_email)
    builder.add_edge(START, "email")
    builder.add_edge("email", END)
    return builder


graph = build().compile()
