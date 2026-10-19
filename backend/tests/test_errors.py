from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_missing_route_returns_safe_json_error() -> None:
    response = client.get("/api/v1/does-not-exist")

    assert response.status_code == 404
    assert response.json() == {
        "error": {"code": "HTTP_ERROR", "message": "Resource not found"}
    }


def test_cors_allows_both_local_frontend_origins() -> None:
    for origin in ("http://127.0.0.1:5173", "http://localhost:5173"):
        response = client.get("/api/v1/health", headers={"Origin": origin})
        assert response.headers["access-control-allow-origin"] == origin
