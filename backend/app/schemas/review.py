from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, model_validator


class ReviewStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    COMPLETED_WITH_ERRORS = "completed_with_errors"
    FAILED = "failed"


class ReviewRequest(BaseModel):
    fixture_id: str | None = None
    reference: str | None = None

    @model_validator(mode="after")
    def require_one_source(self) -> "ReviewRequest":
        if bool(self.fixture_id) == bool(self.reference):
            raise ValueError("provide exactly one fixture_id or reference")
        return self


class ReviewAccepted(BaseModel):
    review_id: UUID
    status: ReviewStatus
    existing: bool = False
