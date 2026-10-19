from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_missing_route_returns_safe_json_error() -> None:
    response = client.get("/api/v1/does-not-exist")

    assert response.status_code == 404
    assert response.json() == {
        "error": {"code": "HTTP_ERROR", "message": "Resource not found"}
    }
