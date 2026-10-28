"""Accounts, cookies and permission checks."""

from uuid import UUID
import pytest

from fastapi import HTTPException
from sqlalchemy import select

from app.core.clock import utcnow
from app.db.models import Notification, User
from app.db.session import SessionLocal
from app.services.accounts import authenticate, open_login_session
from tests.conftest import csrf, register


def test_register_login_logout_and_me(http):
    created = register(http, "ada@example.com", "Ada Driver")
    assert created["role"] == "driver"
    me = http.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["user"]["email"] == "ada@example.com"

    logout = http.post("/api/v1/auth/logout", headers=csrf(http))
    assert logout.status_code == 204
    assert http.get("/api/v1/auth/me").status_code == 401

    login = http.post(
        "/api/v1/auth/login",
        headers=csrf(http),
        json={"email": "ada@example.com", "password": "correct-horse-battery"},
    )
    assert login.status_code == 200
    assert http.get("/api/v1/auth/me").status_code == 200


@pytest.mark.parametrize("privileged_role", ["manager", "researcher"])
def test_registration_cannot_grant_privileged_role(http, privileged_role):
    response = http.post(
        "/api/v1/auth/register",
        headers=csrf(http),
        json={
            "email": "sam@example.com",
            "password": "correct-horse-battery",
            "display_name": "Sam",
            "role": privileged_role,
        },
    )
    assert response.status_code == 422


def test_password_change_revokes_other_sessions(http, db):
    register(http, "bea@example.com", "Bea Driver")
    user = db.scalar(select(User).where(User.email == "bea@example.com"))
    _other, raw = open_login_session(db, user)
    db.commit()

    changed = http.post(
        "/api/v1/auth/password",
        headers=csrf(http),
        json={"current_password": "correct-horse-battery", "new_password": "a-different-phrase"},
    )
    assert changed.status_code == 204
    assert http.get("/api/v1/auth/me").status_code == 200

    with SessionLocal() as check:
        try:
            authenticate(check, raw)
        except HTTPException as exc:
            assert exc.status_code == 401
        else:
            raise AssertionError("the other session should have been revoked")


def test_notification_is_private(http, db):
    owner = register(http, "owner@example.com")
    note = Notification(
        user_id=UUID(owner["id"]),
        event_key="private-note",
        title="Hello",
        body="Only the owner can read this.",
        destination="/app/notifications",
        created_at=utcnow(),
    )
    db.add(note)
    db.commit()
    http.post("/api/v1/auth/logout", headers=csrf(http))
    register(http, "other@example.com", "Other Driver")
    listing = http.get("/api/v1/notifications")
    assert listing.status_code == 200
    assert listing.json()["items"] == []
    missing = http.post(f"/api/v1/notifications/{note.id}/read", headers=csrf(http))
    assert missing.status_code == 404


def test_login_is_throttled(http):
    register(http, "limit@example.com")
    http.post("/api/v1/auth/logout", headers=csrf(http))
    statuses = []
    for _ in range(6):
        response = http.post(
            "/api/v1/auth/login",
            headers=csrf(http),
            json={"email": "limit@example.com", "password": "wrong-password-value"},
        )
        statuses.append(response.status_code)
    assert statuses[:5] == [401, 401, 401, 401, 401]
    assert statuses[5] == 429
