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
        if response_model.__name__ == "CriticResponse":
            return {"supported": True, "remediation_addressed": True, "explanation": "The candidate follows from the delimited fixture evidence."}
        if response_model is not AgentResponse:
            raise LLMProviderError("mock response model is unsupported")
        category = self._category_from_prompt(prompt)
        finding = self._finding(category, prompt)
        findings = [finding] if finding else []
        if finding and category is IssueCategory.BUG_LOGIC:
            findings.append(self._hallucinated_finding())
        return {"findings": findings}

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
            IssueCategory.SECURITY: ("SQL query uses untrusted input", "app.py", 5, Severity.HIGH, "query = f\"SELECT * FROM users WHERE name = '{username}'\"", "Parameterize the SQL query."),
            IssueCategory.BUG_LOGIC: ("Pagination accepts an out-of-range index", "app.py", 18, Severity.MEDIUM, "if index > len(items):", "Reject indexes greater than or equal to the list length."),
            IssueCategory.ERROR_HANDLING: ("File-read failure is swallowed", "app.py", 13, Severity.MEDIUM, "pass", "Report or propagate the read failure."),
            IssueCategory.TEST_ADEQUACY: ("Boundary behavior lacks a regression test", "tests/test_app.py", 1, Severity.LOW, "assert page([\"first\"], 0) == \"first\"", "Add tests for the empty and upper-bound cases."),
            IssueCategory.DEPENDENCY: ("Pinned dependency has known vulnerability risk", "requirements.txt", 1, Severity.HIGH, "requests==2.19.0", "Upgrade and constrain a currently supported dependency version."),
        }[category]
        title, path, line, severity, evidence, remediation = details
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
            evidence=evidence,
            impact="The changed behavior may affect reliability or security.",
            recommended_remediation=remediation,
            verification_status=VerificationStatus.UNVERIFIED,
            supporting_tools=[],
            supporting_rule_ids=[],
            is_changed_line=True,
        ).model_dump()

    @staticmethod
    def _hallucinated_finding() -> dict[str, Any]:
        return Finding(
            finding_id=uuid5(NAMESPACE_URL, "mock:hallucinated-file"),
            review_id=uuid5(NAMESPACE_URL, "synthetic/demo#1"),
            repository_id=uuid5(NAMESPACE_URL, "synthetic/demo"),
            pull_request_number=1,
            commit_sha="head-small-0001",
            category=IssueCategory.BUG_LOGIC,
            title="Synthetic unsupported issue",
            description="Synthetic hallucinated candidate for demonstration.",
            severity=Severity.MEDIUM,
            confidence=0.9,
            file_path="missing_file.py",
            start_line=99,
            end_line=99,
            evidence="This line does not exist.",
            impact="Synthetic unsupported impact.",
            recommended_remediation="Do not apply.",
            verification_status=VerificationStatus.UNVERIFIED,
        ).model_dump()
