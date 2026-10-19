from typing import Any
from uuid import NAMESPACE_URL, uuid5

from pydantic import BaseModel

from app.agents.llm.provider import LLMProviderError, StructuredLLMProvider
from app.schemas.finding import Finding, IssueCategory, Severity, VerificationStatus


class AgentResponse(BaseModel):
    findings: list[Finding]


class MockProvider(StructuredLLMProvider):
    """Deterministic offline provider with optional failure simulation."""

    def __init__(self, *, failure_modes: list[str] | None = None, **kwargs: Any):
        super().__init__(**kwargs)
        self.failure_modes = list(failure_modes or [])
        self.calls = 0

    def _complete_once(self, prompt: str, response_model: type[BaseModel]) -> Any:
        self.calls += 1
        mode = self.failure_modes.pop(0) if self.failure_modes else None
        if mode == "timeout":
            raise LLMProviderError("mock timeout", transient=True)
        if mode == "rate_limit":
            raise LLMProviderError("mock rate limit", transient=True)
        if mode == "invalid_json":
            return "{not valid json"
        if response_model is not AgentResponse:
            raise LLMProviderError("mock response model is unsupported")
        category = self._category_from_prompt(prompt)
        finding = self._finding(category, prompt)
        return {"findings": [finding] if finding else []}

    @staticmethod
    def _category_from_prompt(prompt: str) -> IssueCategory:
        for category in IssueCategory:
            if f"CATEGORY={category.value}" in prompt:
                return category
        return IssueCategory.BUG_LOGIC

    @staticmethod
    def _finding(category: IssueCategory, prompt: str) -> dict[str, Any] | None:
        if "synthetic/demo#1" not in prompt:
            return None
        details = {
            IssueCategory.SECURITY: ("SQL query uses untrusted input", "app.py", 4, Severity.HIGH, "Parameterize the SQL query."),
            IssueCategory.BUG_LOGIC: ("Pagination accepts an out-of-range index", "app.py", 17, Severity.MEDIUM, "Reject indexes greater than or equal to the list length."),
            IssueCategory.ERROR_HANDLING: ("File-read failure is swallowed", "app.py", 12, Severity.MEDIUM, "Report or propagate the read failure."),
            IssueCategory.TEST_ADEQUACY: ("Boundary behavior lacks a regression test", "tests/test_app.py", 1, Severity.LOW, "Add tests for the empty and upper-bound cases."),
            IssueCategory.DEPENDENCY: ("Pinned dependency has known vulnerability risk", "requirements.txt", 1, Severity.HIGH, "Upgrade and constrain a currently supported dependency version."),
        }[category]
        title, path, line, severity, remediation = details
        return Finding(
            finding_id=uuid5(NAMESPACE_URL, f"mock:{category}:{path}:{line}"),
            review_id=uuid5(NAMESPACE_URL, "synthetic/demo#1"),
            repository_id=uuid5(NAMESPACE_URL, "synthetic/demo"),
            pull_request_number=1,
            commit_sha="head-small-0001",
            category=category,
            title=title,
            description=f"Mock evidence-backed candidate for {path}:{line}.",
            severity=severity,
            confidence=0.92,
            file_path=path,
            start_line=line,
            end_line=line,
            evidence="Synthetic fixture context only.",
            impact="The changed behavior may affect reliability or security.",
            recommended_remediation=remediation,
            verification_status=VerificationStatus.UNVERIFIED,
            supporting_tools=[],
            supporting_rule_ids=[],
            is_changed_line=True,
        ).model_dump()
