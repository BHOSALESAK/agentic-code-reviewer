import json
from pathlib import Path

import pytest

from app.analyzers.bandit import BanditAdapter
from app.analyzers.base import CommandResult, ToolStatus
from app.analyzers.pip_audit import PipAuditAdapter
from app.analyzers.semgrep import SemgrepAdapter

ROOT = Path(__file__).parents[2] / "fixtures" / "sample_repositories" / "small_repo"


@pytest.mark.parametrize("adapter", [SemgrepAdapter(), BanditAdapter()])
def test_command_analyzers_normalize_findings(monkeypatch: pytest.MonkeyPatch, adapter) -> None:
    if isinstance(adapter, SemgrepAdapter):
        payload = {"results": [{"check_id": "rule.x", "path": "app.py", "start": {"line": 4}, "end": {"line": 4}, "extra": {"severity": "WARNING", "message": "issue", "lines": "code"}}]}
        target = "app.analyzers.semgrep.run_in_copy"
    else:
        payload = {"results": [{"test_id": "B101", "filename": "app.py", "line_number": 2, "issue_severity": "LOW", "issue_text": "issue", "code": "code"}]}
        target = "app.analyzers.bandit.run_in_copy"
    monkeypatch.setattr(target, lambda *args, **kwargs: CommandResult(ToolStatus.SUCCESS, json.dumps(payload)))
    result = adapter.run(ROOT)
    assert result.status is ToolStatus.SUCCESS
    assert result.findings[0].rule_id
    assert result.findings[0].file_path == "app.py"


@pytest.mark.parametrize("adapter", [SemgrepAdapter(), BanditAdapter()])
def test_command_analyzers_report_unavailable(monkeypatch: pytest.MonkeyPatch, adapter) -> None:
    target = "app.analyzers.semgrep.run_in_copy" if isinstance(adapter, SemgrepAdapter) else "app.analyzers.bandit.run_in_copy"
    monkeypatch.setattr(target, lambda *args, **kwargs: CommandResult(ToolStatus.UNAVAILABLE, reason="missing executable"))
    result = adapter.run(ROOT)
    assert result.status is ToolStatus.UNAVAILABLE
    assert not result.findings


def test_command_analyzers_report_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.analyzers.bandit.run_in_copy", lambda *args, **kwargs: CommandResult(ToolStatus.TIMED_OUT, reason="deadline"))
    result = BanditAdapter().run(ROOT)
    assert result.status is ToolStatus.TIMED_OUT


def test_pip_audit_uses_labelled_recorded_demo_output() -> None:
    result = PipAuditAdapter().run(ROOT, demo_mode=True)
    assert result.status is ToolStatus.SUCCESS
    assert result.reason and "recorded synthetic" in result.reason
    assert result.findings[0].rule_id == "CVE-SYNTHETIC-REQUESTS"
