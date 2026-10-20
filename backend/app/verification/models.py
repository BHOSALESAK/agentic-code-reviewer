from enum import StrEnum

from pydantic import BaseModel, Field


class VerificationOutcome(StrEnum):
    VERIFIED = "verified"
    REJECTED = "rejected"
    NEEDS_MANUAL_REVIEW = "needs_manual_review"


class VerificationDecision(BaseModel):
    status: VerificationOutcome
    reason_code: str
    explanation: str
    provenance: list[str] = Field(default_factory=list)


class CriticResponse(BaseModel):
    supported: bool
    remediation_addressed: bool
    explanation: str
