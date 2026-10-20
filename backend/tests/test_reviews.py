from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.agents.llm.mock import MockProvider
from app.analyzers.base import ToolRunResult, ToolStatus
from app.core.config import get_settings
from app.github.client import PullRequestData
from app.github.reference import PRReference
from app.graphs import review as review_graph
from app.graphs.review import build_review_graph
from app.main import app
from app.models.review import (
    AgentExecution,
    PullRequest,
    Repository,
    ReviewFinding,
    ReviewRun,
    ToolExecution,
)
from app.persistence.database import Base, SessionLocal, engine

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_review_rows() -> None:
    Base.metadata.create_all(engine)
    with SessionLocal() as session:
        for model in (ReviewFinding, AgentExecution, ToolExecution, ReviewRun, PullRequest, Repository):
            session.execute(delete(model))
        session.commit()


def test_small_review_runs_and_persists() -> None:
    response = client.post("/api/v1/reviews", json={"fixture_id": "small"})
    assert response.status_code == 202
    review_id = response.json()["review_id"]
    detail = client.get(f"/api/v1/reviews/{review_id}").json()
    assert detail["status"] in {"completed", "completed_with_errors"}
    findings = client.get(f"/api/v1/reviews/{review_id}/findings").json()
    trace = client.get(f"/api/v1/reviews/{review_id}/trace").json()
    assert findings
    assert {item["status"] for item in trace["tool_statuses"]} <= {"success", "unavailable", "failed", "timed_out"}


def test_large_review_reports_incomplete_context() -> None:
    response = client.post("/api/v1/reviews", json={"fixture_id": "large"})
    assert response.status_code == 202
    trace = client.get(f"/api/v1/reviews/{response.json()['review_id']}/trace").json()
    assert trace["status"] in {"completed", "completed_with_errors"}
    assert any(item.get("node") == "build_context" for item in trace["trace"])


def test_duplicate_review_returns_existing_review() -> None:
    first = client.post("/api/v1/reviews", json={"fixture_id": "small"}).json()
    second = client.post("/api/v1/reviews", json={"fixture_id": "small"}).json()
    assert second["existing"] is True
    assert second["review_id"] == first["review_id"]


def _graph_state():
    return {"reference": PRReference("synthetic", "demo", 1), "provider": __import__("app.github.client", fromlist=["FixturePullRequestProvider"]).FixturePullRequestProvider(), "settings": get_settings(), "retry_count": 0}


def test_one_agent_failure_preserves_other_findings(monkeypatch) -> None:
    def fail(self, context, tool_evidence=None):
        raise RuntimeError("synthetic agent failure")

    monkeypatch.setattr(review_graph.SecurityAnalysisAgent, "analyze", fail)
    result = build_review_graph().invoke(_graph_state())
    assert result["findings"]
    assert any(item["task"] == "security-analysis" for item in result["failures"])
    assert result["status"] == "completed_with_errors"


def test_failed_model_call_recovers_with_provider_retry(monkeypatch) -> None:
    monkeypatch.setattr(review_graph, "build_provider", lambda settings: MockProvider(failure_modes=["timeout"], max_retries=1))
    result = build_review_graph().invoke(_graph_state())
    assert result["status"] == "completed"


def test_unavailable_scanner_is_recorded_without_erasing_results(monkeypatch) -> None:
    monkeypatch.setattr(review_graph.SemgrepAdapter, "run", lambda self, root: ToolRunResult(tool_name="semgrep", status=ToolStatus.UNAVAILABLE, reason="not installed"))
    result = build_review_graph().invoke(_graph_state())
    assert result["findings"]
    assert any(tool.status is ToolStatus.UNAVAILABLE for tool in result["tool_results"])


def test_invalid_context_location_becomes_partial_failure() -> None:
    root = Path(__file__).parents[2] / "fixtures" / "sample_repositories" / "small_repo"

    class InvalidProvider:
        def get_pull_request(self, reference):
            return PullRequestData(metadata={"head": {"sha": "invalid"}}, files=[{"filename": "../escape.py"}], repository_root=root)

    result = build_review_graph().invoke({"reference": PRReference("synthetic", "demo", 99), "provider": InvalidProvider(), "settings": get_settings(), "retry_count": 0})
    assert result["status"] == "completed_with_errors"
    assert any(item["task"] == "context" for item in result["failures"])
