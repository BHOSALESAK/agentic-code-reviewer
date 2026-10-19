from pathlib import Path

import httpx
import pytest

from app.context.builder import ContextLimits, build_context
from app.context.diff import parse_patch
from app.github.client import GitHubClient, GitHubError
from app.github.reference import InvalidPRReference, parse_pr_reference


def test_parse_diff_tracks_added_removed_and_context_lines() -> None:
    hunks = parse_patch("@@ -1,3 +1,4 @@\n context\n-old\n+new\n tail")
    assert len(hunks) == 1
    assert [(line.kind, line.old_line, line.new_line) for line in hunks[0].lines] == [
        ("context", 1, 1), ("removed", 2, None), ("added", None, 2), ("context", 3, 3)
    ]


def test_reference_parser_accepts_url_and_shorthand() -> None:
    assert parse_pr_reference("octo/repo#12").number == 12
    assert parse_pr_reference("https://github.com/octo/repo/pull/12").full_name == "octo/repo"
    with pytest.raises(InvalidPRReference):
        parse_pr_reference("not a pull request")


def test_context_limits_and_path_traversal() -> None:
    root = Path(__file__).parents[2] / "fixtures" / "sample_repositories" / "small_repo"
    summary = build_context(root, [{"filename": "app.py"}], ContextLimits(max_bytes=200, max_tokens=100, chunk_bytes=20))
    assert summary.incomplete
    assert len(summary.chunks) > 1
    assert sum(len(chunk.content.encode("utf-8")) for chunk in summary.chunks) <= 200
    with pytest.raises(ValueError):
        build_context(root, [{"filename": "../outside.py"}])


@pytest.mark.parametrize(
    ("status", "message"),
    [(404, "not found"), (403, "denied access"), (429, "rate limit")],
)
def test_github_error_mapping(status: int, message: str) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json={"message": "failure"}, request=request)

    client = GitHubClient(None, max_retries=0, client=httpx.Client(transport=httpx.MockTransport(handler)))
    with pytest.raises(GitHubError, match=message):
        client.get_pull_request(parse_pr_reference("octo/repo#1"))


def test_github_error_mapping_for_network_failure() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("offline", request=request)

    client = GitHubClient(None, max_retries=0, client=httpx.Client(transport=httpx.MockTransport(handler)))
    with pytest.raises(GitHubError, match="network"):
        client.get_pull_request(parse_pr_reference("octo/repo#1"))
