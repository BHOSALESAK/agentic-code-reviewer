export type Health = { status: string; service: string; environment: string; demo_mode: boolean };
export type Fixture = { fixture_id: string; title: string; number: number; repository: string; changed_files: number; synthetic: boolean };
export type DiffLine = { kind: "added" | "removed" | "context"; content: string; old_line: number | null; new_line: number | null };
export type DiffHunk = { old_start: number; old_count: number; new_start: number; new_count: number; lines: DiffLine[] };
export type ChangedFile = { filename: string; status: string; additions: number; deletions: number; patch?: string; hunks: DiffHunk[] };
export type Preview = {
  metadata: { title: string; number: number; user?: { login?: string }; base: { sha: string }; head: { sha: string }; html_url?: string };
  changed_files: ChangedFile[];
  context: { chunks: { file_path: string; start_line: number; end_line: number; content: string }[]; incomplete: boolean; incomplete_reasons: string[]; files_considered: number; files_included: number; chunk_plan: { file_path: string; start_line: number; end_line: number }[] };
};
export type ReviewStatus = "queued" | "running" | "completed" | "completed_with_errors" | "failed";
export type VerificationStatus = "Verified" | "Rejected" | "Needs manual review" | "Unverified";
export type ReviewAccepted = { review_id: string; status: ReviewStatus; existing: boolean };
export type ReviewSummary = { review_id: string; status: ReviewStatus; commit_sha: string; partial_failure: boolean; latency_ms: number | null; created_at: string; updated_at: string; verification_counts: Record<VerificationStatus, number> };
export type ReviewDetail = ReviewSummary & { repository_id: string; pull_request_id: string };
export type FindingRecord = { finding_id: string; title: string; category: string; severity: string; confidence: number; file_path: string | null; start_line: number | null; end_line: number | null; verification_status: VerificationStatus; verification_reason: string | null; verification_explanation: string | null; evidence: string | null; provenance: { supporting_agents?: string[]; supporting_tools?: string[]; supporting_rule_ids?: string[]; verification?: { reason_code?: string; explanation?: string; provenance?: string[] } } };
export type FindingsResponse = { findings: FindingRecord[]; counts: Record<VerificationStatus, number> };
export type TraceResponse = { review_id: string; status: ReviewStatus; trace: { node: string; status: string; [key: string]: unknown }[]; failures: { task?: string; kind?: string; status?: string; reason?: string }[]; tool_statuses: { tool: string; status: "success" | "unavailable" | "failed" | "timed_out"; reason?: string | null }[]; verification_counts: Record<VerificationStatus, number> };
