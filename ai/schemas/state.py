"""Shared LangGraph state for the recruitment screening workflow."""
from typing import Any

from pydantic import BaseModel, Field

from .types import (
    CandidateProfile,
    CVValidation,
    EvidenceItem,
    JobRequirements,
    MatchedRequirement,
    ScreeningRecommendation,
    UncertaintyItem,
)


class ScreeningState(BaseModel):
    """State carried through the LangGraph screening workflow.

    Mirrors the `RecruitmentState` from docs/architecture/ai-workflow.md.
    """

    # Inputs
    cv_text: str
    job_title: str | None = None
    job_description: str | None = None
    candidate_id: str | None = None
    application_id: str | None = None

    # Node outputs
    candidate_profile: CandidateProfile | None = None
    cv_validation: CVValidation | None = None
    job_requirements: JobRequirements | None = None
    matched_requirements: list[MatchedRequirement] = Field(default_factory=list)
    evidence_items: list[EvidenceItem] = Field(default_factory=list)
    uncertainties: list[UncertaintyItem] = Field(default_factory=list)
    recommendation: ScreeningRecommendation | None = None

    # Workflow control
    ai_mode: bool = True
    errors: list[str] = Field(default_factory=list)
    prompt_versions: dict[str, str] = Field(default_factory=dict)
    model: str | None = None
    requires_hr_review: bool = False

    def as_plain(self) -> dict[str, Any]:
        return self.model_dump(exclude_none=True)
