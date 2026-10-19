from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.schemas.finding import Finding, IssueCategory, Severity


def valid_finding(**overrides: object) -> dict:
    payload = {
        "review_id": uuid4(),
        "repository_id": uuid4(),
        "pull_request_number": 4,
        "category": IssueCategory.SECURITY,
        "title": "Unsafe input handling",
        "description": "User input reaches a sensitive operation.",
        "severity": Severity.HIGH,
        "confidence": 0.8,
        "file_path": "src/handler.py",
        "start_line": 10,
        "end_line": 12,
    }
    payload.update(overrides)
    return payload


def test_finding_accepts_valid_payload() -> None:
    finding = Finding.model_validate(valid_finding())
    assert finding.confidence == 0.8


@pytest.mark.parametrize(
    "overrides",
    [
        {"confidence": 1.1},
        {"start_line": 12, "end_line": 10},
        {"start_line": 10, "end_line": None},
        {"file_path": "../secrets.txt"},
    ],
)
def test_finding_rejects_invalid_location_or_confidence(overrides: dict) -> None:
    with pytest.raises(ValidationError):
        Finding.model_validate(valid_finding(**overrides))


def test_settings_use_environment_values(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("FRONTEND_ORIGINS", "http://test.local,http://test.local:5173")
    settings = Settings()
    assert settings.app_env == "test"
    assert settings.cors_origins == ["http://test.local", "http://test.local:5173"]
    assert settings.database_url.startswith("sqlite")
