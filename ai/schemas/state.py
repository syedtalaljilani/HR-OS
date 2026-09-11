"""Shared LangGraph state for the recruitment screening workflow."""
from typing import Annotated, Any

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


def _merge_dicts(a: dict, b: dict) -> dict:
    """Merge concurrent node writes to a dict channel (idempotent)."""
    return {**a, **b}


def _merge_str_lists(a: list[str], b: list[str]) -> list[str]:
    """Union error lists written by concurrent nodes (dedupes, idempotent)."""
    merged: list[str] = []
    for item in (*a, *b):
        if item not in merged:
            merged.append(item)
    return merged


def _latest_value(a: Any, b: Any) -> Any:
    """Keep the most recent non-null value when concurrent nodes write model."""
    return b if b not in (None, "") else a


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
    # Reducers make the shared channels accept concurrent writes from the
    # parallel screening branches (extraction||requirements, validation||
    # matching, evidence||uncertainty). All are idempotent.
    errors: Annotated[list[str], _merge_str_lists] = Field(default_factory=list)
    prompt_versions: Annotated[dict[str, str], _merge_dicts] = Field(
        default_factory=dict
    )
    model: Annotated[str | None, _latest_value] = None
    # Optional separate (smaller/faster) model for CV extraction while the
    # evaluation-model runs the screening "brain" nodes.
    profile_model: str | None = None
    requires_hr_review: bool = False

    def as_plain(self) -> dict[str, Any]:
        return self.model_dump(exclude_none=True)
