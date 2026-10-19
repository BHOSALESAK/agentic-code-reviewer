import json
from pathlib import Path

from app.analyzers.base import RawToolFinding, ToolRunResult, ToolStatus, run_in_copy


class PipAuditAdapter:
    tool_name = "pip-audit"

    def __init__(self, *, timeout_seconds: float = 30.0, recorded_output: Path | None = None):
        self.timeout_seconds = timeout_seconds
        self.recorded_output = recorded_output or Path(__file__).resolve().parents[3] / "fixtures" / "tool_outputs" / "pip-audit.json"

    def run(self, repository_root: Path, *, demo_mode: bool = False) -> ToolRunResult:
        if demo_mode:
            if not self.recorded_output.is_file():
                return ToolRunResult(tool_name=self.tool_name, status=ToolStatus.UNAVAILABLE, reason="recorded demo output is missing")
            payload = json.loads(self.recorded_output.read_text(encoding="utf-8"))
            return self._normalize(payload, "recorded synthetic output; no network scan was run")
        result = run_in_copy(repository_root, ["pip-audit", "-r", "requirements.txt", "-f", "json"], timeout_seconds=self.timeout_seconds)
        if result.status is ToolStatus.FAILED and result.stdout:
            try:
                return self._normalize(json.loads(result.stdout), "pip-audit exited nonzero because vulnerabilities were reported")
            except json.JSONDecodeError:
                pass
        if result.status is not ToolStatus.SUCCESS:
            return ToolRunResult(tool_name=self.tool_name, status=result.status, reason=result.reason)
        try:
            return self._normalize(json.loads(result.stdout or "{}"), None)
        except json.JSONDecodeError as exc:
            return ToolRunResult(tool_name=self.tool_name, status=ToolStatus.FAILED, reason=f"invalid pip-audit output: {type(exc).__name__}")

    def _normalize(self, payload: dict, reason: str | None) -> ToolRunResult:
        findings = []
        for dependency in payload.get("dependencies", []):
            for vulnerability in dependency.get("vulns", []):
                findings.append(RawToolFinding(rule_id=vulnerability.get("id", "unknown"), severity="HIGH", evidence=dependency.get("version"), message=vulnerability.get("description", "Known dependency vulnerability"), tool_name=self.tool_name))
        return ToolRunResult(tool_name=self.tool_name, status=ToolStatus.SUCCESS, findings=findings, reason=reason, raw_output=payload)
