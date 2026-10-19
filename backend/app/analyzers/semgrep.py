import json
from pathlib import Path

from app.analyzers.base import RawToolFinding, ToolRunResult, ToolStatus, run_in_copy


class SemgrepAdapter:
    tool_name = "semgrep"

    def __init__(self, *, timeout_seconds: float = 20.0, rules_path: Path | None = None):
        self.timeout_seconds = timeout_seconds
        self.rules_path = rules_path or Path(__file__).parent / "rules" / "semgrep.yml"

    def run(self, repository_root: Path) -> ToolRunResult:
        result = run_in_copy(repository_root, ["semgrep", "--config", str(self.rules_path), "--metrics=off", "--json", "."], timeout_seconds=self.timeout_seconds)
        if result.status is not ToolStatus.SUCCESS:
            return ToolRunResult(tool_name=self.tool_name, status=result.status, reason=result.reason)
        try:
            payload = json.loads(result.stdout or "{}")
            findings = [RawToolFinding(rule_id=item["check_id"], severity=item.get("extra", {}).get("severity", "WARNING"), file_path=item.get("path"), start_line=item.get("start", {}).get("line"), end_line=item.get("end", {}).get("line"), evidence=item.get("extra", {}).get("lines"), message=item.get("extra", {}).get("message", ""), tool_name=self.tool_name) for item in payload.get("results", [])]
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            return ToolRunResult(tool_name=self.tool_name, status=ToolStatus.FAILED, reason=f"invalid Semgrep output: {type(exc).__name__}")
        return ToolRunResult(tool_name=self.tool_name, status=ToolStatus.SUCCESS, findings=findings, raw_output=payload)
