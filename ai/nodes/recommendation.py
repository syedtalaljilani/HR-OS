"""Node 7: Screening Recommendation."""
from ai.prompts import recommendation
from ai.schemas import MatchStatus, ScreeningRecommendation, ScreeningState

from ._util import NodeError, llm_json


def _compute_score(matched) -> int:
    if not matched:
        return 0
    total = 0
    for m in matched:
        if m.status == "MATCH":
            total += 100
        elif m.status == "PARTIAL":
            total += 50
    return int(total / len(matched))


def _deterministic(state: ScreeningState) -> ScreeningRecommendation:
    matched = state.matched_requirements
    score = _compute_score(matched)

    if score >= 70:
        rec: MatchStatus = "MATCH"
    elif score >= 40:
        rec = "PARTIAL"
    elif score > 0:
        rec = "MISSING"
    else:
        rec = "UNCLEAR"

    # Mandatory requirement rule must never be overridden by overall strength.
    missing_mandatory = [m for m in matched if m.is_mandatory and m.status == "MISSING"]
    if missing_mandatory and rec == "MATCH":
        rec = "PARTIAL"

    missing = [m.requirement for m in matched if m.status == "MISSING"]
    matched_list = [m.requirement for m in matched if m.status == "MATCH"]
    unc = [m.requirement for m in matched if m.status == "UNCLEAR"]

    return ScreeningRecommendation(
        recommendation=rec,
        score=score,
        reason="Deterministic recommendation from requirement matching",
        matched_requirements=matched_list,
        missing_requirements=missing,
        uncertainties=unc,
        requires_hr_review=state.requires_hr_review or bool(unc),
    )


def _str_list(value) -> list[str]:
    """Coerce list[str] or list[dict] (with 'issue'/'requirement') to list[str]."""
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for item in value:
        if isinstance(item, str):
            out.append(item)
        elif isinstance(item, dict):
            for key in ("issue", "requirement", "uncertainty"):
                if isinstance(item.get(key), str):
                    out.append(item[key])
                    break
    return out


def _normalize(raw: dict) -> dict:
    for key in ("uncertainties", "matched_requirements", "missing_requirements"):
        if key in raw:
            raw[key] = _str_list(raw.get(key))
    return raw


def run(state: ScreeningState) -> dict:
    errors = list(state.errors)
    prompt_versions = dict(state.prompt_versions)
    model = state.model

    try:
        raw, prompt_versions, model = llm_json(
            recommendation.SYSTEM,
            recommendation.user(
                [m.model_dump() for m in state.matched_requirements],
                [e.model_dump() for e in state.evidence_items],
                [u.model_dump() for u in state.uncertainties],
                state.cv_text,
            ),
            prompt_version=recommendation.PROMPT_VERSION,
            model=model,
            prompt_versions=prompt_versions,
            enabled=state.ai_mode,
        )
        result = ScreeningRecommendation.model_validate(_normalize(raw))

        # Guard against LLM score unreliability: if the model returns a score of 0
        # even though requirement evidence clearly contains matches, fall back to
        # the deterministic aggregate score. This keeps screening scores stable so
        # automation (auto-reject / ranking) never mis-fires on a strong profile
        # just because the chat model returned a bad number.
        det = _deterministic(state)
        if result.score == 0 and det.score > 0:
            result = ScreeningRecommendation(
                recommendation=det.recommendation,
                score=det.score,
                reason=result.reason or det.reason,
                matched_requirements=result.matched_requirements
                or det.matched_requirements,
                missing_requirements=result.missing_requirements
                or det.missing_requirements,
                uncertainties=result.uncertainties or det.uncertainties,
                requires_hr_review=(
                    result.requires_hr_review
                    or det.requires_hr_review
                    or bool(result.uncertainties)
                ),
            )
    except (NodeError, ValueError) as e:
        errors.append(
            f"recommendation: LLM failed, used deterministic fallback "
            f"({type(e).__name__}: {str(e)[:120]})"
        )
        result = _deterministic(state)

    hr_review = (
        result.requires_hr_review
        or (state.cv_validation.requires_hr_review if state.cv_validation else False)
        or bool(state.uncertainties)
        or bool(errors)
    )
    return {
        "recommendation": result,
        "errors": errors,
        "prompt_versions": prompt_versions,
        "model": model,
        "requires_hr_review": hr_review,
    }