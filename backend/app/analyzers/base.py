import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class ToolStatus(StrEnum):
    SUCCESS = "success"
    UNAVAILABLE = "unavailable"
    FAILED = "failed"
    TIMED_OUT = "timed_out"


class RawToolFinding(BaseModel):
    rule_id: str
    severity: str
    file_path: str | None = None
    start_line: int | None = Field(default=None, ge=1)
    end_line: int | None = Field(default=None, ge=1)
    evidence: str | None = None
    message: str
    tool_name: str


class ToolRunResult(BaseModel):
    tool_name: str
    status: ToolStatus
    findings: list[RawToolFinding] = Field(default_factory=list)
    reason: str | None = None
    raw_output: dict[str, Any] | None = None


@dataclass(frozen=True)
class CommandResult:
    status: ToolStatus
    stdout: str = ""
    stderr: str = ""
    reason: str | None = None


def run_in_copy(root: Path, command: list[str], *, timeout_seconds: float) -> CommandResult:
    executable = shutil.which(command[0])
    if executable is None:
        venv_executable = Path(sys.prefix) / "bin" / command[0]
        if venv_executable.is_file():
            executable = str(venv_executable)
    if executable is None:
        return CommandResult(ToolStatus.UNAVAILABLE, reason=f"tool executable not found: {command[0]}")
    resolved_command = [executable, *command[1:]]
    with tempfile.TemporaryDirectory(prefix="agentic-scan-") as temp_dir:
        scan_root = Path(temp_dir) / "repository"
        shutil.copytree(root, scan_root)
        try:
            completed = subprocess.run(
                resolved_command,
                cwd=scan_root,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                shell=False,
                check=False,
            )
        except FileNotFoundError:
            return CommandResult(ToolStatus.UNAVAILABLE, reason=f"tool executable not found: {command[0]}")
        except subprocess.TimeoutExpired:
            return CommandResult(ToolStatus.TIMED_OUT, reason=f"tool exceeded {timeout_seconds:g}s timeout")
        if completed.returncode != 0:
            return CommandResult(ToolStatus.FAILED, completed.stdout, completed.stderr, f"tool exited with code {completed.returncode}")
        return CommandResult(ToolStatus.SUCCESS, completed.stdout, completed.stderr)
