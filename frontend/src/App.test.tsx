import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import App from "./App";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter } from "react-router-dom";

const preview = {
  metadata: { title: "Add user lookup", number: 1, user: { login: "fixture-author" }, base: { sha: "base" }, head: { sha: "head" } },
  changed_files: [{ filename: "app.py", status: "modified", additions: 2, deletions: 1, hunks: [{ old_start: 1, old_count: 1, new_start: 1, new_count: 2, lines: [{ kind: "added", content: "new line", old_line: null, new_line: 1 }] }] }],
  context: { chunks: [{ file_path: "app.py", start_line: 1, end_line: 2, content: "new line" }], incomplete: true, incomplete_reasons: ["file-count limit reached"], files_considered: 1, files_included: 1, chunk_plan: [{ file_path: "app.py", start_line: 1, end_line: 2 }] },
};
const reviewId = "review-1";
const findingData = {
  finding_id: "finding-1", title: "Unsafe query", category: "Security", severity: "High", confidence: 0.92, file_path: "app.py", start_line: 5, end_line: 5, verification_status: "Verified", verification_reason: "EVIDENCE_SUPPORTED", verification_explanation: "Evidence is supported.", evidence: "query = unsafe", provenance: { supporting_tools: ["semgrep"], supporting_rule_ids: ["rule.sql"], verification: { provenance: ["file_exists", "critic"] } },
};
const rejectedFinding = { ...findingData, finding_id: "finding-2", title: "Unsupported candidate", verification_status: "Rejected", verification_reason: "FILE_NOT_FOUND", verification_explanation: "The file does not exist." };

function renderApp() {
  return render(<QueryClientProvider client={new QueryClient()}><BrowserRouter><App /></BrowserRouter></QueryClientProvider>);
}

beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url.endsWith("/health")) return Promise.resolve(new Response(JSON.stringify({ status: "ok", environment: "demo", demo_mode: true }), { status: 200 }));
    if (url.endsWith("/fixtures")) return Promise.resolve(new Response(JSON.stringify([{ fixture_id: "small", title: "Small fixture", number: 1, repository: "synthetic/demo", changed_files: 1, synthetic: true }]), { status: 200 }));
    if (url.endsWith("/preview") && init?.method === "POST") return Promise.resolve(new Response(JSON.stringify(preview), { status: 200 }));
    return Promise.resolve(new Response(JSON.stringify({ error: { message: "Not found" } }), { status: 404 }));
  }));
});
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

describe("dashboard", () => {
  it("navigates to the review workspace", async () => {
    renderApp();
    await screen.findByText("API online");
    fireEvent.click(screen.getByRole("link", { name: /Review a PR/i }));
    expect(await screen.findByRole("heading", { name: /Inspect a pull request/i })).toBeInTheDocument();
  });

  it("shows inline validation for an invalid reference", async () => {
    renderApp();
    fireEvent.click(await screen.findByRole("link", { name: /Review a PR/i }));
    await screen.findByRole("heading", { name: /Inspect a pull request/i });
    fireEvent.change(screen.getByPlaceholderText("owner/repository#42"), { target: { value: "bad reference" } });
    expect(screen.getByText("Use owner/repository#number or a GitHub pull-request URL.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Load pull request/i })).toBeDisabled();
  });

  it("renders the fixture preview and incomplete context notice", async () => {
    renderApp();
    fireEvent.click(await screen.findByRole("link", { name: /Review a PR/i }));
    await screen.findByRole("heading", { name: /Inspect a pull request/i });
    fireEvent.click(screen.getByRole("button", { name: /Load pull request/i }));
    expect(await screen.findByRole("heading", { name: /Add user lookup/i })).toBeInTheDocument();
    expect(screen.getByText("Context incomplete")).toBeInTheDocument();
    expect(screen.getByText("new line")).toBeInTheDocument();
  });

  it("shows a loading skeleton while the preview request is pending", async () => {
    const fetchMock = vi.mocked(fetch);
    fetchMock.mockImplementation((input: RequestInfo | URL) => {
      if (String(input).endsWith("/health")) return Promise.resolve(new Response(JSON.stringify({ status: "ok", environment: "demo", demo_mode: true }), { status: 200 }));
      if (String(input).endsWith("/fixtures")) return Promise.resolve(new Response(JSON.stringify([]), { status: 200 }));
      return new Promise(() => {});
    });
    renderApp();
    fireEvent.click(await screen.findByRole("link", { name: /Review a PR/i }));
    await screen.findByRole("heading", { name: /Inspect a pull request/i });
    fireEvent.click(screen.getByRole("button", { name: /Load pull request/i }));
    expect(screen.getByLabelText("Loading pull request")).toBeInTheDocument();
  });

  it("shows a request error with retry", async () => {
    const fetchMock = vi.mocked(fetch);
    fetchMock.mockImplementation((input: RequestInfo | URL) => {
      if (String(input).endsWith("/health")) return Promise.resolve(new Response(JSON.stringify({ status: "ok", environment: "demo", demo_mode: true }), { status: 200 }));
      if (String(input).endsWith("/fixtures")) return Promise.resolve(new Response(JSON.stringify([]), { status: 200 }));
      return Promise.resolve(new Response(JSON.stringify({ error: { message: "Fixture unavailable" } }), { status: 404 }));
    });
    renderApp();
    fireEvent.click(await screen.findByRole("link", { name: /Review a PR/i }));
    await screen.findByRole("heading", { name: /Inspect a pull request/i });
    fireEvent.click(screen.getByRole("button", { name: /Load pull request/i }));
    expect(await screen.findByText("Fixture unavailable")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
  });

  it("starts a review and polls until completion", async () => {
    let polls = 0;
    const fetchMock = vi.mocked(fetch);
    fetchMock.mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/health")) return Promise.resolve(new Response(JSON.stringify({ status: "ok", environment: "demo", demo_mode: true }), { status: 200 }));
      if (url.endsWith("/fixtures")) return Promise.resolve(new Response(JSON.stringify([{ fixture_id: "small", title: "Small fixture", number: 1, repository: "synthetic/demo", changed_files: 1, synthetic: true }]), { status: 200 }));
      if (url.endsWith("/preview")) return Promise.resolve(new Response(JSON.stringify(preview), { status: 200 }));
      if (url.endsWith("/reviews") && init?.method === "POST") return Promise.resolve(new Response(JSON.stringify({ review_id: reviewId, status: "queued", existing: false }), { status: 202 }));
      if (url.endsWith(`/reviews/${reviewId}`)) { polls += 1; return Promise.resolve(new Response(JSON.stringify({ review_id: reviewId, status: polls > 1 ? "completed" : "running", commit_sha: "head", partial_failure: false, latency_ms: 10, created_at: "2026-01-01", updated_at: "2026-01-01", verification_counts: { Verified: 1, Rejected: 0, "Needs manual review": 0, Unverified: 0 }, repository_id: "repo", pull_request_id: "pr" }), { status: 200 })); }
      if (url.endsWith(`/reviews/${reviewId}/findings`)) return Promise.resolve(new Response(JSON.stringify({ findings: [findingData], counts: { Verified: 1, Rejected: 0, "Needs manual review": 0, Unverified: 0 } }), { status: 200 }));
      return Promise.resolve(new Response(JSON.stringify({ error: { message: "Not found" } }), { status: 404 }));
    });
    renderApp();
    fireEvent.click(await screen.findByRole("link", { name: /Review a PR/i }));
    await screen.findByRole("heading", { name: /Inspect a pull request/i });
    fireEvent.click(screen.getByRole("button", { name: /Load pull request/i }));
    await screen.findByRole("heading", { name: /Add user lookup/i });
    fireEvent.click(screen.getByRole("button", { name: "Start review" }));
    expect(await screen.findByText("Review complete")).toBeInTheDocument();
  });

  it("filters findings and hides rejected candidates by default", async () => {
    window.history.pushState({}, "", "/findings");
    const fetchMock = vi.mocked(fetch);
    fetchMock.mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/health")) return Promise.resolve(new Response(JSON.stringify({ status: "ok", environment: "demo", demo_mode: true }), { status: 200 }));
      if (url.endsWith("/reviews")) return Promise.resolve(new Response(JSON.stringify([{ review_id: reviewId, status: "completed", commit_sha: "head", partial_failure: false, latency_ms: 10, created_at: "2026-01-01", updated_at: "2026-01-01", verification_counts: { Verified: 1, Rejected: 1, "Needs manual review": 0, Unverified: 0 } }]), { status: 200 }));
      return Promise.resolve(new Response(JSON.stringify({ findings: [findingData, rejectedFinding], counts: { Verified: 1, Rejected: 1, "Needs manual review": 0, Unverified: 0 } }), { status: 200 }));
    });
    renderApp();
    expect(await screen.findByRole("heading", { name: "Findings." })).toBeInTheDocument();
    expect(await screen.findByText("Unsafe query")).toBeInTheDocument();
    expect(screen.queryByText("Unsupported candidate")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("checkbox", { name: /Show rejected/i }));
    expect(await screen.findByText("Rejected: FILE_NOT_FOUND")).toBeInTheDocument();
    fireEvent.change(screen.getByPlaceholderText("Title, file or evidence"), { target: { value: "Unsafe" } });
    expect(screen.getByText("Unsafe query")).toBeInTheDocument();
    expect(screen.queryByText("Unsupported candidate")).not.toBeInTheDocument();
  });

  it("renders finding detail and a failed tool in the trace", async () => {
    window.history.pushState({}, "", "/findings/finding-1");
    const fetchMock = vi.mocked(fetch);
    fetchMock.mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/health")) return Promise.resolve(new Response(JSON.stringify({ status: "ok", environment: "demo", demo_mode: true }), { status: 200 }));
      if (url.endsWith("/reviews")) return Promise.resolve(new Response(JSON.stringify([{ review_id: reviewId, status: "completed", commit_sha: "head", partial_failure: true, latency_ms: 10, created_at: "2026-01-01", updated_at: "2026-01-01", verification_counts: { Verified: 1, Rejected: 0, "Needs manual review": 0, Unverified: 0 } }]), { status: 200 }));
      if (url.endsWith("/findings")) return Promise.resolve(new Response(JSON.stringify({ findings: [findingData], counts: { Verified: 1, Rejected: 0, "Needs manual review": 0, Unverified: 0 } }), { status: 200 }));
      if (url.endsWith("/trace")) return Promise.resolve(new Response(JSON.stringify({ review_id: reviewId, status: "completed_with_errors", trace: [{ node: "parallel_analysis", status: "completed" }], failures: [{ task: "bandit", reason: "timeout", status: "timed_out" }], tool_statuses: [{ tool: "bandit", status: "timed_out", reason: "deadline" }], verification_counts: { Verified: 1, Rejected: 0, "Needs manual review": 0, Unverified: 0 } }), { status: 200 }));
      return Promise.resolve(new Response(JSON.stringify({ error: { message: "Not found" } }), { status: 404 }));
    });
    renderApp();
    expect(await screen.findByRole("heading", { name: "Unsafe query" })).toBeInTheDocument();
    expect(screen.getByText("Confidence is not a calibrated probability.")).toBeInTheDocument();
    window.history.pushState({}, "", `/trace?review=${reviewId}`);
    fireEvent.click(screen.getByRole("link", { name: "Agent trace" }));
    expect(await screen.findByText("bandit")).toBeInTheDocument();
    expect(screen.getByText("timed_out")).toBeInTheDocument();
  });
});
