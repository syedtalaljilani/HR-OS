"""Email-writing prompts for the LangGraph email agent.

The same prompt powers two flows:
- Pipeline emails (rejection/acceptance) using structured context
  (reason, score, missing requirements, rank).
- An HR email-writing assistant where the HR user gives free-form notes.

A small model is used; the output must stay plain, concise and human-sounding.
"""

PROMPT_VERSION = "email-draft-v1"

SYSTEM = """You are a senior HR email writer. You compose clear, professional and
warm recruitment emails in the candidate's language of communication. Write like
a real HR person, not like a corporate bot.

Return only valid JSON.

Schema:
{
  "subject": "Email subject line",
  "body": "Full email body as plain text with newlines."
}

Rules:
- Output PLAIN TEXT only. No markdown: no "#", "**", bullets or numbers.
- Keep the body short, respectful, and honest.
- Open with a greeting using the candidate's name when provided.
- Do NOT include the internal AI confidence/score unless it is explicitly given
  in the context and requested. Never leak internal ranking.
- If an explicit rejection/decision reason is provided, reflect it clearly and
  kindly, with enough detail that the candidate understands the decision. If
  only HR notes are provided, use those as the driver.
- Always mention the COMPANY_NAME as the sender/company when provided, and sign
  off with the HR_NAME (e.g. "Best regards,\n{HR_NAME}" or
  "Best regards, {HR_NAME} on behalf of {COMPANY_NAME}").
- Close politely with a sign-off.
- If the tone is "firm", be more direct and brief. If "warm", be encouraging.
"""


def _render_context(context: dict, reason: str | None) -> str:
    lines = []
    if reason:
        lines.append(f"REASON: {reason}")
    if context:
        for key, value in context.items():
            if value in (None, "", []):
                continue
            if isinstance(value, list):
                value = ", ".join(str(v) for v in value)
            lines.append(f"{key.upper()}: {value}")
    return "\n".join(lines)


def user(state) -> str:
    parts = [f"EMAIL_TYPE: {state.email_type or 'general'}"]
    if state.candidate_name:
        parts.append(f"CANDIDATE_NAME: {state.candidate_name}")
    if state.job_title:
        parts.append(f"JOB_TITLE: {state.job_title}")
    if state.tone:
        parts.append(f"TONE: {state.tone}")
    if state.company_name:
        parts.append(f"COMPANY_NAME: {state.company_name}")
    if state.hr_name:
        parts.append(f"HR_NAME: {state.hr_name}")
    context = _render_context(state.context, state.reason)
    if context:
        parts.append("CONTEXT:\n" + context)
    parts.append("HR_NOTES / INSTRUCTIONS:")
    parts.append(state.hr_notes or "(no additional instructions — write a standard email)")
    return "\n\n".join(parts)
