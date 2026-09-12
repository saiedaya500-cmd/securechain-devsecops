from secrets import compare_digest, token_urlsafe

from fastapi import HTTPException, Request, status
from starlette.responses import Response


CSRF_COOKIE_NAME = "csrf_token"


def get_or_create_csrf_token(request: Request) -> str:
    token = request.cookies.get(CSRF_COOKIE_NAME)

    if token:
        return token

    return token_urlsafe(32)


def set_csrf_cookie(
    response: Response,
    request: Request,
    token: str,
) -> None:
    if request.cookies.get(CSRF_COOKIE_NAME) == token:
        return

    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=token,
        max_age=3600,
        httponly=True,
        samesite="strict",
        secure=request.url.scheme == "https",
        path="/",
    )


def validate_csrf_token(
    request: Request,
    submitted_token: str,
) -> None:
    cookie_token = request.cookies.get(CSRF_COOKIE_NAME)

    if (
        not cookie_token
        or not submitted_token
        or not compare_digest(cookie_token, submitted_token)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Jeton CSRF invalide ou absent",
        )