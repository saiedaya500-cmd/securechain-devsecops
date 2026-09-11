import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_health_endpoint(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "secureshop"
    }


def test_home_page_loads(client):
    response = client.get("/")

    assert response.status_code == 200
    assert "SecureShop" in response.text


def test_create_product_redirects(client):
    response = client.post(
        "/products",
        data={
            "name": "Security Key",
            "description": "Clé matérielle de démonstration",
            "price": "49.90",
            "quantity": "4",
            "category": "Sécurité",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/"