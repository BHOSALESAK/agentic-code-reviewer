import threading
import time
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.config import get_settings
from app.github.client import FixturePullRequestProvider, GitHubClient, GitHubError
from app.github.reference import InvalidPRReference, PRReference, parse_pr_reference
from app.graphs.review import build_review_graph
from app.models.review import (
    AgentExecution,
    PullRequest,
    Repository,
    ReviewFinding,
    ReviewRun,
    ToolExecution,
    VerificationDecision,
)
from app.persistence.database import Base, SessionLocal, engine
from app.schemas.review import ReviewRequest, ReviewStatus

_review_locks: dict[str, threading.Lock] = {}
_review_locks_guard = threading.Lock()


def _lock_for(key: str) -> threading.Lock:
    with _review_locks_guard:
        return _review_locks.setdefault(key, threading.Lock())


def provider_for_settings():
    settings = get_settings()
    return FixturePullRequestProvider() if settings.demo_mode else GitHubClient(settings.github_token)


def reference_for_request(request: ReviewRequest) -> PRReference:
    if request.fixture_id:
        mapping = {"small": 1, "large": 2}
        if request.fixture_id not in mapping:
            raise GitHubError("fixture not found; choose a listed fixture", 404)
        return PRReference("synthetic", "demo", mapping[request.fixture_id])
    try:
        return parse_pr_reference(request.reference or "")
    except InvalidPRReference as exc:
        raise GitHubError(str(exc), 422) from exc


def create_queued_review(request: ReviewRequest) -> tuple[ReviewRun, bool, PRReference, object]:
    Base.metadata.create_all(engine)
    reference = reference_for_request(request)
    provider = provider_for_settings()
    data = provider.get_pull_request(reference)
    repository_id = str(uuid5(NAMESPACE_URL, reference.full_name))
    commit_sha = data.metadata.get("head", {}).get("sha")
    review_key = f"{reference.full_name}#{reference.number}@{commit_sha}"
    lock = _lock_for(review_key)
    with lock, SessionLocal() as session:
            existing = session.scalar(select(ReviewRun).where(ReviewRun.review_key == review_key))
            if existing:
                return existing, True, reference, provider
            repository = session.get(Repository, repository_id)
            if repository is None:
                repository = Repository(id=repository_id, full_name=reference.full_name)
                session.add(repository)
            pull_request_id = str(uuid5(NAMESPACE_URL, f"{reference.full_name}#{reference.number}"))
            pull_request = session.get(PullRequest, pull_request_id)
            if pull_request is None:
                pull_request = PullRequest(id=pull_request_id, repository_id=repository_id, number=reference.number, title=data.metadata.get("title"), base_sha=data.metadata.get("base", {}).get("sha"), head_sha=commit_sha)
                session.add(pull_request)
            review = ReviewRun(id=str(uuid5(NAMESPACE_URL, f"review:{review_key}")), repository_id=repository_id, pull_request_id=pull_request_id, status=ReviewStatus.QUEUED.value, commit_sha=commit_sha, review_key=review_key)
            session.add(review)
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                existing = session.scalar(select(ReviewRun).where(ReviewRun.review_key == review_key))
                if existing:
                    return existing, True, reference, provider
                raise
            session.refresh(review)
            return review, False, reference, provider


def run_review(review_id: str, reference: PRReference, provider: object) -> None:
    started = time.perf_counter()
    settings = get_settings()
    with SessionLocal() as session:
        review = session.get(ReviewRun, review_id)
        if review is None:
            return
        review.status = ReviewStatus.RUNNING.value
        session.commit()
    try:
        graph = build_review_graph()
        result = graph.invoke({"reference": reference, "provider": provider, "settings": settings, "review_id": review_id, "retry_count": 0})
        with SessionLocal() as session:
            review = session.get(ReviewRun, review_id)
            if review is None:
                return
            for execution in result.get("agent_results", []):
                session.add(AgentExecution(review_run_id=review_id, agent_name=execution["task"], status="success", candidate_count=len(execution["findings"]), retry_count=result.get("retry_count", 0), usage_metadata={"requests": execution.get("usage_requests", 0)}))
            for failure in result.get("failures", []):
                if failure.get("kind") == "agent":
                    session.add(AgentExecution(review_run_id=review_id, agent_name=failure["task"], status=failure.get("status", "failed"), retry_count=result.get("retry_count", 0), error_code=failure.get("reason")))
            for tool in result.get("tool_results", []):
                session.add(ToolExecution(review_run_id=review_id, tool_name=tool.tool_name, status=tool.status.value, result_metadata={"reason": tool.reason, "finding_count": len(tool.findings)}))
            decisions = result.get("verification_decisions", [])
            for index, finding in enumerate(result.get("findings", [])):
                key = f"{finding.category}:{finding.file_path}:{finding.start_line}:{finding.title}"
                decision = decisions[index] if index < len(decisions) else None
                provenance = {"source": "mock_provider", "supporting_agents": finding.supporting_agents, "supporting_tools": finding.supporting_tools, "supporting_rule_ids": finding.supporting_rule_ids, "verification": decision.model_dump() if decision else {}}
                session.add(ReviewFinding(id=str(finding.finding_id), review_run_id=review_id, repository_id=review.repository_id, finding_key=key, category=finding.category.value, severity=finding.severity.value, confidence=finding.confidence, file_path=finding.file_path, start_line=finding.start_line, end_line=finding.end_line, title=finding.title, description=finding.description, evidence=finding.evidence, impact=finding.impact, remediation=finding.recommended_remediation, verification_status=finding.verification_status.value, provenance=provenance, publication_status=finding.publication_status.value))
                if decision:
                    session.add(VerificationDecision(finding_id=str(finding.finding_id), status=decision.status.value, explanation=decision.explanation, provenance={"reason_code": decision.reason_code, "checks": decision.provenance}))
            failures = result.get("failures", [])
            review.partial_failure = bool(failures)
            review.status = result.get("status", ReviewStatus.COMPLETED.value)
            review.latency_ms = int((time.perf_counter() - started) * 1000)
            review.usage_metadata = {"trace": result.get("trace", []), "failures": failures, "tool_statuses": [{"tool": tool.tool_name, "status": tool.status.value, "reason": tool.reason} for tool in result.get("tool_results", [])], "context_incomplete": result.get("context").incomplete if result.get("context") else False}
            session.commit()
    except Exception as exc:  # noqa: BLE001 - persist workflow failure state
        with SessionLocal() as session:
            review = session.get(ReviewRun, review_id)
            if review:
                review.status = ReviewStatus.FAILED.value
                review.partial_failure = True
                review.latency_ms = int((time.perf_counter() - started) * 1000)
                review.usage_metadata = {"failures": [{"kind": "workflow", "reason": type(exc).__name__}]}
                session.commit()


def list_reviews() -> list[ReviewRun]:
    Base.metadata.create_all(engine)
    with SessionLocal() as session:
        return list(session.scalars(select(ReviewRun).order_by(ReviewRun.created_at.desc())))


def get_review(review_id: str) -> ReviewRun | None:
    with SessionLocal() as session:
        return session.get(ReviewRun, review_id)


def get_findings(review_id: str) -> list[ReviewFinding]:
    with SessionLocal() as session:
        return list(session.scalars(select(ReviewFinding).where(ReviewFinding.review_run_id == review_id)))
