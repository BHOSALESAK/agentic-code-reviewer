import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from app.context.diff import parse_patch


@dataclass(frozen=True)
class ContextLimits:
    max_files: int = 10
    max_bytes: int = 16000
    max_tokens: int = 4000
    chunk_bytes: int = 6000
    surrounding_lines: int = 3


@dataclass(frozen=True)
class ContextChunk:
    file_path: str
    content: str
    start_line: int
    end_line: int


@dataclass(frozen=True)
class ContextSummary:
    chunks: list[ContextChunk]
    incomplete: bool
    incomplete_reasons: list[str]
    files_considered: int
    files_included: int


SECRET_RE = re.compile(r"(?i)(api[_-]?key|secret|token|password)\s*[:=]")
SKIP_NAMES = {"package-lock.json", "pnpm-lock.yaml", "yarn.lock", "poetry.lock"}
GENERATED_PARTS = {"dist", "build", "__pycache__", ".git"}


def _safe_relative(path: str) -> PurePosixPath:
    candidate = PurePosixPath(path)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError("repository path must stay within the fixture repository")
    return candidate


def build_context(root: Path, files: list[dict[str, Any]], limits: ContextLimits | None = None) -> ContextSummary:
    limits = limits or ContextLimits()
    chunks: list[ContextChunk] = []
    reasons: list[str] = []
    total_bytes = total_tokens = 0
    included_files = 0
    for file in files:
        path = _safe_relative(str(file.get("filename", "")))
        path_text = path.as_posix()
        if included_files >= limits.max_files:
            reasons.append("file-count limit reached")
            break
        if path.name in SKIP_NAMES or path.suffix in {".lock", ".map"} or any(part in GENERATED_PARTS for part in path.parts):
            reasons.append(f"skipped non-source file: {path_text}")
            continue
        full_path = (root / Path(*path.parts)).resolve()
        if root.resolve() not in full_path.parents:
            raise ValueError("repository path escapes the fixture repository")
        if not full_path.is_file():
            reasons.append(f"file unavailable: {path_text}")
            continue
        raw = full_path.read_bytes()
        if b"\x00" in raw:
            reasons.append(f"skipped binary file: {path_text}")
            continue
        text = raw.decode("utf-8", errors="replace")
        if SECRET_RE.search(text):
            reasons.append(f"skipped possible secret: {path_text}")
            continue
        selected_lines: list[str] = []
        selected_bytes = 0
        selected_tokens = 0
        for line in text.splitlines(keepends=True):
            line_bytes = len(line.encode("utf-8"))
            line_tokens = len(line.split())
            if selected_bytes + line_bytes > limits.max_bytes - total_bytes:
                break
            if selected_tokens + line_tokens > limits.max_tokens - total_tokens:
                break
            selected_lines.append(line)
            selected_bytes += line_bytes
            selected_tokens += line_tokens
        clipped = "".join(selected_lines)
        if not clipped:
            reasons.append("byte limit reached")
            break
        clipped_lines = clipped.splitlines(keepends=True)
        offset = 0
        start_line = 1
        while offset < len(clipped_lines):
            chunk_lines = clipped_lines[offset : offset + max(1, limits.chunk_bytes // 80)]
            content = "".join(chunk_lines)
            end_line = start_line + len(chunk_lines) - 1
            chunks.append(ContextChunk(path_text, content, start_line, end_line))
            offset += len(chunk_lines)
            start_line = end_line + 1
        included_files += 1
        total_bytes += selected_bytes
        total_tokens += selected_tokens
        if len(clipped) < len(text):
            reasons.append(f"truncated file: {path_text}")
        if total_bytes >= limits.max_bytes or total_tokens >= limits.max_tokens:
            reasons.append("context size limit reached")
            break
    return ContextSummary(chunks, bool(reasons), reasons, len(files), included_files)


def parse_file_hunks(files: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{**file, "hunks": parse_patch(file.get("patch"))} for file in files]
