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
