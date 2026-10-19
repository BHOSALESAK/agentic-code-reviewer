import re
from dataclasses import dataclass


@dataclass(frozen=True)
class DiffLine:
    kind: str
    content: str
    old_line: int | None
    new_line: int | None


@dataclass(frozen=True)
class DiffHunk:
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    lines: list[DiffLine]


HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


def parse_patch(patch: str | None) -> list[DiffHunk]:
    if not patch:
        return []
    hunks: list[DiffHunk] = []
    current: DiffHunk | None = None
    old_line = new_line = 0
    for raw_line in patch.splitlines():
        match = HUNK_RE.match(raw_line)
        if match:
            if current:
                hunks.append(current)
            old_line = int(match.group(1))
            new_line = int(match.group(3))
            current = DiffHunk(
                old_start=old_line,
                old_count=int(match.group(2) or 1),
                new_start=new_line,
                new_count=int(match.group(4) or 1),
                lines=[],
            )
            continue
        if current is None or not raw_line or raw_line[0] not in " +-":
            continue
        kind = {"+": "added", "-": "removed", " ": "context"}[raw_line[0]]
        current.lines.append(DiffLine(kind, raw_line[1:], old_line if kind != "added" else None, new_line if kind != "removed" else None))
        if kind != "added":
            old_line += 1
        if kind != "removed":
            new_line += 1
    if current:
        hunks.append(current)
    return hunks
