"""Authentication dependencies and cookies.

Frontend route guards are only a convenience. These dependencies are the check
that matters.
"""

from fastapi import Depends, Request, Response
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import fail
from app.core.security import CSRF_COOKIE, SESSION_COOKIE, cookie_kwargs, new_token
from app.db.models import AuthSession, User
from app.db.session import get_db
from app.services.accounts import authenticate


def current_principal(
    request: Request,
    db: Session = Depends(get_db),
) -> tuple[User, AuthSession]:
    user, auth = authenticate(db, request.cookies.get(SESSION_COOKIE))
    return user, auth


def current_user(principal: tuple[User, AuthSession] = Depends(current_principal)) -> User:
    return principal[0]


def current_auth(principal: tuple[User, AuthSession] = Depends(current_principal)) -> tuple[User, AuthSession]:
    return principal


def require_driver(user: User = Depends(current_user)) -> User:
    if user.role != "driver":
        fail(403, "drivers_only", "This action is for driver accounts.")
    return user


def require_manager(user: User = Depends(current_user)) -> User:
    if user.role != "manager":
        fail(403, "managers_only", "This action is for station manager accounts.")
    return user


def require_researcher(user: User = Depends(current_user)) -> User:
    if user.role != "researcher":
        fail(403, "researchers_only", "This page is for the protected examiner workspace.")
    return user


def require_admin(user: User = Depends(current_user)) -> User:
    if user.role != "manager" or not user.is_admin:
        fail(403, "administrators_only", "This page is for the project administrator.")
    return user


def set_session_cookie(response: Response, raw_token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        SESSION_COOKIE,
        raw_token,
        **cookie_kwargs(settings, settings.session_ttl_hours * 3600),
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE, path="/")


def ensure_csrf_cookie(request: Request, response: Response) -> str:
    token = request.cookies.get(CSRF_COOKIE)
    if not token or len(token) < 20:
        token = new_token()
        settings = get_settings()
        response.set_cookie(CSRF_COOKIE, token, **cookie_kwargs(settings, settings.session_ttl_hours * 3600))
    return token
