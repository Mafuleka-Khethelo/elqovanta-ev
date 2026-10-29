"""Accounts, vehicles and favourites."""

from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import clear_session_cookie, current_auth, current_user, ensure_csrf_cookie, require_driver, set_session_cookie
from app.db.models import Favourite, User
from app.db.session import get_db
from app.schemas import LoginIn, PasswordIn, ProfileIn, RegisterIn, UserOut, VehicleIn, VehicleOut, VehicleSelectionIn
from app.services import accounts

router = APIRouter()


def _user(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        role=user.role,
        is_demonstration=user.is_demonstration,
    )


@router.get("/auth/csrf")
def issue_csrf(request: Request, response: Response) -> dict:
    return {"csrf_token": ensure_csrf_cookie(request, response)}


@router.post("/auth/register", status_code=201)
def register(body: RegisterIn, response: Response, db: Session = Depends(get_db)) -> dict:
    user, token = accounts.register_driver(db, body.email, body.password, body.display_name)
    set_session_cookie(response, token)
    return {"user": _user(user)}


@router.post("/auth/login")
def login(body: LoginIn, response: Response, db: Session = Depends(get_db)) -> dict:
    user, token = accounts.login(db, body.email, body.password)
    set_session_cookie(response, token)
    return {"user": _user(user)}


@router.post("/auth/logout", status_code=204)
def logout(response: Response, principal=Depends(current_auth)) -> None:
    _user_row, auth = principal
    accounts.revoke_session(auth)
    clear_session_cookie(response)


@router.get("/auth/me")
def me(user: User = Depends(current_user)) -> dict:
    return {"user": _user(user)}


@router.post("/auth/password", status_code=204)
def change_password(body: PasswordIn, principal=Depends(current_auth), db: Session = Depends(get_db)) -> None:
    user, auth = principal
    accounts.change_password(db, user, auth, body.current_password, body.new_password)


@router.patch("/me")
def update_me(body: ProfileIn, user: User = Depends(current_user)) -> dict:
    accounts.update_profile(user, body.display_name)
    return {"user": _user(user)}


@router.get("/me/vehicles", response_model=list[VehicleOut])
def get_vehicles(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return accounts.list_vehicles(db, user.id)


@router.get("/me/vehicle-selection")
def get_vehicle_selection(user: User = Depends(require_driver), db: Session = Depends(get_db)):
    return accounts.vehicle_selection(db, user)


@router.put("/me/vehicle-selection")
def put_vehicle_selection(body: VehicleSelectionIn, user: User = Depends(require_driver), db: Session = Depends(get_db)):
    return accounts.select_vehicle(db, user, body.vehicle_id, body.make_default)


@router.post("/me/vehicles", status_code=201, response_model=VehicleOut)
def post_vehicle(body: VehicleIn, user: User = Depends(require_driver), db: Session = Depends(get_db)):
    return accounts.add_vehicle(db, user, body.nickname, body.model_name, body.port_preference, battery_capacity_kwh=body.battery_capacity_kwh, max_ac_kw=body.max_ac_kw, max_dc_kw=body.max_dc_kw)


@router.patch("/me/vehicles/{vehicle_id}", response_model=VehicleOut)
def patch_vehicle(vehicle_id: UUID, body: VehicleIn, user: User = Depends(require_driver), db: Session = Depends(get_db)):
    return accounts.update_vehicle(db, user, vehicle_id, body.nickname, body.model_name, body.port_preference, battery_capacity_kwh=body.battery_capacity_kwh, max_ac_kw=body.max_ac_kw, max_dc_kw=body.max_dc_kw)


@router.delete("/me/vehicles/{vehicle_id}", status_code=204)
def remove_vehicle(vehicle_id: UUID, user: User = Depends(require_driver), db: Session = Depends(get_db)) -> None:
    accounts.delete_vehicle(db, user, vehicle_id)


@router.get("/favourites")
def get_favourites(user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    from app.api.v1.chargers import charger_cards

    ids = list(db.scalars(select(Favourite.charger_id).where(Favourite.user_id == user.id)))
    items, _total = charger_cards(db, user, charger_ids=ids)
    return {"items": items}
