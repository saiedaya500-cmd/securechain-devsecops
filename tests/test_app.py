import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app


# Base SQLite temporaire réservée aux tests
test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(
    bind=test_engine,
    autoflush=False,
    autocommit=False,
)


def override_get_db():
    db = TestingSessionLocal()

    try:
        yield db
    finally:
        db.close()


# FastAPI utilise la base temporaire pendant les tests
app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_test_database():
    # Nettoyer les cookies entre les tests
    client.cookies.clear()

    # Recréer une base vide pour chaque test
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)

    yield

    client.cookies.clear()


def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "secureshop",
    }


def test_home_page_loads():
    response = client.get("/")

    assert response.status_code == 200
    assert "SecureShop" in response.text


def test_create_product_redirects():
    # Ouvrir la page pour recevoir le cookie CSRF
    page_response = client.get("/")

    assert page_response.status_code == 200

    # Récupérer le token enregistré dans le cookie
    csrf_token = client.cookies.get("csrf_token")

    assert csrf_token is not None

    # Envoyer le même token avec le formulaire
    response = client.post(
        "/products",
        data={
            "csrf_token": csrf_token,
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


def test_create_product_rejects_missing_csrf_token():
    # Tentative de création sans token CSRF
    response = client.post(
        "/products",
        data={
            "name": "Produit malveillant",
            "description": "Requête sans token CSRF",
            "price": "10.00",
            "quantity": "1",
            "category": "Test",
        },
        follow_redirects=False,
    )

    # FastAPI doit bloquer la requête
    assert response.status_code == 403