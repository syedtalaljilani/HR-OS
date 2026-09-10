"""Langfuse-backed quality evaluation for the HR OS LLM features.

Run from ``apps/backend`` with::

    python -m app.evaluation.cli --features ocr,extraction --dry-run

Features: ``ocr``, ``extraction``, ``screening``, ``job-assistant``, ``email``.
"""
from .pipeline import FEATURES, evaluate, evaluate_trace

__all__ = ["FEATURES", "evaluate", "evaluate_trace"]