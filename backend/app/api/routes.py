from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.context.builder import build_context, parse_file_hunks
from app.core.config import get_settings
from app.github.client import FixturePullRequestProvider, GitHubClient, GitHubError
from app.github.reference import InvalidPRReference, PRReference, parse_pr_reference
from app.schemas.preview import FixtureSummary, PreviewRequest

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
