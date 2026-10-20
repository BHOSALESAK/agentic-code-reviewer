from concurrent.futures import ThreadPoolExecutor, as_completed
from operator import add
from typing import Annotated, Any, TypedDict

from langgraph.graph import END, START, StateGraph

from app.agents.llm.factory import build_provider
from app.agents.specialists import (
    BugLogicAnalysisAgent,
    ErrorHandlingAnalysisAgent,
    SecurityAnalysisAgent,
    SpecialistAgent,
    TestAdequacyAgent,
)
from app.analyzers.bandit import BanditAdapter
from app.analyzers.base import ToolRunResult, ToolStatus
from app.analyzers.pip_audit import PipAuditAdapter
from app.analyzers.semgrep import SemgrepAdapter
from app.context.builder import ContextChunk, ContextLimits, ContextSummary, build_context
from app.github.client import PullRequestData, PullRequestProvider
from app.github.reference import PRReference
from app.schemas.finding import Finding
from app.verification.critic import Critic
from app.verification.dedupe import merge_duplicate_candidates
from app.verification.models import VerificationDecision, VerificationOutcome


class ReviewState(TypedDict, total=False):
    request: Any
    reference: PRReference
    provider: PullRequestProvider
    settings: Any
    review_id: str
    metadata: dict[str, Any]
    pull_request: PullRequestData
    context: ContextSummary
    chunks: list[ContextChunk]
    findings: list[Finding]
    agent_results: list[dict[str, Any]]
    tool_results: list[ToolRunResult]
    failures: list[dict[str, Any]]
    pending_failures: list[dict[str, Any]]
    retry_count: int
    trace: Annotated[list[dict[str, Any]], add]
    status: str
    verification_decisions: list[VerificationDecision]
    llm_provider: Any


def _context_for_agent(chunks: list[ContextChunk], agent: SpecialistAgent) -> ContextChunk:
    if isinstance(agent, TestAdequacyAgent):
        return next((chunk for chunk in chunks if chunk.file_path.startswith("tests/")), chunks[0])
    return next((chunk for chunk in chunks if chunk.file_path.endswith(".py")), chunks[0])


def build_review_graph(*, persist: Any | None = None):
    graph = StateGraph(ReviewState)

    def validate(state: ReviewState) -> ReviewState:
        if not state.get("reference") or not state.get("provider"):
            raise ValueError("review request and provider are required")
        return {"status": "running", "trace": [{"node": "validate_request", "status": "success"}]}

    def fetch(state: ReviewState) -> ReviewState:
        data = state["provider"].get_pull_request(state["reference"])
        return {"pull_request": data, "metadata": data.metadata, "trace": [{"node": "fetch_pull_request", "status": "success"}]}

    def context(state: ReviewState) -> ReviewState:
        data = state["pull_request"]
        if data.repository_root is None:
            return {"context": ContextSummary([], True, ["repository source files were not available"], len(data.files), 0), "chunks": [], "failures": [{"task": "context", "kind": "context", "status": "failed", "reason": "repository source files unavailable"}], "trace": [{"node": "build_context", "status": "failed", "reason": "repository source files unavailable"}]}
        try:
            summary = build_context(data.repository_root, data.files, ContextLimits())
        except (OSError, ValueError) as exc:
            return {"context": ContextSummary([], True, [str(exc)], len(data.files), 0), "chunks": [], "failures": [{"task": "context", "kind": "context", "status": "failed", "reason": type(exc).__name__}], "trace": [{"node": "build_context", "status": "failed", "reason": type(exc).__name__}]}
        return {"context": summary, "chunks": summary.chunks, "trace": [{"node": "build_context", "status": "success", "incomplete": summary.incomplete}]}

    def plan(state: ReviewState) -> ReviewState:
        return {"trace": [{"node": "plan_review_tasks", "status": "success", "chunk_count": len(state["chunks"])}]}

    def analyze(state: ReviewState) -> ReviewState:
        provider = state.get("llm_provider") or build_provider(state["settings"])
        agents: list[SpecialistAgent] = [SecurityAnalysisAgent(provider), BugLogicAnalysisAgent(provider), ErrorHandlingAnalysisAgent(provider), TestAdequacyAgent(provider)]
        if state.get("pending_failures"):
            failed_names = {item["task"] for item in state["pending_failures"]}
            agents = [agent for agent in agents if agent.name in failed_names]
        review_reference = f"{state['reference'].full_name}#{state['reference'].number}"
        tasks: list[tuple[str, Any]] = [(agent.name, lambda agent=agent: agent.analyze(_context_for_agent(state["chunks"], agent), state.get("tool_results", []), review_reference)) for agent in agents]
        def run_tool(name: str, adapter: Any) -> ToolRunResult:
            if name == "pip-audit":
                return adapter.run(state["pull_request"].repository_root, demo_mode=state["settings"].demo_mode)
            return adapter.run(state["pull_request"].repository_root)

        for name, adapter in [("semgrep", SemgrepAdapter()), ("bandit", BanditAdapter()), ("pip-audit", PipAuditAdapter())]:
            if not state.get("pending_failures") or name in {item["task"] for item in state["pending_failures"]}:
                tasks.append((name, lambda name=name, adapter=adapter: run_tool(name, adapter)))
        results: list[dict[str, Any]] = []
        tool_results = list(state.get("tool_results", []))
        current_failures: list[dict[str, Any]] = []
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {executor.submit(task): name for name, task in tasks}
            for future in as_completed(futures):
                name = futures[future]
                try:
                    result = future.result()
                    if isinstance(result, ToolRunResult):
                        tool_results.append(result)
                        if result.status in {ToolStatus.FAILED, ToolStatus.TIMED_OUT}:
                            current_failures.append({"task": name, "kind": "scanner", "status": result.status.value, "reason": result.reason})
                    else:
                        results.append({"task": name, "findings": result.findings, "usage_requests": result.usage_requests})
                except Exception as exc:  # noqa: BLE001 - isolate one task failure
                    current_failures.append({"task": name, "kind": "agent", "status": "failed", "reason": type(exc).__name__})
        failures = list(state.get("failures", [])) + current_failures
        trace = [{"node": "parallel_analysis", "status": "completed", "failures": len(current_failures)}]
        return {"agent_results": list(state.get("agent_results", [])) + results, "tool_results": tool_results, "failures": failures, "pending_failures": current_failures, "llm_provider": provider, "trace": trace}

    def aggregate(state: ReviewState) -> ReviewState:
        findings = merge_duplicate_candidates(state.get("agent_results", []))
        return {"findings": findings, "trace": [{"node": "aggregate_findings", "status": "success", "candidate_count": len(findings)}]}

    def retry_route(state: ReviewState) -> str:
        retryable = {"failed", "timed_out"}
        pending = [item for item in state.get("pending_failures", []) if item.get("kind") == "agent" or item.get("status") in retryable]
        return "retry" if pending and state.get("retry_count", 0) < 1 else "verify"

    def retry(state: ReviewState) -> ReviewState:
        return {"retry_count": state.get("retry_count", 0) + 1, "trace": [{"node": "retry_recoverable_failures", "status": "retrying"}]}

    def verify(state: ReviewState) -> ReviewState:
        pull_request = state["pull_request"]
        provider = state.get("llm_provider") or build_provider(state["settings"])
        critic = Critic(provider, min_confidence=state["settings"].verification_min_confidence)
        verified_findings: list[Finding] = []
        decisions: list[VerificationDecision] = []
        failures = list(state.get("failures", []))
        for finding in state.get("findings", []):
            updated, decision = critic.verify(finding, repository_root=pull_request.repository_root or __import__("pathlib").Path("."), changed_files=pull_request.files, tool_results=state.get("tool_results", []), review_reference=f"{state['reference'].full_name}#{state['reference'].number}")
            verified_findings.append(updated)
            decisions.append(decision)
            if decision.reason_code == "CRITIC_CALL_FAILED":
                failures.append({"task": "critic", "kind": "verification", "status": "needs_manual_review", "reason": decision.explanation})
        counts = {outcome.value: sum(decision.status is outcome for decision in decisions) for outcome in VerificationOutcome}
        return {"findings": verified_findings, "verification_decisions": decisions, "failures": failures, "trace": [{"node": "verification", "status": "completed", "counts": counts, "confidence_note": "confidence is not a calibrated probability"}]}

    def assign(state: ReviewState) -> ReviewState:
        return {"trace": [{"node": "assign_severity_confidence", "status": "success", "rule": "retain validated values; confidence is not calibrated probability"}]}

    def save(state: ReviewState) -> ReviewState:
        if persist:
            persist(state)
        status = "completed_with_errors" if state.get("failures") else "completed"
        return {"status": status, "trace": [{"node": "persist_review", "status": "success"}]}

    graph.add_node("validate", validate)
    graph.add_node("fetch", fetch)
    graph.add_node("context", context)
    graph.add_node("plan", plan)
    graph.add_node("analyze", analyze)
    graph.add_node("aggregate", aggregate)
    graph.add_node("retry", retry)
    graph.add_node("verify", verify)
    graph.add_node("assign", assign)
    graph.add_node("save", save)
    graph.add_edge(START, "validate")
    graph.add_edge("validate", "fetch")
    graph.add_edge("fetch", "context")
    graph.add_edge("context", "plan")
    graph.add_edge("plan", "analyze")
    graph.add_edge("analyze", "aggregate")
    graph.add_conditional_edges("aggregate", retry_route, {"retry": "retry", "verify": "verify"})
    graph.add_edge("retry", "analyze")
    graph.add_edge("verify", "assign")
    graph.add_edge("assign", "save")
    graph.add_edge("save", END)
    return graph.compile()
