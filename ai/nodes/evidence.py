"""Node 5: Evidence Verification."""
from ai.prompts import evidence_verification
from ai.schemas import EvidenceItem, ScreeningState

from ._util import NodeError, llm_json


def _claims_from_matched(state: ScreeningState) -> list[str]:
    """Claims requiring verification, from matched requirements with evidence."""
    claims: list[str] = []
    for m in state.matched_requirements:
        if m.status in ("MATCH", "PARTIAL") and m.evidence:
            claims.append(
                f"{m.requirement} (labelled {m.status}) - evidence: {m.evidence}"
            )
    return claims


def _fallback(state: ScreeningState) -> list[EvidenceItem]:
    """If no evidence was supplied for a claim, mark it unsupported/uncertain."""
    items: list[EvidenceItem] = []
    for m in state.matched_requirements:
        if m.status in ("MATCH", "PARTIAL"):
            items.append(
                EvidenceItem(
                    claim=m.requirement,
                    supported=bool(m.evidence),
                    evidence=m.evidence,
                    reason=(
                        "Evidence provided" if m.evidence
                        else "Keyword present but no supporting evidence found"
                    ),
                )
            )
    return items


def run(state: ScreeningState) -> dict:
    errors = list(state.errors)
    prompt_versions = dict(state.prompt_versions)
    model = state.model

    claims = _claims_from_matched(state)
    if not claims:
        return {
            "evidence_items": [
                EvidenceItem(
                    claim="No positive match claims", supported=True, reason="None claimed"
                )
            ],
            "errors": errors,
            "prompt_versions": prompt_versions,
            "model": model,
        }

    try:
        raw, prompt_versions, model = llm_json(
            evidence_verification.SYSTEM,
            evidence_verification.user(claims, state.cv_text),
            prompt_version=evidence_verification.PROMPT_VERSION,
            model=model,
            prompt_versions=prompt_versions,
            enabled=state.ai_mode,
        )
        claims_out = raw.get("claims")
        if not isinstance(claims_out, list):
            raise NodeError("evidence verification returned no claims")
        items = [EvidenceItem.model_validate(c) for c in claims_out]
    except (NodeError, ValueError):
        errors.append("evidence_verification: LLM failed, used fallback")
        items = _fallback(state)

    return {
        "evidence_items": items,
        "errors": errors,
        "prompt_versions": prompt_versions,
        "model": model,
    }