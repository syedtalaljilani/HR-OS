"""Builds and exposes the compiled screening LangGraph."""
from langgraph.graph import END, START, StateGraph

from ai.nodes import (
    run_evidence,
    run_extraction,
    run_matching,
    run_recommendation,
    run_requirements,
    run_uncertainty,
    run_validation,
)
from ai.schemas import ScreeningState


def build() -> StateGraph:
    builder = StateGraph(ScreeningState)

    builder.add_node("extraction", run_extraction)
    builder.add_node("validation", run_validation)
    builder.add_node("requirements", run_requirements)
    builder.add_node("matching", run_matching)
    builder.add_node("evidence", run_evidence)
    builder.add_node("uncertainty", run_uncertainty)
    builder.add_node("recommendation", run_recommendation)

    builder.add_edge(START, "extraction")
    builder.add_edge("extraction", "validation")
    builder.add_edge("validation", "requirements")
    builder.add_edge("requirements", "matching")
    builder.add_edge("matching", "evidence")
    builder.add_edge("evidence", "uncertainty")
    builder.add_edge("uncertainty", "recommendation")
    builder.add_edge("recommendation", END)

    return builder


graph = build().compile()