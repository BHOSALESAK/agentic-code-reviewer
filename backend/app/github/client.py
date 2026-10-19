from dataclasses import dataclass
from pathlib import Path
from time import sleep
from typing import Any, Protocol

import httpx

from app.github.reference import PRReference


class GitHubError(RuntimeError):
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


@dataclass(frozen=True)
class PullRequestData:
    metadata: dict[str, Any]
    files: list[dict[str, Any]]
    repository_root: Path | None = None
    fixture_id: str | None = None


class PullRequestProvider(Protocol):
    def get_pull_request(self, reference: PRReference) -> PullRequestData: ...


class GitHubClient:
    def __init__(
        self,
        token: str | None,
        timeout_seconds: float = 10.0,
        max_retries: int = 2,
        backoff_seconds: float = 0.1,
        client: httpx.Client | None = None,
    ):
        self._client = client or httpx.Client(timeout=timeout_seconds)
        self._max_retries = max_retries
        self._backoff_seconds = backoff_seconds
        self._headers = {"Accept": "application/vnd.github+json"}
        if token:
            self._headers["Authorization"] = f"Bearer {token}"

    def get_pull_request(self, reference: PRReference) -> PullRequestData:
        base = f"https://api.github.com/repos/{reference.full_name}/pulls/{reference.number}"
        metadata = self._get_json(base)
        files = self._get_all_files(f"{base}/files")
        return PullRequestData(metadata=metadata, files=files)

    def _get_all_files(self, url: str) -> list[dict[str, Any]]:
        return self._get_json(url)

    def _get_json(self, url: str) -> Any:
        for attempt in range(self._max_retries + 1):
            try:
                response = self._client.get(url, headers=self._headers)
            except httpx.RequestError as exc:
                if attempt == self._max_retries:
                    raise GitHubError("GitHub network request failed; check connectivity and try again") from exc
                sleep(self._backoff_seconds * (2**attempt))
                continue
            if response.status_code == 404:
                raise GitHubError("GitHub pull request was not found; check the repository and number", 404)
            if response.status_code == 403:
                raise GitHubError("GitHub denied access; check token permissions or rate limits", 403)
            if response.status_code == 429:
                if attempt == self._max_retries:
                    raise GitHubError("GitHub rate limit reached; wait and try again", 429)
                sleep(self._backoff_seconds * (2**attempt))
                continue
            if response.status_code >= 500:
                if attempt == self._max_retries:
                    raise GitHubError("GitHub is temporarily unavailable; try again later", response.status_code)
                sleep(self._backoff_seconds * (2**attempt))
                continue
            if response.is_error:
                raise GitHubError("GitHub rejected the request; check the reference and permissions", response.status_code)
            return response.json()
        raise GitHubError("GitHub request failed; try again")


class FixturePullRequestProvider:
    def __init__(self, fixtures_root: Path | None = None):
        self.fixtures_root = fixtures_root or Path(__file__).resolve().parents[3] / "fixtures"

    def get_pull_request(self, reference: PRReference) -> PullRequestData:
        fixture_id = self._fixture_id(reference)
        fixture_path = self.fixtures_root / "pull_requests" / f"{fixture_id}.json"
        if not fixture_path.is_file():
            raise GitHubError("Demo fixture was not found; choose a listed fixture", 404)
        payload = __import__("json").loads(fixture_path.read_text(encoding="utf-8"))
        return PullRequestData(
            metadata=payload,
            files=payload["files"],
            repository_root=self.fixtures_root / "sample_repositories" / payload["repository_fixture"],
            fixture_id=fixture_id,
        )

    def _fixture_id(self, reference: PRReference) -> str:
        if reference.owner == "synthetic" and reference.repo == "demo":
            return {1: "small", 2: "large"}.get(reference.number, "")
        return ""
