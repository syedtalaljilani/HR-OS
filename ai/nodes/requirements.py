"""Node 4a: Job Requirement Extraction."""
from ai.prompts import job_requirements
from ai.schemas import JobRequirements, ScreeningState

from ._util import NodeError, llm_json


def _from_title(title: str | None) -> JobRequirements:
    if not title:
        return JobRequirements()
    base = f"Relevant skills and qualifications for {title}"
    return JobRequirements(mandatory=[base])


def run(state: ScreeningState) -> dict:
    errors = list(state.errors)
    prompt_versions = dict(state.prompt_versions)
    model = state.model

    if not state.job_description:
        return {
            "job_requirements": _from_title(state.job_title),
            "errors": errors,
            "prompt_versions": prompt_versions,
            "model": model,
        }

    try:
        raw, prompt_versions, model = llm_json(
            job_requirements.SYSTEM,
            job_requirements.user(state.job_title, state.job_description),
            prompt_version=job_requirements.PROMPT_VERSION,
            model=model,
            prompt_versions=prompt_versions,
            enabled=state.ai_mode,
        )
        result = JobRequirements.model_validate(raw)
    except (NodeError, ValueError):
        errors.append("job_requirements: LLM failed, used title fallback")
        result = _from_title(state.job_title)

    return {
        "job_requirements": result,
        "errors": errors,
        "prompt_versions": prompt_versions,
        "model": model,
    }