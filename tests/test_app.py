from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "secureshop"}


def test_home_page_loads():
    response = client.get("/")
    assert response.status_code == 200
    assert "SecureShop" in response.text


def test_create_product_redirects():
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
