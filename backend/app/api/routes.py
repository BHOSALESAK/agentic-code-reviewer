from datetime import UTC, datetime

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from app.context.builder import build_context, parse_file_hunks
from app.core.config import get_settings
from app.github.client import FixturePullRequestProvider, GitHubClient, GitHubError
from app.github.reference import InvalidPRReference, PRReference, parse_pr_reference
from app.schemas.preview import FixtureSummary, PreviewRequest
from app.schemas.review import ReviewAccepted, ReviewRequest
from app.services.reviews import (
    create_queued_review,
    get_findings,
    get_review,
    list_reviews,
    run_review,
)

router = APIRouter(prefix="/api/v1")


class HealthResponse(BaseModel):
    status: str
    service: str
    environment: str
    demo_mode: bool
    timestamp: datetime


@router.get("/health", response_model=HealthResponse, tags=["system"])
def health_check() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        status="ok",
        service=settings.app_name,
        environment=settings.app_env,
        demo_mode=settings.demo_mode,
        timestamp=datetime.now(UTC),
    )


def _fixture_reference(fixture_id: str) -> PRReference:
    numbers = {"small": 1, "large": 2}
    if fixture_id not in numbers:
        raise HTTPException(status_code=404, detail="fixture not found")
    return PRReference("synthetic", "demo", numbers[fixture_id])


@router.get("/fixtures", response_model=list[FixtureSummary], tags=["fixtures"])
def list_fixtures() -> list[FixtureSummary]:
    provider = FixturePullRequestProvider()
    results = []
    for fixture_id in ("small", "large"):
        data = provider.get_pull_request(_fixture_reference(fixture_id))
        results.append(FixtureSummary(
            fixture_id=fixture_id,
            title=data.metadata["title"],
            number=data.metadata["number"],
            repository=data.metadata["base"]["repo"]["full_name"],
            changed_files=len(data.files),
        ))
    return results


@router.post("/pull-requests/preview", tags=["pull-requests"])
def preview_pull_request(request: PreviewRequest) -> dict:
    try:
        reference = _fixture_reference(request.fixture_id) if request.fixture_id else parse_pr_reference(request.reference or "")
        settings = get_settings()
        provider = FixturePullRequestProvider() if settings.demo_mode else GitHubClient(settings.github_token)
        data = provider.get_pull_request(reference)
        parsed_files = parse_file_hunks(data.files)
        context = build_context(data.repository_root, data.files)
        return {
            "metadata": data.metadata,
            "changed_files": parsed_files,
            "context": {
                "chunks": [chunk.__dict__ for chunk in context.chunks],
                "incomplete": context.incomplete,
                "incomplete_reasons": context.incomplete_reasons,
                "files_considered": context.files_considered,
                "files_included": context.files_included,
                "chunk_plan": [
                    {"file_path": chunk.file_path, "start_line": chunk.start_line, "end_line": chunk.end_line}
                    for chunk in context.chunks
                ],
            },
        }
    except InvalidPRReference as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except (GitHubError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _review_payload(review) -> dict:
    findings = get_findings(review.id)
    counts = {status: sum(finding.verification_status == status for finding in findings) for status in ("Verified", "Rejected", "Needs manual review", "Unverified")}
    return {
        "review_id": review.id,
        "status": review.status,
        "repository_id": review.repository_id,
        "pull_request_id": review.pull_request_id,
        "commit_sha": review.commit_sha,
        "partial_failure": review.partial_failure,
        "latency_ms": review.latency_ms,
        "created_at": review.created_at,
        "updated_at": review.updated_at,
        "verification_counts": counts,
    }


@router.post("/reviews", response_model=ReviewAccepted, status_code=202, tags=["reviews"])
def create_review(request: ReviewRequest, background_tasks: BackgroundTasks) -> ReviewAccepted:
    try:
        review, existing, reference, provider = create_queued_review(request)
        if not existing:
            background_tasks.add_task(run_review, review.id, reference, provider)
        return ReviewAccepted(review_id=review.id, status=review.status, existing=existing)
    except GitHubError as exc:
        raise HTTPException(status_code=exc.status_code or 400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/reviews", tags=["reviews"])
def reviews() -> list[dict]:
    return [_review_payload(review) for review in list_reviews()]


@router.get("/reviews/{review_id}", tags=["reviews"])
def review_detail(review_id: str) -> dict:
    review = get_review(review_id)
    if review is None:
        raise HTTPException(status_code=404, detail="review not found")
    return _review_payload(review)


@router.get("/reviews/{review_id}/findings", tags=["reviews"])
def review_findings(review_id: str, verification_status: str | None = None) -> dict:
    if get_review(review_id) is None:
        raise HTTPException(status_code=404, detail="review not found")
    findings = get_findings(review_id)
    counts = {status: sum(finding.verification_status == status for finding in findings) for status in ("Verified", "Rejected", "Needs manual review", "Unverified")}
    if verification_status:
        findings = [finding for finding in findings if finding.verification_status == verification_status]
    return {"findings": [{"finding_id": finding.id, "title": finding.title, "category": finding.category, "severity": finding.severity, "confidence": finding.confidence, "file_path": finding.file_path, "start_line": finding.start_line, "end_line": finding.end_line, "verification_status": finding.verification_status, "verification_reason": (finding.provenance or {}).get("verification", {}).get("reason_code"), "verification_explanation": (finding.provenance or {}).get("verification", {}).get("explanation"), "evidence": finding.evidence, "provenance": finding.provenance} for finding in findings], "counts": counts}


@router.get("/reviews/{review_id}/trace", tags=["reviews"])
def review_trace(review_id: str) -> dict:
    review = get_review(review_id)
    if review is None:
        raise HTTPException(status_code=404, detail="review not found")
    metadata = review.usage_metadata or {}
    return {"review_id": review_id, "status": review.status, "trace": metadata.get("trace", []), "failures": metadata.get("failures", []), "tool_statuses": metadata.get("tool_statuses", []), "verification_counts": _review_payload(review)["verification_counts"]}
