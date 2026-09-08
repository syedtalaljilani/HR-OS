"""Builds a user prompt containing JSON-embedded metadata like prompt version."""

PROMPT_VERSION_HEADER = (
    "PROMPT_VERSION={version}\n"
    "MODEL={model}\n"
    "Follow the exact JSON schema described in the system message.\n"
)


def with_metadata(prompt: str, *, version: str, model: str) -> str:
    return PROMPT_VERSION_HEADER.format(version=version, model=model) + prompt
