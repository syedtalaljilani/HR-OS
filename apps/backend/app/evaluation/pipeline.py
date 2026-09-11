"""Evaluation pipeline: pull traces from Langfuse, run judges, ingest scores.

Routing is by trace name and by the shape of the observations recorded in the
trace, so it keeps working when prompts or graph node names change.
"""
from typing import Any, Iterable

from . import basic_judges, lf_api, llm_judges

FEATURES = {
    "ocr": ("ollama-ocr",),
    "extraction": ("cv-extraction",),
    "screening": ("cv-screening", "cv-screening-capped"),
    "job-assistant": ("job-assist",),
    "email": ("email-draft",),
}


def _obs_with_key(observations: list[dict], key: str) -> list[dict]:
    return [o for o in observations if isinstance(o.get("output"), dict) and key in o["output"]]


def _user_content(generation: dict) -> str:
    messages = (generation.get("input") or {}).get("messages") or []
    for msg in reversed(messages):
        content = msg.get("content")
        if isinstance(content, str) and content.strip():
            return content
    return ""


def _extract_materials(trace: dict) -> dict:
    """Pull whatever each feature needs out of the trace's observations."""
    name = trace.get("name")
    obs = trace.get("observations") or []
    mats: dict[str, Any] = {}

    if name == "ollama-ocr":
        for o in obs:
            if not isinstance(o, dict):
                continue
            out = o.get("output")
            if isinstance(out, dict) and isinstance(out.get("text"), str):
                mats["ocr_text"] = out["text"]
                break
        return mats

    if name == "cv-extraction":
        root_span = next(
            (o for o in obs if (o.get("type") in ("SPAN", "ROOT", "GENERATION", None))),
            {},
        )
        mats["trace_input"] = trace.get("input") or root_span.get("input") or {}
        # The profile is the generation whose output is a dict rich in profile keys.
        for o in obs:
            if not isinstance(o, dict):
                continue
            out = o.get("output")
            if isinstance(out, dict) and any(
                k in out for k in ("skills", "experience", "education", "name")
            ):
                mats["profile"] = out
                cv = _user_content(o)
                if cv and len(cv) > 60:
                    mats["cv_text"] = cv
                break
        return mats

    if name in FEATURES["screening"]:
        mats["trace_input"] = trace.get("input") or {}
        for o in obs:
            if not isinstance(o, dict):
                continue
            out = o.get("output")
            candidates: list = []
            if isinstance(out, list):
                candidates = out
            elif isinstance(out, dict):
                nested = out.get("matched_requirements")
                candidates = nested if isinstance(nested, list) else []
            items = [
                i
                for i in candidates
                if isinstance(i, dict) and "requirement" in i and "status" in i
            ]
            if items:
                mats["matched"] = items
            elif isinstance(out, dict):
                recommand = out.get("recommendation")
                score_holder = out if ("score" in out and "recommendation" in out) else None
                if score_holder is None and isinstance(recommand, dict) and "score" in recommand:
                    score_holder = recommand
                if score_holder is not None:
                    mats["recommendation"] = score_holder
        mats["cv_text"] = _user_content(
            next(iter(_obs_with_key(obs, "recommendation")), {})
        )
        return mats

    if name == "job-assist":
        mats["trace_input"] = trace.get("input") or {}
        for o in obs:
            if not isinstance(o, dict):
                continue
            out = o.get("output")
            if isinstance(out, dict) and isinstance(out.get("description"), str):
                desc = out["description"]
                if len(desc) > 30:
                    mats["description"] = desc
                    break
        return mats

    if name == "email-draft":
        mats["trace_input"] = trace.get("input") or {}
        for o in obs:
            if not isinstance(o, dict):
                continue
            out = o.get("output")
            if isinstance(out, dict) and out.get("subject") is not None:
                mats["trace_output"] = out
                break
        gen = next(iter(_obs_with_key(obs, "subject")), None)
        if gen is not None:
            mats["task_context"] = _user_content(gen)
        return mats

    return mats


def evaluate_trace(trace: dict, ingest: bool = True) -> dict:
    """Run every applicable judge for one trace; optionally write scores."""
    name = trace.get("name")
    trace_id = trace.get("id")
    mats = _extract_materials(trace)
    scores: list[dict] = []
    reports: list[str] = []

    def add(judgings: dict[str, dict]) -> None:
        for score_name, payload in judgings.items():
            entry = {"name": score_name, "comment": payload.get("comment", "")}
            value = payload.get("value")
            if value is None:
                entry["value"] = None
                entry["skipped"] = True
                scores.append(entry)
            else:
                entry["value"] = round(float(value), 3)
                scores.append(entry)

    if name == "ollama-ocr":
        text = mats.get("ocr_text", "")
        quality, issues = basic_judges.ocr_text_quality(text)
        add(
            {
                "ocr_text_quality": {
                    "value": quality,
                    "comment": "; ".join(issues) or "no repetition detected",
                }
            }
        )
    elif name == "cv-extraction":
        profile = mats.get("profile")
        shape, shape_issues = basic_judges.extraction_shape(profile)
        add(
            {
                "extraction_shape": {
                    "value": shape,
                    "comment": "; ".join(shape_issues[:3]) or "profile shape valid",
                }
            }
        )
        if profile and mats.get("cv_text"):
            add(llm_judges.judge_extraction(mats["cv_text"], profile))
    elif name in FEATURES["screening"]:
        rules_ok, issues = basic_judges.screening_rules(
            mats.get("matched"), mats.get("recommendation")
        )
        add(
            {
                "screening_rules_ok": {
                    "value": rules_ok,
                    "comment": "; ".join(issues) or "screening rules held",
                }
            }
        )
        if mats.get("matched") and mats.get("recommendation"):
            add(llm_judges.judge_screening(mats["matched"], mats["recommendation"]))
    elif name == "job-assist":
        title = (mats.get("trace_input") or {}).get("job_title")
        note = (mats.get("trace_input") or {}).get("user_note") or ""
        description = mats.get("description")
        if description:
            t_ok, t_issues = basic_judges.job_title_coverage(title, description)
            s_ok, s_issues = basic_judges.job_draft_shape(description)
            add(
                {
                    "job_draft_includes_title": {
                        "value": t_ok,
                        "comment": "; ".join(t_issues) or "title present",
                    },
                    "job_draft_shape": {
                        "value": s_ok,
                        "comment": "; ".join(s_issues) or "draft well-formed",
                    },
                }
            )
            add(llm_judges.judge_job_draft(title, note, description))
    elif name == "email-draft":
        output = mats.get("trace_output") or {}
        subject, body = output.get("subject"), output.get("body")
        if subject is not None:
            p_ok, p_issues = basic_judges.email_placeholders(subject, body)
            s_ok, s_issues = basic_judges.email_shape(subject, body)
            add(
                {
                    "email_no_placeholders": {
                        "value": p_ok,
                        "comment": "; ".join(p_issues) or "no leftover placeholders",
                    },
                    "email_shape": {
                        "value": s_ok,
                        "comment": "; ".join(s_issues) or "email well-formed",
                    },
                }
            )
            if mats.get("task_context"):
                add(llm_judges.judge_email(mats["task_context"], subject, body or ""))
    else:
        reports.append(f"no evaluator for feature name {name!r}")

    ingested = []
    if ingest:
        for entry in scores:
            if entry.get("skipped"):
                continue
            try:
                lf_api.ingest_score(
                    trace_id, entry["name"], entry["value"], entry.get("comment", "")
                )
                ingested.append(entry["name"])
            except RuntimeError as e:
                reports.append(f"ingest {entry['name']} failed: {e}")

    return {
        "id": trace_id,
        "name": name,
        "scores": scores,
        "ingested": ingested,
        "reports": reports,
    }


def evaluate(features: Iterable[str] | None = None, limit: int = 50, ingest: bool = True) -> list[dict]:
    trace_names = set()
    for feature in features or FEATURES:
        trace_names.update(FEATURES.get(feature, ()))
    traces = lf_api.list_traces(limit=limit)
    matched = [t for t in traces if t.get("name") in trace_names]
    results: list[dict] = []
    for meta in matched:
        trace = lf_api.get_trace(meta["id"])
        results.append(evaluate_trace(trace, ingest=ingest))
    return results