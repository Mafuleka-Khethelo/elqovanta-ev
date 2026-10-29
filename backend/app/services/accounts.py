"""Registration, login sessions, profile, vehicles and favourites.

Public registration always creates a driver. Manager access is only granted by
the operator command, never by a field on these requests.
"""

import re
from datetime import timedelta
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.clock import utcnow
from app.core.config import get_settings
from app.core.errors import fail
from app.core.security import dummy_verify, hash_password, hash_token, needs_rehash, new_token, verify_password
from app.db.models import AuthSession, Charger, Favourite, LoginAttempt, User, Vehicle, VehiclePreference

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def normalise_email(value: str) -> str:
    email = value.strip().lower()
    if len(email) > 255 or not _EMAIL.fullmatch(email):
        fail(422, "invalid_email", "Enter a valid email address.")
    return email


def check_password(password: str) -> None:
    if len(password) < 10 or len(password) > 128:
        fail(422, "invalid_password", "Use a password between 10 and 128 characters.")


def check_display_name(name: str) -> str:
    cleaned = " ".join(name.split())
    if len(cleaned) < 2 or len(cleaned) > 80:
        fail(422, "invalid_name", "Enter a name between 2 and 80 characters.")
    return cleaned


def open_login_session(db: Session, user: User, now=None) -> tuple[AuthSession, str]:
    moment = now or utcnow()
    settings = get_settings()
    raw = new_token()
    auth = AuthSession(
        user_id=user.id,
        token_hash=hash_token(raw),
        expires_at=moment + timedelta(hours=settings.session_ttl_hours),
        created_at=moment,
    )
    db.add(auth)
    db.flush()
    return auth, raw


def authenticate(db: Session, raw_token: str | None, now=None) -> tuple[User, AuthSession]:
    moment = now or utcnow()
    if not raw_token:
        fail(401, "login_required", "Sign in to continue.")
    auth = db.scalar(select(AuthSession).where(AuthSession.token_hash == hash_token(raw_token)))
    if auth is None:
        fail(401, "login_required", "Sign in to continue.")
    if auth.revoked_at is not None:
        fail(401, "session_revoked", "This sign-in is no longer valid. Please sign in again.")
    if auth.expires_at <= moment:
        fail(401, "session_expired", "Your sign-in has expired. Please sign in again.")
    user = db.get(User, auth.user_id)
    if user is None:
        fail(401, "login_required", "Sign in to continue.")
    return user, auth


def register_driver(db: Session, email: str, password: str, display_name: str) -> tuple[User, str]:
    check_password(password)
    cleaned_name = check_display_name(display_name)
    normalised = normalise_email(email)
    if db.scalar(select(User.id).where(User.email == normalised)):
        fail(409, "email_taken", "An account with that email address already exists.")
    now = utcnow()
    user = User(
        email=normalised,
        password_hash=hash_password(password),
        display_name=cleaned_name,
        role="driver",
        is_demonstration=False,
        created_at=now,
        updated_at=now,
    )
    db.add(user)
    db.flush()
    _auth, raw = open_login_session(db, user, now)
    return user, raw


def login(db: Session, email: str, password: str) -> tuple[User, str]:
    settings = get_settings()
    now = utcnow()
    normalised = normalise_email(email)
    window_start = now - timedelta(seconds=settings.login_window_seconds)
    failures = db.scalar(
        select(func.count())
        .select_from(LoginAttempt)
        .where(
            LoginAttempt.email == normalised,
            LoginAttempt.succeeded.is_(False),
            LoginAttempt.created_at >= window_start,
        )
    )
    if int(failures or 0) >= settings.login_max_failures:
        fail(429, "too_many_attempts", "Too many sign-in attempts. Wait 15 minutes and try again.")
    user = db.scalar(select(User).where(User.email == normalised))
    if user is None:
        dummy_verify(password)
        ok = False
    else:
        ok = verify_password(password, user.password_hash)
    db.add(LoginAttempt(email=normalised, succeeded=ok, created_at=now))
    db.flush()
    if not ok or user is None:
        # The request will raise and the outer session rolls back. Commit the
        # failure first, or the throttle never sees the earlier attempts.
        db.commit()
        fail(401, "invalid_login", "The email address or password is not correct.")
    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)
    _auth, raw = open_login_session(db, user, now)
    return user, raw


def revoke_session(auth: AuthSession, now=None) -> None:
    auth.revoked_at = now or utcnow()


def change_password(
    db: Session,
    user: User,
    current_session: AuthSession,
    current_password: str,
    new_password: str,
) -> None:
    check_password(new_password)
    if not verify_password(current_password, user.password_hash):
        fail(400, "wrong_password", "The current password is not correct.")
    if current_password == new_password:
        fail(422, "password_unchanged", "Choose a password that is different from the current one.")
    now = utcnow()
    user.password_hash = hash_password(new_password)
    user.updated_at = now
    db.execute(
        update(AuthSession)
        .where(
            AuthSession.user_id == user.id,
            AuthSession.id != current_session.id,
            AuthSession.revoked_at.is_(None),
        )
        .values(revoked_at=now)
    )


def update_profile(user: User, display_name: str) -> User:
    user.display_name = check_display_name(display_name)
    user.updated_at = utcnow()
    return user


def list_vehicles(db: Session, user_id: UUID) -> list[Vehicle]:
    return list(db.scalars(select(Vehicle).where(Vehicle.user_id == user_id).order_by(Vehicle.created_at)))


def vehicle_selection(db: Session, user: User) -> dict:
    row = db.get(VehiclePreference, user.id)
    return {"selected_vehicle_id": (row.selected_vehicle_id or row.default_vehicle_id) if row else None,
            "default_vehicle_id": row.default_vehicle_id if row else None}


def select_vehicle(db: Session, user: User, vehicle_id: UUID, make_default: bool = False) -> dict:
    # Serialise first selection and deletion for one account, including two tabs.
    db.scalar(select(User).where(User.id == user.id).with_for_update())
    _own_vehicle(db, user.id, vehicle_id)
    row = db.get(VehiclePreference, user.id)
    if row is None:
        row = VehiclePreference(user_id=user.id)
        db.add(row)
    row.selected_vehicle_id = vehicle_id
    if make_default:
        row.default_vehicle_id = vehicle_id
    db.flush()
    return vehicle_selection(db, user)


def add_vehicle(db: Session, user: User, nickname: str, model_name: str | None, port_preference: str | None, *, battery_capacity_kwh: float | None = None, max_ac_kw: float | None = None, max_dc_kw: float | None = None) -> Vehicle:
    db.scalar(select(User).where(User.id == user.id).with_for_update())
    count = db.scalar(select(func.count()).select_from(Vehicle).where(Vehicle.user_id == user.id))
    if int(count or 0) >= 5:
        fail(409, "too_many_vehicles", "You can save up to five vehicles.")
    now = utcnow()
    vehicle = Vehicle(
        user_id=user.id,
        nickname=_short(nickname, 40, "Enter a vehicle nickname."),
        model_name=_optional(model_name, 60),
        port_preference=_optional(port_preference, 60),
        battery_capacity_kwh=battery_capacity_kwh, max_ac_kw=max_ac_kw, max_dc_kw=max_dc_kw,
        created_at=now,
        updated_at=now,
    )
    db.add(vehicle)
    db.flush()
    return vehicle


def update_vehicle(db: Session, user: User, vehicle_id: UUID, nickname: str, model_name: str | None, port_preference: str | None, *, battery_capacity_kwh: float | None = None, max_ac_kw: float | None = None, max_dc_kw: float | None = None) -> Vehicle:
    vehicle = _own_vehicle(db, user.id, vehicle_id)
    vehicle.nickname = _short(nickname, 40, "Enter a vehicle nickname.")
    vehicle.model_name = _optional(model_name, 60)
    vehicle.port_preference = _optional(port_preference, 60)
    vehicle.battery_capacity_kwh = battery_capacity_kwh
    vehicle.max_ac_kw, vehicle.max_dc_kw = max_ac_kw, max_dc_kw
    vehicle.updated_at = utcnow()
    return vehicle


def delete_vehicle(db: Session, user: User, vehicle_id: UUID) -> None:
    db.scalar(select(User).where(User.id == user.id).with_for_update())
    vehicle = _own_vehicle(db, user.id, vehicle_id)
    db.delete(vehicle)


def add_favourite(db: Session, user: User, charger_id: UUID) -> Favourite:
    if db.get(Charger, charger_id) is None:
        fail(404, "not_found", "Charger not found.")
    existing = db.get(Favourite, (user.id, charger_id))
    if existing is not None:
        return existing
    favourite = Favourite(user_id=user.id, charger_id=charger_id, created_at=utcnow())
    db.add(favourite)
    db.flush()
    return favourite


def remove_favourite(db: Session, user: User, charger_id: UUID) -> None:
    favourite = db.get(Favourite, (user.id, charger_id))
    if favourite is None:
        fail(404, "not_found", "That charger is not in your favourites.")
    db.delete(favourite)


def _own_vehicle(db: Session, user_id: UUID, vehicle_id: UUID) -> Vehicle:
    vehicle = db.get(Vehicle, vehicle_id)
    if vehicle is None or vehicle.user_id != user_id:
        fail(404, "not_found", "Vehicle not found.")
    return vehicle


def _short(value: str, limit: int, message: str) -> str:
    cleaned = " ".join(value.split())
    if not cleaned or len(cleaned) > limit:
        fail(422, "invalid_field", message)
    return cleaned


def _optional(value: str | None, limit: int) -> str | None:
    if value is None:
        return None
    cleaned = " ".join(value.split())
    if not cleaned:
        return None
    if len(cleaned) > limit:
        fail(422, "invalid_field", f"Use {limit} characters or fewer.")
    return cleaned
