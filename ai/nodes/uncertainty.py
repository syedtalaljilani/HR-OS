"""Node 6: Uncertainty Detection."""
from ai.prompts import uncertainty
from ai.schemas import ScreeningState, UncertaintyItem, UncertaintyResult

from ._util import NodeError, llm_json


def _fallback(state: ScreeningState) -> UncertaintyResult:
    items: list[UncertaintyItem] = []
    for m in state.matched_requirements:
        if m.status == "UNCLEAR":
            items.append(
                UncertaintyItem(
                    issue=f"Cannot reliably determine: {m.requirement}",
                    impact="MEDIUM",
                    requires_hr_review=True,
                )
            )
    if state.cv_validation and state.cv_validation.uncertainties:
        for u in state.cv_validation.uncertainties:
            items.append(
                UncertaintyItem(issue=u, impact="MEDIUM", requires_hr_review=True)
            )
    overall = "HIGH" if items else "LOW"
    return UncertaintyResult(uncertainties=items, overall_uncertainty=overall)


def run(state: ScreeningState) -> dict:
    errors = list(state.errors)
    prompt_versions = dict(state.prompt_versions)
    model = state.model

    try:
        raw, prompt_versions, model = llm_json(
            uncertainty.SYSTEM,
            uncertainty.user(
                state.cv_text,
                state.candidate_profile,
                [m.model_dump() for m in state.matched_requirements],
            ),
            prompt_version=uncertainty.PROMPT_VERSION,
            model=model,
            prompt_versions=prompt_versions,
            enabled=state.ai_mode,
        )
        result = UncertaintyResult.model_validate(raw)
    except (NodeError, ValueError):
        errors.append("uncertainty: LLM failed, used fallback")
        result = _fallback(state)

    return {
        "uncertainties": result.uncertainties,
        "errors": errors,
        "prompt_versions": prompt_versions,
        "model": model,
    }