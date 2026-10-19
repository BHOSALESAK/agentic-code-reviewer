import re
from dataclasses import dataclass


class InvalidPRReference(ValueError):
    """Raised when a pull-request reference is not supported."""


@dataclass(frozen=True)
class PRReference:
    owner: str
    repo: str
    number: int

    @property
    def full_name(self) -> str:
        return f"{self.owner}/{self.repo}"


def parse_pr_reference(value: str) -> PRReference:
    candidate = value.strip()
    patterns = (
        r"^(?P<owner>[A-Za-z0-9_.-]+)/(?P<repo>[A-Za-z0-9_.-]+)#(?P<number>[1-9][0-9]*)$",
        r"^https?://github\.com/(?P<owner>[A-Za-z0-9_.-]+)/(?P<repo>[A-Za-z0-9_.-]+)/pull/(?P<number>[1-9][0-9]*)/?$",
    )
    for pattern in patterns:
        match = re.match(pattern, candidate)
        if match:
            return PRReference(match["owner"], match["repo"], int(match["number"]))
    raise InvalidPRReference("Use owner/repository#number or a GitHub pull-request URL")
