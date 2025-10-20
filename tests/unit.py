import pytest
from fastapi.testclient import TestClient
from routes import ingest, review, status, system

@pytest.fixture
def client():
    from main import app
    return TestClient(app)

class TestIngestRoutes:
    def test_ingest_endpoint_success(self, client):
        response = client.post("/ingest", json={"data": "test"})
        assert response.status_code == 200
        assert "message" in response.json()

    def test_ingest_invalid_data(self, client):
        response = client.post("/ingest", json={})
        assert response.status_code == 422

class TestReviewRoutes:
    def test_get_review_success(self, client):
        response = client.get("/review")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_post_review_success(self, client):
        response = client.post("/review", json={"review": "test"})
        assert response.status_code == 200

class TestStatusRoutes:
    def test_get_status_success(self, client):
        response = client.get("/status")
        assert response.status_code == 200
        assert "status" in response.json()

    def test_status_details(self, client):
        response = client.get("/status/details")
        assert response.status_code == 200
        assert isinstance(response.json(), dict)

class TestSystemRoutes:
    def test_system_health(self, client):
        response = client.get("/system/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_system_metrics(self, client):
        response = client.get("/system/metrics")
        assert response.status_code == 200
        assert isinstance(response.json(), dict)

def test_error_handling(client):
    response = client.get("/nonexistent")
    assert response.status_code == 404

if __name__ == "__main__":
    pytest.main(["-v"])