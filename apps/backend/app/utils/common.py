import uuid
from dataclasses import asdict, is_dataclass
from datetime import date, datetime

from pydantic import BaseModel


def jsonify_uuid(value) -> str | None:
    if value is None:
        return None
    return str(value)


def jsonify_data(obj) -> dict | None:
    result = to_json_safe(obj)
    if isinstance(result, dict):
        return result
    return {"value": result}


def to_json_safe(obj, _depth: int = 0, _seen: set[int] | None = None) -> object:
    if _depth > 8:
        return str(obj)
    if obj is None:
        return None
    if isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, uuid.UUID):
        return str(obj)
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {str(k): to_json_safe(v, _depth + 1, _seen) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [to_json_safe(v, _depth + 1, _seen) for v in obj]
    if isinstance(obj, BaseModel):
        return to_json_safe(obj.model_dump(), _depth + 1, _seen)
    if is_dataclass(obj):
        return to_json_safe(asdict(obj), _depth + 1, _seen)
    if hasattr(obj, "__dict__"):
        oid = id(obj)
        if _seen is None:
            _seen = set()
        if oid in _seen:
            return str(obj)
        _seen = set(_seen) | {oid}
        payload = {
            str(k): to_json_safe(v, _depth + 1, _seen)
            for k, v in obj.__dict__.items()
            if not k.startswith("_sa_")
        }
        return payload
    return str(obj)