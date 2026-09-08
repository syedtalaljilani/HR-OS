"""Node 4: Requirement Matching."""
import re

from ai.prompts import requirement_matching
from ai.schemas import MatchStatus, MatchedRequirement, ScreeningState

from ._util import NodeError, llm_json

STOPWORDS = {
    "a", "an", "the", "of", "and", "or", "for", "in", "on", "with",
    "to", "at", "by", "years", "year", "experience", "experience.",
    "using", "knowledge", "plus", "minimum", "strong", "good",
}


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9+#.]+", text.lower()))


def _deterministic(requirement: str, cv_text: str) -> MatchedRequirement:
    req_tokens = _tokenize(requirement) - STOPWORDS
    cv_tokens = _tokenize(cv_text)
    if not req_tokens:
        return MatchedRequirement(
            requirement=requirement, status="UNCLEAR", evidence=None
        )

    hits = req_tokens & cv_tokens
    ratio = len(hits) / len(req_tokens)

    if ratio >= 1.0:
        status: MatchStatus = "MATCH"
    elif ratio >= 0.5:
        status = "PARTIAL"
    else:
        status = "MISSING"

    evidence = None
    for sentence in re.split(r"[.\n]", cv_text):
        lower = sentence.lower()
        if any(t in lower for t in hits):
            evidence = sentence.strip()
            if len(evidence) > 20:
                break
    if evidence and len(evidence) > 300:
        evidence = evidence[:300]

    return MatchedRequirement(
        requirement=requirement, status=status, evidence=evidence
    )


def _is_mandatory(req: str, state: ScreeningState) -> bool:
    reqs = state.job_requirements
    if not reqs:
        return False
    return req in reqs.mandatory or req in reqs.technical_skills


def run(state: ScreeningState) -> dict:
    errors = list(state.errors)
    prompt_versions = dict(state.prompt_versions)
    model = state.model
    reqs_obj = state.job_requirements

    if reqs_obj is None:
        errors.append("requirement_matching: no job requirements available")
        return {
            "matched_requirements": [],
            "errors": errors,
            "prompt_versions": prompt_versions,
            "model": model,
        }

    requirements = reqs_obj.as_flat_list()
    if not requirements:
        requirements = [
            "Relevant skills and qualifications for " + (state.job_title or "the role")
        ]

    try:
        raw, prompt_versions, model = llm_json(
            requirement_matching.SYSTEM,
            requirement_matching.user(requirements, state.cv_text, state.job_title),
            prompt_version=requirement_matching.PROMPT_VERSION,
            model=model,
            prompt_versions=prompt_versions,
            enabled=state.ai_mode,
        )
        items = raw.get("requirements")
        if not isinstance(items, list) or not items:
            raise NodeError("requirement matching returned no items")

        matched: list[MatchedRequirement] = []
        for i, it in enumerate(items):
            req = str(it.get("requirement", "")) or requirements[i]
            status = str(it.get("status", "UNCLEAR")).upper()
            if status not in ("MATCH", "PARTIAL", "MISSING", "UNCLEAR"):
                status = "UNCLEAR"
            matched.append(
                MatchedRequirement(
                    requirement=req,
                    status=status,
                    evidence=it.get("evidence"),
                    is_mandatory=_is_mandatory(req, state),
                )
            )
    except (NodeError, ValueError):
        errors.append("requirement_matching: LLM failed, used deterministic fallback")
        matched = [_deterministic(r, state.cv_text) for r in requirements]
        for m in matched:
            m.is_mandatory = _is_mandatory(m.requirement, state)

    return {
        "matched_requirements": matched,
        "errors": errors,
        "prompt_versions": prompt_versions,
        "model": model,
    }