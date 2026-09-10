"""Natural-language date/time extraction for candidate interview-slot requests.

The email reply agent uses this to decide (human-in-the-loop) whether a
candidate who asked to move their interview gave a full date AND time, or only
a date — in the latter case the agent asks for the time before generating a
request for HR approval.
"""
import re
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

KARACHI = ZoneInfo("Asia/Karachi")

MONTHS = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}

WEEKDAYS = {
    "monday": 0, "mon": 0,
    "tuesday": 1, "tue": 1, "tues": 1,
    "wednesday": 2, "wed": 2,
    "thursday": 3, "thu": 3, "thur": 3, "thurs": 3,
    "friday": 4, "fri": 4,
    "saturday": 5, "sat": 5,
    "sunday": 6, "sun": 6,
}

_MONTH_RE = r"(?:january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec)"

_INTENT_PATTERNS = (
    r"\breschedul(?:e|ed|ing)?\b",
    r"\bre-?schedul",
    r"\bmove\b.{0,40}\b(?:interview|meeting|call)\b",
    r"\b(?:interview|meeting|call)\b.{0,40}\bmove\b",
    r"\b(?:another|different|other|alternative|better|new)\s+(?:time|day|date|slot)\b",
    r"\b(?:date|time|slot|timing|schedule)\b.{0,20}\b(?:change|move|shift)\b",
    r"\b(?:change|move|shift)\b.{0,30}\b(?:interview|slot|schedule|timing|time|date|day)\b",
    r"\b(?:change|move|shift)\b.{0,40}(?:20\d{2}-\d{1,2}|\d{1,2}/|\d{1,2}:\d{2}|(?:next|this|coming)?\s*(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday))",
    r"\bshift\b.{0,30}\b(?:interview|slot|time)\b",
    r"\bpostpon|push\s+(?:back|the)|bring\s+forward|advance\b",
    r"\b(?:would|can|could|is|are)\b.{0,30}\b(?:be\s+)?(?:possible|ok\b|okay|fine|convenient)\b",
    r"\b(?:can|could)\s+(?:we|you|i)\b",
    r"\bi'?d\s+like\b|\bi\s+would\s+like\b|\bi\s+want\b",
    r"\bnot\s+(?:free|available)\b|\bbusy\b",
    r"\bcan'?t\s+(?:make|attend)\b|\bcannot\s+(?:make|attend)\b|\bunable\s+to\s+(?:make|attend)\b",
    r"\bworks\b|\bsuits\s+me\b|\bsuitable\b|\bconvenient\b|\bok\s+with\b|\bokay\s+with\b|\bfine\s+with\b",
    r"\bhave\s+to\s+be\s+(?:moved|shifted)\b",
)

_INTENT_RE = re.compile("|".join(_INTENT_PATTERNS), re.IGNORECASE)

_TIME12_RE = re.compile(
    r"\b(\d{1,2})(?::(\d{2}))?\s*(a\.?m\.?|p\.?m\.?)\b", re.IGNORECASE
)
_TIME24_RE = re.compile(r"\b(\d{1,2}):(\d{2})\b")
_OCLOCK_RE = re.compile(r"\b(\d{1,2})\s*o'?clock\b", re.IGNORECASE)

_ISO_DATE_RE = re.compile(r"\b(20\d{2})-(\d{1,2})-(\d{1,2})\b")
_SLASH_DATE_RE = re.compile(r"\b(\d{1,2})[/\-.](\d{1,2})(?:[/\-.](\d{2,4}))?\b")
_ORDINAL_DAY_RE = re.compile(r"\b(\d{1,2})(?:st|nd|rd|th)\b")
_MONTH_FIRST_RE = re.compile(
    rf"\b({_MONTH_RE})(?:\.)?\s+(\d{{1,2}})(?:st|nd|rd|th)?(?:,?\s+(20\d{{2}}))?\b",
    re.IGNORECASE,
)
_DAY_FIRST_RE = re.compile(
    rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+(?:of\s+)?({_MONTH_RE})(?:,?\s+(20\d{{2}}))?\b",
    re.IGNORECASE,
)
_WEEKDAY_RE = re.compile(
    r"\b((?:next|this|coming)\s+)?(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
    re.IGNORECASE,
)
_TODAY_TOKEN_RE = re.compile(r"\b(today|tomorrow)\b", re.IGNORECASE)


def _clip_year(year: int) -> int:
    return year if 2000 <= year <= 2099 else (year + 2000 if year < 100 else year)


def _extract_time(low: str) -> time | None:
    match = _TIME12_RE.search(low)
    if match:
        hour, minute, mer = int(match.group(1)), int(match.group(2) or 0), match.group(3)
        if not (1 <= hour <= 12 and 0 <= minute <= 59):
            return None
        if mer.lower().startswith("p") and hour != 12:
            hour += 12
        elif mer.lower().startswith("a") and hour == 12:
            hour = 0
        return time(hour, minute)
    match = _OCLOCK_RE.search(low)
    if match:
        hour = int(match.group(1))
        if 0 <= hour <= 23:
            return time(hour, 0)
    match = _TIME24_RE.search(low)
    if match:
        hour, minute = int(match.group(1)), int(match.group(2))
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return time(hour, minute)
    return None


def _bad(part: str) -> bool:
    return not (1 <= int(part) <= 31)


def _extract_date(low: str, today: date) -> date | None:
    match = _ISO_DATE_RE.search(low)
    if match:
        y, m, d = int(match.group(1)), int(match.group(2)), int(match.group(3))
        try:
            return date(y, m, d)
        except ValueError:
            return None

    match = _SLASH_DATE_RE.search(low)
    if match:
        a, b, year = int(match.group(1)), int(match.group(2)), match.group(3)
        if not _bad(str(a)) and not _bad(str(b)):
            try:
                if a > 12:
                    return date(_clip_year(int(year) if year else today.year), b, a)
                if b > 12:
                    return date(_clip_year(int(year) if year else today.year), a, b)
                # both <= 12: pick MM/DD if the day is in this month and ahead
                # of today, otherwise interpret as DD/MM (common outside the US)
                m, d = a, b
                year_num = _clip_year(int(year) if year else today.year)
                cand_1 = date(year_num, m, d)
                cand_2 = date(year_num, d, m)
                if cand_1 >= today and (d > m or cand_1 >= cand_2):
                    return cand_1
                return cand_2
            except ValueError:
                return None

    match = _MONTH_FIRST_RE.search(low)
    if match:
        month = MONTHS[match.group(1).lower()]
        day = int(match.group(2))
        year = int(match.group(3)) if match.group(3) else today.year
        try:
            candidate = date(year, month, day)
        except ValueError:
            return None
        if candidate < today:
            candidate = candidate.replace(year=year + 1)
        return candidate

    match = _DAY_FIRST_RE.search(low)
    if match:
        day = int(match.group(1))
        month = MONTHS[match.group(2).lower()]
        year = int(match.group(3)) if match.group(3) else today.year
        try:
            candidate = date(year, month, day)
        except ValueError:
            return None
        if candidate < today:
            candidate = candidate.replace(year=year + 1)
        return candidate

    match = _WEEKDAY_RE.search(low)
    if match:
        qualifier, name = match.group(1) or "", match.group(2).lower()
        target_wd = WEEKDAYS[name]
        today_wd = today.weekday()
        delta = (target_wd - today_wd) % 7
        candidate = today + timedelta(days=delta)
        if delta == 0 and "next" in qualifier.lower():
            candidate += timedelta(days=7)
        return candidate

    match = _TODAY_TOKEN_RE.search(low)
    if match:
        token = match.group(1).lower()
        if token == "tomorrow":
            return today + timedelta(days=1)
        return today

    match = _ORDINAL_DAY_RE.search(low)
    if match:
        day = int(match.group(1))
        try:
            candidate = date(today.year, today.month, day)
        except ValueError:
            return None
        if candidate < today:
            if today.month == 12:
                candidate = date(today.year + 1, 1, day)
            else:
                try:
                    candidate = date(today.year, today.month + 1, day)
                except ValueError:
                    return None
        return candidate

    return None


def extract_requested_slot(
    text: str | None, *, now: datetime | None = None
) -> dict:
    """Detect an interview-move request and pull the date / time the candidate gave.

    Returns ``{"intent": bool, "date": date | None, "time": time | None}`` where
    the date/time are interpreted in Asia/Karachi wall-clock time.
    """
    if not text:
        return {"intent": False, "date": None, "time": None}
    low = text.lower()
    today = (now or datetime.now(KARACHI)).date()
    return {
        "intent": bool(_INTENT_RE.search(low)),
        "date": _extract_date(low, today),
        "time": _extract_time(low),
    }


def build_proposed_at(parsed: dict) -> datetime | None:
    """Combine a parsed date + time into an aware UTC datetime (or None)."""
    from app.services.interview_service import as_utc

    if not parsed.get("date"):
        return None
    combined = datetime.combine(parsed["date"], parsed["time"] or time(0, 0))
    aware = combined.replace(tzinfo=KARACHI)
    return as_utc(aware)