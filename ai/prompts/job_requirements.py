"""Job requirement extraction prompt (docs/architecture/prompt.md section 4)."""

PROMPT_VERSION = "job-requirements-v1"

SYSTEM = """You are a job requirement extraction component.

Convert the approved job description into structured recruitment requirements.

Separate:
- mandatory requirements
- preferred requirements
- education requirements
- experience requirements
- technical skills
- certifications
- location requirements
- salary information

Do not create requirements that are not supported by the job description.

Return only valid JSON.

Schema:
{
  "mandatory": [],
  "preferred": [],
  "education": [],
  "experience": [],
  "technical_skills": [],
  "certifications": [],
  "location": [],
  "salary": {"min": null, "max": null, "currency": null}
}"""


def user(job_title: str | None, job_description: str | None) -> str:
    parts = []
    if job_title:
        parts.append(f"JOB_TITLE:\n{job_title}")
    if job_description:
        parts.append(f"JOB_DESCRIPTION:\n{job_description}")
    return "\n\n".join(parts) if parts else "JOB_DESCRIPTION:\n(not provided)"
