from enum import Enum


class UserRole(str, Enum):
    ADMIN = "ADMIN"
    HR = "HR"
    INTERVIEWER = "INTERVIEWER"


class JobStatus(str, Enum):
    DRAFT = "DRAFT"
    OPEN = "OPEN"
    CLOSED = "CLOSED"


class ApplicationStatus(str, Enum):
    APPLIED = "APPLIED"
    PROCESSING = "PROCESSING"
    HR_REVIEW = "HR_REVIEW"
    SHORTLISTED = "SHORTLISTED"
    INTERVIEW_SCHEDULED = "INTERVIEW_SCHEDULED"
    TECHNICAL_INTERVIEW = "TECHNICAL_INTERVIEW"
    TECHNICAL_REVIEW = "TECHNICAL_REVIEW"
    BEHAVIORAL_INTERVIEW = "BEHAVIORAL_INTERVIEW"
    FINAL_REVIEW = "FINAL_REVIEW"
    SELECTED = "SELECTED"
    HOLD = "HOLD"
    REJECTED = "REJECTED"


class ExtractionStatus(str, Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class Recommendation(str, Enum):
    MATCH = "MATCH"
    PARTIAL = "PARTIAL"
    MISSING = "MISSING"
    UNCLEAR = "UNCLEAR"


class HRDecision(str, Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    OVERRIDDEN = "OVERRIDDEN"


class TalentPoolStatus(str, Enum):
    ACTIVE = "ACTIVE"
    CONTACTED = "CONTACTED"
    INTERESTED = "INTERESTED"
    NOT_INTERESTED = "NOT_INTERESTED"
    MOVED_TO_PIPELINE = "MOVED_TO_PIPELINE"
    EXPIRED = "EXPIRED"
    REMOVED = "REMOVED"


class InterviewType(str, Enum):
    TECHNICAL = "TECHNICAL"
    HR = "HR"


class InterviewStatus(str, Enum):
    SCHEDULED = "SCHEDULED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class AssignmentStatus(str, Enum):
    ASSIGNED = "ASSIGNED"
    COMPLETED = "COMPLETED"


class EmailType(str, Enum):
    APPLICATION = "APPLICATION"
    INTERVIEW = "INTERVIEW"
    SELECTED = "SELECTED"
    REJECTED = "REJECTED"
    REPLY = "REPLY"


class EmailDirection(str, Enum):
    INBOUND = "INBOUND"
    OUTBOUND = "OUTBOUND"
    TALENT_POOL = "TALENT_POOL"


class EmailStatus(str, Enum):
    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"


class ScreeningQueueStatus(str, Enum):
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
