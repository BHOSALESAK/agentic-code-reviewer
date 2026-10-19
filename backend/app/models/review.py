from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.persistence.database import Base


def new_id() -> str:
    return str(uuid4())


def now_utc() -> datetime:
    return datetime.now(UTC)


class Timestamped:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc, nullable=False)


class Repository(Timestamped, Base):
    __tablename__ = "repositories"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    full_name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    default_branch: Mapped[str | None] = mapped_column(String(255))


class PullRequest(Timestamped, Base):
    __tablename__ = "pull_requests"
    __table_args__ = (UniqueConstraint("repository_id", "number", name="uq_pull_request_repository_number"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    repository_id: Mapped[str] = mapped_column(ForeignKey("repositories.id", ondelete="CASCADE"), index=True)
    number: Mapped[int] = mapped_column(Integer)
    title: Mapped[str | None] = mapped_column(String(500))
    base_sha: Mapped[str | None] = mapped_column(String(200))
    head_sha: Mapped[str | None] = mapped_column(String(200))


class ReviewRun(Timestamped, Base):
    __tablename__ = "review_runs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    repository_id: Mapped[str] = mapped_column(ForeignKey("repositories.id", ondelete="CASCADE"), index=True)
    pull_request_id: Mapped[str] = mapped_column(ForeignKey("pull_requests.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(50), index=True)
    commit_sha: Mapped[str | None] = mapped_column(String(200))
    partial_failure: Mapped[bool] = mapped_column(default=False, nullable=False)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    usage_metadata: Mapped[dict | None] = mapped_column(JSON)


class ReviewFinding(Timestamped, Base):
    __tablename__ = "review_findings"
    __table_args__ = (Index("ix_review_findings_review_status", "review_run_id", "verification_status"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    review_run_id: Mapped[str] = mapped_column(ForeignKey("review_runs.id", ondelete="CASCADE"), index=True)
    repository_id: Mapped[str] = mapped_column(ForeignKey("repositories.id", ondelete="CASCADE"), index=True)
    finding_key: Mapped[str] = mapped_column(String(255), index=True)
    category: Mapped[str] = mapped_column(String(80))
    severity: Mapped[str] = mapped_column(String(30))
    confidence: Mapped[float] = mapped_column()
    file_path: Mapped[str | None] = mapped_column(String(1000))
    start_line: Mapped[int | None] = mapped_column(Integer)
    end_line: Mapped[int | None] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str] = mapped_column(Text)
    evidence: Mapped[str | None] = mapped_column(Text)
    impact: Mapped[str | None] = mapped_column(Text)
    remediation: Mapped[str | None] = mapped_column(Text)
    verification_status: Mapped[str] = mapped_column(String(50), index=True)
    provenance: Mapped[dict | None] = mapped_column(JSON)
    publication_status: Mapped[str] = mapped_column(String(50), default="Not published")


class AgentExecution(Timestamped, Base):
    __tablename__ = "agent_executions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    review_run_id: Mapped[str] = mapped_column(ForeignKey("review_runs.id", ondelete="CASCADE"), index=True)
    agent_name: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(50))
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    candidate_count: Mapped[int] = mapped_column(Integer, default=0)
    error_code: Mapped[str | None] = mapped_column(String(100))
    usage_metadata: Mapped[dict | None] = mapped_column(JSON)


class ToolExecution(Timestamped, Base):
    __tablename__ = "tool_executions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    review_run_id: Mapped[str] = mapped_column(ForeignKey("review_runs.id", ondelete="CASCADE"), index=True)
    tool_name: Mapped[str] = mapped_column(String(100))
    rule_id: Mapped[str | None] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(50))
    result_metadata: Mapped[dict | None] = mapped_column(JSON)


class VerificationDecision(Timestamped, Base):
    __tablename__ = "verification_decisions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    finding_id: Mapped[str] = mapped_column(ForeignKey("review_findings.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(50))
    explanation: Mapped[str] = mapped_column(Text)
    provenance: Mapped[dict | None] = mapped_column(JSON)


class EvaluationRun(Timestamped, Base):
    __tablename__ = "evaluation_runs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(255))
    baseline: Mapped[str] = mapped_column(String(100))
    metrics: Mapped[dict] = mapped_column(JSON)
    measured: Mapped[bool] = mapped_column(default=False, nullable=False)


class GroundTruthLabel(Timestamped, Base):
    __tablename__ = "ground_truth_labels"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    evaluation_run_id: Mapped[str] = mapped_column(ForeignKey("evaluation_runs.id", ondelete="CASCADE"), index=True)
    repository_id: Mapped[str | None] = mapped_column(ForeignKey("repositories.id", ondelete="SET NULL"))
    category: Mapped[str] = mapped_column(String(80))
    file_path: Mapped[str | None] = mapped_column(String(1000))
    start_line: Mapped[int | None] = mapped_column(Integer)
    description: Mapped[str] = mapped_column(Text)


class PublicationAttempt(Timestamped, Base):
    __tablename__ = "publication_attempts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    finding_id: Mapped[str] = mapped_column(ForeignKey("review_findings.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(50))
    reason: Mapped[str | None] = mapped_column(Text)
    external_comment_id: Mapped[str | None] = mapped_column(String(200))
