import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app


# Base SQLite temporaire réservée aux tests.
test_engine = create_engine(
    "sqlite://",
    connect_args={
        "check_same_thread": False,
    },
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(
    bind=test_engine,
    autoflush=False,
    autocommit=False,
)


def override_get_db():
    """Fournir une session de base de données temporaire."""

    db = TestingSessionLocal()

    try:
        yield db
    finally:
        db.close()


# FastAPI utilise la base temporaire pendant les tests.
app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_test_database():
    """Recréer une base vide avant chaque test."""

    client.cookies.clear()

    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)

    yield

    client.cookies.clear()


def get_csrf_token() -> str:
    """Ouvrir la page d'accueil et récupérer le token CSRF."""

    response = client.get("/")

    assert response.status_code == 200

    csrf_token = client.cookies.get("csrf_token")

    assert csrf_token is not None

    return csrf_token


def create_test_product() -> dict[str, str]:
    """Retourner les données d'un produit de démonstration."""

    return {
        "csrf_token": get_csrf_token(),
        "name": "Security Key",
        "description": "Clé matérielle de démonstration",
        "price": "49.90",
        "quantity": "4",
        "category": "Sécurité",
    }


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
    assert "Gestion des produits" in response.text


def test_create_product_redirects():
    response = client.post(
        "/products",
        data=create_test_product(),
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/?notice=created"

    notification_response = client.get(
        response.headers["location"]
    )

    assert notification_response.status_code == 200
    assert "Produit ajouté" in notification_response.text
    assert "Security Key" in notification_response.text
    assert "Stock faible" in notification_response.text


def test_create_product_rejects_missing_csrf_token():
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

    assert response.status_code == 403


def test_product_with_zero_quantity_is_out_of_stock():
    product_data = create_test_product()
    product_data["quantity"] = "0"

    create_response = client.post(
        "/products",
        data=product_data,
        follow_redirects=False,
    )

    assert create_response.status_code == 303

    page_response = client.get("/")

    assert page_response.status_code == 200
    assert "Security Key" in page_response.text
    assert "Rupture" in page_response.text


def test_product_with_available_stock():
    product_data = create_test_product()
    product_data["quantity"] = "10"

    create_response = client.post(
        "/products",
        data=product_data,
        follow_redirects=False,
    )

    assert create_response.status_code == 303

    page_response = client.get("/")

    assert page_response.status_code == 200
    assert "Security Key" in page_response.text
    assert "Disponible" in page_response.text


def test_product_search():
    create_response = client.post(
        "/products",
        data=create_test_product(),
        follow_redirects=False,
    )

    assert create_response.status_code == 303

    found_response = client.get(
        "/",
        params={"q": "Security"},
    )

    assert found_response.status_code == 200
    assert "Security Key" in found_response.text

    missing_response = client.get(
        "/",
        params={"q": "Produit inexistant"},
    )

    assert missing_response.status_code == 200
    assert "Aucun résultat" in missing_response.text