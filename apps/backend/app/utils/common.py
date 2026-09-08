import uuid
from datetime import date, datetime


def jsonify_uuid(value) -> str | None:
    if value is None:
        return None
    return str(value)


def jsonify_data(obj) -> dict | None:
    result = to_json_safe(obj)
    if isinstance(result, dict):
        return result
    return {"value": result}


def to_json_safe(obj) -> object:
    if obj is None:
        return None
    if isinstance(obj, uuid.UUID):
        return str(obj)
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {str(k): to_json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [to_json_safe(v) for v in obj]
    return obj