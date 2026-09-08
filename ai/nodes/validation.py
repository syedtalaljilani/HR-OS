"""Node 2: CV Validation."""
from ai.prompts import cv_validation
from ai.schemas import CVValidation, ScreeningState, ValidationIssue

from ._util import NodeError, llm_json


def _fallback(state: ScreeningState) -> CVValidation:
    issues: list[ValidationIssue] = []
    profile = state.candidate_profile
    text_len = len(state.cv_text)

    if text_len < 100:
        issues.append(
            ValidationIssue(
                type="INSUFFICIENT_CONTENT",
                description="CV appears to contain too little text to be meaningful",
                severity="HIGH",
            )
        )
    if not (profile and profile.email):
        issues.append(
            ValidationIssue(type="MISSING_EMAIL", description="No email address found in CV")
        )
    if profile is None or not profile.name:
        issues.append(
            ValidationIssue(type="MISSING_NAME", description="Could not extract a candidate name")
        )
    if profile is None or not profile.skills:
        issues.append(
            ValidationIssue(type="MISSING_SKILLS", description="No skills detected in CV")
        )
    if profile is None or not (profile.education or profile.experience):
        issues.append(
            ValidationIssue(
                type="MISSING_EDUCATION_EXPERIENCE",
                description="No education or experience information found",
            )
        )

    return CVValidation(
        valid=len(issues) == 0,
        requires_hr_review=len(issues) > 0,
        issues=issues,
    )


def run(state: ScreeningState) -> dict:
    errors = list(state.errors)
    prompt_versions = dict(state.prompt_versions)
    model = state.model
    profile = state.candidate_profile

    if profile is None:
        errors.append("cv_validation: missing candidate profile")
        return {
            "cv_validation": _fallback(state),
            "errors": errors,
            "prompt_versions": prompt_versions,
            "model": model,
        }

    try:
        raw, prompt_versions, model = llm_json(
            cv_validation.SYSTEM,
            cv_validation.user(state.cv_text, profile),
            prompt_version=cv_validation.PROMPT_VERSION,
            model=model,
            prompt_versions=prompt_versions,
            enabled=state.ai_mode,
        )
        result = CVValidation.model_validate(raw)
    except (NodeError, ValueError):
        errors.append("cv_validation: LLM failed, used deterministic fallback")
        result = _fallback(state)

    return {
        "cv_validation": result,
        "errors": errors,
        "prompt_versions": prompt_versions,
        "model": model,
    }