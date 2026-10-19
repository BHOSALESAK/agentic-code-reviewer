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
    await screen.findByText("Connected");
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
});
