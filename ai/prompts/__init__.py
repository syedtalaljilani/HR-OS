"""Prompt templates for AI nodes.

System prompts are defined per node and versioned. Each exports a
SYSTEM prompt string and a PROMPT_VERSION string used for evaluation and
regression tracking (docs/architecture/evaluation.md).
"""
from . import (
    cv_extraction,
    cv_validation,
    evidence_verification,
    job_requirements,
    recommendation,
    requirement_matching,
    uncertainty,
)

__all__ = [
    "cv_extraction",
    "cv_validation",
    "evidence_verification",
    "job_requirements",
    "recommendation",
    "requirement_matching",
    "uncertainty",
]
