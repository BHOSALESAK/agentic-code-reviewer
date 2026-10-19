from pathlib import Path

from app.agents.llm.mock import MockProvider
from app.agents.specialists import (
    BugLogicAnalysisAgent,
    ErrorHandlingAnalysisAgent,
    SecurityAnalysisAgent,
    TestAdequacyAgent,
)
from app.context.builder import ContextChunk


def test_each_specialist_returns_unverified_mock_finding() -> None:
    context = ContextChunk("app.py", "query = f'unsafe'", 1, 1)
    for agent in (SecurityAnalysisAgent, BugLogicAnalysisAgent, ErrorHandlingAnalysisAgent):
        result = agent(MockProvider()).analyze(context)
        assert result.findings
        assert result.findings[0].verification_status.value == "Unverified"


def test_test_agent_checks_test_context_before_claiming_missing_tests() -> None:
    provider = MockProvider()
    agent = TestAdequacyAgent(provider)
    no_test_context = agent.analyze(ContextChunk("app.py", "return value", 1, 1))
    assert no_test_context.findings == []
    test_context = agent.analyze(ContextChunk("tests/test_app.py", "def test_boundary(): pass", 1, 1))
    assert test_context.findings


def test_repository_prompt_injection_is_delimited_and_not_followed() -> None:
    malicious = Path(__file__).parents[2] / "fixtures" / "sample_repositories" / "small_repo" / "prompt_injection.py"
    content = malicious.read_text(encoding="utf-8")
    result = SecurityAnalysisAgent(MockProvider()).analyze(ContextChunk("prompt_injection.py", content, 1, 3))
    assert "<UNTRUSTED_REPOSITORY_CONTENT" in result.prompt
    assert all("Ignore the reviewer" not in finding.title for finding in result.findings)
