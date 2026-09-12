from pathlib import Path

from fastapi import Depends, FastAPI, Form, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import Base, engine, get_db
from .models import Product
from .security import (
    get_or_create_csrf_token,
    set_csrf_cookie,
    validate_csrf_token,
)


APP_DIR = Path(__file__).resolve().parent

app = FastAPI(
    title="SecureShop",
    description="Application de démonstration pour le projet SecureChain DevSecOps.",
    version="0.1.0",
)

app.mount(
    "/static",
    StaticFiles(directory=APP_DIR / "static"),
    name="static",
)

templates = Jinja2Templates(directory=APP_DIR / "templates")


def render_template_with_csrf(
    request: Request,
    name: str,
    context: dict,
):
    csrf_token = get_or_create_csrf_token(request)

    response = templates.TemplateResponse(
        request=request,
        name=name,
        context={
            **context,
            "csrf_token": csrf_token,
        },
    )

    set_csrf_cookie(response, request, csrf_token)
    return response


@app.on_event("startup")
def create_database() -> None:
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "secureshop",
    }


@app.get("/", response_class=HTMLResponse)
def product_list(
    request: Request,
    q: str = Query(default="", max_length=100),
    db: Session = Depends(get_db),
):
    statement = select(Product).order_by(Product.id.desc())

    if q:
        statement = statement.where(
            Product.name.ilike(f"%{q}%")
        )

    products = db.scalars(statement).all()

    return render_template_with_csrf(
        request=request,
        name="products.html",
        context={
            "products": products,
            "query": q,
        },
    )


@app.get("/products/new", response_class=HTMLResponse)
def new_product_form(request: Request):
    return render_template_with_csrf(
        request=request,
        name="product_form.html",
        context={
            "product": None,
            "action": "/products",
        },
    )


@app.post("/products")
def create_product(
    request: Request,
    name: str = Form(min_length=2, max_length=100),
    description: str = Form(default="", max_length=500),
    price: float = Form(gt=0),
    quantity: int = Form(ge=0),
    category: str = Form(min_length=2, max_length=80),
    csrf_token: str = Form(default=""),
    db: Session = Depends(get_db),
):
    validate_csrf_token(request, csrf_token)

    product = Product(
        name=name.strip(),
        description=description.strip(),
        price=price,
        quantity=quantity,
        category=category.strip(),
    )

    db.add(product)
    db.commit()

    return RedirectResponse(
        url="/",
        status_code=status.HTTP_303_SEE_OTHER,
    )


def get_product_or_404(
    product_id: int,
    db: Session,
) -> Product:
    product = db.get(Product, product_id)

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Produit introuvable",
        )

    return product


@app.get(
    "/products/{product_id}/edit",
    response_class=HTMLResponse,
)
def edit_product_form(
    product_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    product = get_product_or_404(product_id, db)

    return render_template_with_csrf(
        request=request,
        name="product_form.html",
        context={
            "product": product,
            "action": f"/products/{product_id}",
        },
    )


@app.post("/products/{product_id}")
def update_product(
    product_id: int,
    request: Request,
    name: str = Form(min_length=2, max_length=100),
    description: str = Form(default="", max_length=500),
    price: float = Form(gt=0),
    quantity: int = Form(ge=0),
    category: str = Form(min_length=2, max_length=80),
    csrf_token: str = Form(default=""),
    db: Session = Depends(get_db),
):
    validate_csrf_token(request, csrf_token)

    product = get_product_or_404(product_id, db)

    product.name = name.strip()
    product.description = description.strip()
    product.price = price
    product.quantity = quantity
    product.category = category.strip()

    db.commit()

    return RedirectResponse(
        url="/",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@app.post("/products/{product_id}/delete")
def delete_product(
    product_id: int,
    request: Request,
    csrf_token: str = Form(default=""),
    db: Session = Depends(get_db),
):
    validate_csrf_token(request, csrf_token)

    product = get_product_or_404(product_id, db)

    db.delete(product)
    db.commit()

    return RedirectResponse(
        url="/",
        status_code=status.HTTP_303_SEE_OTHER,
    )