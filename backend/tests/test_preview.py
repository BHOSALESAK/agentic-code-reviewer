from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_fixture_list_contains_small_and_large() -> None:
    response = client.get("/api/v1/fixtures")
    assert response.status_code == 200
    assert {item["fixture_id"] for item in response.json()} == {"small", "large"}


def test_preview_works_for_both_fixture_prs() -> None:
    for fixture_id in ("small", "large"):
        response = client.post("/api/v1/pull-requests/preview", json={"fixture_id": fixture_id})
        assert response.status_code == 200
        payload = response.json()
        assert payload["changed_files"]
        assert "chunk_plan" in payload["context"]
        assert "incomplete" in payload["context"]
