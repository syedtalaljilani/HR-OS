"""Email agent node.

Drafts an email (subject + body) using the small general model. Falls back to
a deterministic template when the model is unavailable so the HR user always
gets a usable draft for review/editing.
"""
from ai.prompts import email as email_prompt
from ai.schemas.email_state import EmailAgentState
from ._util import NodeError, llm_json


def _signoff(state: EmailAgentState) -> str:
    hr = state.hr_name or "Human Resources"
    company = state.company_name
    if company:
        return f"Best regards,\n{hr}\n{company}"
    return f"Best regards,\n{hr}"


def _fallback(state: EmailAgentState) -> dict:
    name = state.candidate_name or "there"
    title = state.job_title or "the position"

    if state.email_type == "REJECTED":
        body = (
            f"Dear {name},\n\n"
            f"Thank you for applying for {title}. After careful review we regret "
            "to inform you that we will not be moving forward with your application."
        )
        if state.reason:
            body += f"\n\n{state.reason}"
        body += (
            "\n\nWe appreciate the time and effort you invested in your application.\n\n"
            + _signoff(state)
        )
        subject = f"Application Update on {title}"
    elif state.email_type == "SELECTED":
        body = (
            f"Dear {name},\n\n"
            f"Congratulations! We are pleased to move your application for {title} "
            "forward in the recruitment process. Our HR team will contact you with "
            "the next steps.\n\n"
            + _signoff(state)
        )
        subject = f"Application Update: You have been selected for {title}"
    else:
        body = (
            f"Dear {name},\n\n"
            f"Thank you for your application for {title}. "
            f"Your application is now under review."
        )
        if state.hr_notes:
            body += f"\n\n{state.hr_notes}"
        body += "\n\n" + _signoff(state)
        subject = f"Update regarding your application for {title}"

    return {"subject": subject, "body": body}


def run(state: EmailAgentState) -> dict:
    errors = list(state.errors)
    prompt_versions = dict(state.prompt_versions or {})
    model = state.model

    try:
        raw, prompt_versions, model = llm_json(
            email_prompt.SYSTEM,
            email_prompt.user(state),
            prompt_version=email_prompt.PROMPT_VERSION,
            model=model,
            prompt_versions=prompt_versions,
            enabled=state.ai_mode,
        )
        subject = raw.get("subject")
        body = raw.get("body")
        if not isinstance(subject, str) or not isinstance(body, str):
            raise ValueError("email draft missing subject/body")
        draft = {"subject": subject, "body": body}
    except (NodeError, ValueError):
        errors.append("email: LLM failed, used deterministic fallback")
        draft = _fallback(state)

    return {
        "draft": draft,
        "errors": errors,
        "model": model,
    }
