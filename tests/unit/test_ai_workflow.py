"""Unit tests for the LangGraph AI screening workflow.

Deterministic-path tests run without any infrastructure.
Ollama-path tests are skipped when Ollama is unavailable.
"""
import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ai.graphs.screening import graph
from ai.ollama import is_available
from ai.schemas import ScreeningState

TEST_CV = """Ali Khan
ali@example.com

PROFILE
Senior Software Engineer with 5+ years of professional experience in Python development.

SKILLS
Python, FastAPI, PostgreSQL, Docker, Kubernetes, Redis, Machine Learning, REST API, Git, AWS

EXPERIENCE
Senior Python Developer - TechCorp (2021-2025)
Led backend development of high-traffic APIs using FastAPI and PostgreSQL.
Built CI/CD pipelines with Docker and Kubernetes.

Software Engineer - DevSoft (2019-2021)
Developed REST APIs and data pipelines using Python, SQL and Redis.

EDUCATION
Bachelor of Science in Computer Science - University of Engineering and Technology Lahore (2015-2019)

CERTIFICATIONS
AWS Certified Solutions Architect
"""

JOB = (
    "Senior Python Developer\n\nRequirements:\n"
    "- 3+ years of Python\n- FastAPI\n- PostgreSQL\n- Docker\n- Kubernetes\n"
    "- Bachelor degree in Computer Science\n- AWS\n"
)

NODE_ORDER = [
    "extraction",
    "validation",
    "requirements",
    "matching",
    "evidence",
    "uncertainty",
    "recommendation",
]


def _state(**overrides) -> ScreeningState:
    base = dict(
        cv_text=TEST_CV,
        job_title="Senior Python Developer",
        job_description=JOB,
        application_id="APP-2026-00421",
        candidate_id="CAND-0001",
    )
    base.update(overrides)
    return ScreeningState(**base)


def test_graph_executes_all_nodes_deterministic():
    """The full pipeline runs and every node contributes output (no Ollama)."""
    result = graph.invoke(_state(ai_mode=False).as_plain())

    assert result["candidate_profile"] is not None
    assert result["candidate_profile"].email == "ali@example.com"
    assert len(result["candidate_profile"].skills) > 0
    assert result["cv_validation"] is not None
    assert result["job_requirements"] is not None
    assert result["matched_requirements"], "matching produced no results"
    assert result["recommendation"] is not None
    assert result["recommendation"].recommendation in (
        "MATCH",
        "PARTIAL",
        "MISSING",
        "UNCLEAR",
    )
    assert 0 <= result["recommendation"].score <= 100


def test_recommendation_is_never_final_decision():
    """AI must never emit SELECTED / REJECTED."""
    result = graph.invoke(_state(ai_mode=False).as_plain())
    assert result["recommendation"].recommendation not in ("SELECTED", "REJECTED")


def test_extraction_structured_profile():
    result = graph.invoke(_state(ai_mode=False).as_plain())
    profile = result["candidate_profile"]
    assert profile.name == "Ali Khan"
    assert "@" in profile.email
    assert any("python".lower() in s.lower() for s in profile.skills)


def test_deterministic_missing_requirement_detects_gap():
    """A CV that lacks a required skill should classify that requirement MISSING/PARTIAL (not MATCH)."""
    weak_cv = TEST_CV.replace(
        "SKILLS\nPython, FastAPI, PostgreSQL, Docker, Kubernetes, Redis, Machine Learning, REST API, Git, AWS",
        "SKILLS\nHTML\nCSS",
    )
    result = graph.invoke(
        _state(cv_text=weak_cv, ai_mode=False).as_plain()
    )
    statuses = {m.requirement: m.status for m in result["matched_requirements"]}
    assert any(
        s in ("MISSING", "PARTIAL") for s in statuses.values()
    ), f"expected missing/partial, got {statuses}"


def test_uncertainty_sets_hr_review_flag():
    """When ambiguity exists, the workflow must request HR review."""
    result = graph.invoke(_state(ai_mode=False).as_plain())
    assert result["requires_hr_review"] is True


@pytest.mark.skipif(not is_available(), reason="Ollama not running")
def test_ai_mode_screen():
    """Full AI-mode run against a live Ollama model."""
    result = graph.invoke(_state(ai_mode=True).as_plain())

    assert result["recommendation"] is not None
    assert result["recommendation"].recommendation in (
        "MATCH",
        "PARTIAL",
        "MISSING",
        "UNCLEAR",
    )
    assert result["model"], "model metadata should be recorded"
    assert result["prompt_versions"], "prompt versions should be recorded"
    assert len(result["matched_requirements"]) > 0


@pytest.mark.skipif(not is_available(), reason="Ollama not running")
def test_ai_mode_metadata_traceable():
    """Model + prompt versions must be present for evaluation/regression."""
    result = graph.invoke(_state(ai_mode=True).as_plain())
    for key in ("cv", "job", "requirement", "evidence", "uncertainty", "screening"):
        assert result["prompt_versions"].get(key), f"missing prompt version key: {key}"