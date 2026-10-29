"""Collected /api/v1 routes."""

from fastapi import APIRouter

from app.api.v1 import activity, auth, chargers, research, coordination, charging_estimates

api = APIRouter()
api.include_router(auth.router)
api.include_router(chargers.router)
api.include_router(activity.router)
api.include_router(research.router)
api.include_router(coordination.router)
api.include_router(charging_estimates.router)
