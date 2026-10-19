from datetime import UTC, datetime
from enum import StrEnum
from pathlib import PurePosixPath
from typing import Annotated
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Severity(StrEnum):
    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"
    INFORMATIONAL = "Informational"


class IssueCategory(StrEnum):
    SECURITY = "Security"
    BUG_LOGIC = "Bug and Logic"
    ERROR_HANDLING = "Error Handling"
    TEST_ADEQUACY = "Test Adequacy"
    DEPENDENCY = "Dependency"


class VerificationStatus(StrEnum):
    UNVERIFIED = "Unverified"
    VERIFIED = "Verified"
    REJECTED = "Rejected"
    NEEDS_MANUAL_REVIEW = "Needs manual review"


class PublicationStatus(StrEnum):
    NOT_PUBLISHED = "Not published"
    PUBLISHED = "Published"
    FAILED = "Failed"
    OUTDATED = "Outdated"


class Finding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    finding_id: UUID = Field(default_factory=uuid4)
    review_id: UUID
    repository_id: UUID
    pull_request_number: Annotated[int, Field(ge=1)]
    commit_sha: str | None = Field(default=None, min_length=1, max_length=200)
    category: IssueCategory
    title: str = Field(min_length=1, max_length=300)
    description: str = Field(min_length=1, max_length=10000)
    severity: Severity
    confidence: float = Field(ge=0, le=1)
    file_path: str | None = Field(default=None, max_length=1000)
    start_line: int | None = Field(default=None, ge=1)
    end_line: int | None = Field(default=None, ge=1)
    evidence: str | None = Field(default=None, max_length=12000)
    impact: str | None = Field(default=None, max_length=5000)
    recommended_remediation: str | None = Field(default=None, max_length=5000)
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED
    verification_explanation: str | None = Field(default=None, max_length=5000)
    supporting_tools: list[str] = Field(default_factory=list, max_length=20)
    supporting_rule_ids: list[str] = Field(default_factory=list, max_length=20)
    is_changed_line: bool | None = None
    publication_status: PublicationStatus = PublicationStatus.NOT_PUBLISHED
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("commit_sha", "title", "description", "evidence", "impact", "recommended_remediation", "verification_explanation")
    @classmethod
    def reject_blank_text(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("text values must not be blank")
        return value

    @field_validator("file_path")
    @classmethod
    def validate_relative_file_path(cls, value: str | None) -> str | None:
        if value is None:
            return value
        path = PurePosixPath(value)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("file_path must be a relative repository path")
        return value

    @model_validator(mode="after")
    def validate_line_range(self) -> "Finding":
        if (self.start_line is None) != (self.end_line is None):
            raise ValueError("start_line and end_line must be provided together")
        if self.start_line is not None and self.end_line is not None and self.end_line < self.start_line:
            raise ValueError("end_line must be greater than or equal to start_line")
        return self
