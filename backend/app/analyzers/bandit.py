import json
from pathlib import Path

from app.analyzers.base import RawToolFinding, ToolRunResult, ToolStatus, run_in_copy


class BanditAdapter:
    tool_name = "bandit"

    def __init__(self, *, timeout_seconds: float = 20.0):
        self.timeout_seconds = timeout_seconds

    def run(self, repository_root: Path) -> ToolRunResult:
        result = run_in_copy(repository_root, ["bandit", "-r", ".", "-f", "json"], timeout_seconds=self.timeout_seconds)
        if result.status is ToolStatus.FAILED and not result.stdout:
            return ToolRunResult(tool_name=self.tool_name, status=result.status, reason=result.reason)
        if result.status is ToolStatus.TIMED_OUT or result.status is ToolStatus.UNAVAILABLE:
            return ToolRunResult(tool_name=self.tool_name, status=result.status, reason=result.reason)
        try:
            payload = json.loads(result.stdout or "{}")
            findings = [RawToolFinding(rule_id=item["test_id"], severity=item.get("issue_severity", "UNDEFINED"), file_path=item.get("filename"), start_line=item.get("line_number"), end_line=item.get("line_number"), evidence=item.get("code"), message=item.get("issue_text", ""), tool_name=self.tool_name) for item in payload.get("results", [])]
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            return ToolRunResult(tool_name=self.tool_name, status=ToolStatus.FAILED, reason=f"invalid Bandit output: {type(exc).__name__}")
        return ToolRunResult(tool_name=self.tool_name, status=ToolStatus.SUCCESS, findings=findings, raw_output=payload)
