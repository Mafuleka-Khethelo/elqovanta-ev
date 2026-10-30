"""Request bodies. Extra fields are rejected so a public form cannot set a role."""

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RegisterIn(StrictModel):
    email: str
    password: str
    display_name: str


class LoginIn(StrictModel):
    email: str
    password: str


class PasswordIn(StrictModel):
    current_password: str
    new_password: str


class ProfileIn(StrictModel):
    display_name: str


class VehicleIn(StrictModel):
    nickname: str
    model_name: str | None = None
    port_preference: str | None = None
    battery_capacity_kwh: float | None = Field(default=None, gt=0, le=500, allow_inf_nan=False)
    max_ac_kw: float | None = Field(default=None, gt=0, le=1000, allow_inf_nan=False)
    max_dc_kw: float | None = Field(default=None, gt=0, le=1000, allow_inf_nan=False)


class ChargeEstimateIn(StrictModel):
    charger_id: UUID | None = None
    port_type: str | None = Field(default=None, min_length=1, max_length=120)
    vehicle_id: UUID | None = None
    vehicle_label: str = Field(default="My vehicle", min_length=1, max_length=140)
    battery_capacity_kwh: float = Field(gt=0, le=500, allow_inf_nan=False)
    current_percent: float = Field(ge=0, le=100, allow_inf_nan=False)
    target_percent: float = Field(gt=0, le=100, allow_inf_nan=False)
    charging_kind: Literal["AC", "DC"] = "AC"
    average_power_kw: float = Field(gt=0, le=1000, allow_inf_nan=False)


class EstimatePreviewIn(ChargeEstimateIn):
    available_minutes: int | None = Field(default=None, ge=1, le=1440)


class ChargeComparisonIn(StrictModel):
    plan: ChargeEstimateIn
    charger_ids: list[UUID] = Field(min_length=1, max_length=6)


class AssistantReminderIn(StrictModel):
    enabled: bool
    lead_minutes: int = Field(default=10, ge=1, le=120)
    expected_version: int = Field(ge=0)


class PortPowerIn(StrictModel):
    name: str = Field(min_length=1, max_length=120)
    charging_kind: Literal["AC", "DC"] | None = None
    power_kw: float | None = Field(default=None, gt=0, le=1000, allow_inf_nan=False)


class VehicleSelectionIn(StrictModel):
    vehicle_id: UUID
    make_default: bool = False


class IdKeyIn(StrictModel):
    idempotency_key: str = Field(min_length=8, max_length=80)


class ChargerActionIn(IdKeyIn):
    charger_id: UUID
    port_type: str | None = Field(default=None, min_length=1, max_length=120)


class SessionStartIn(ChargerActionIn):
    charge_estimate: ChargeEstimateIn | None = None


class OfferAcceptIn(IdKeyIn):
    charge_estimate: ChargeEstimateIn | None = None


class EstimateUpdateIn(ChargeEstimateIn, IdKeyIn):
    expected_version: int = Field(ge=0)


class MessageIn(StrictModel):
    body: str
    client_request_id: str = Field(min_length=8, max_length=80)


class ConversationIn(StrictModel):
    charger_id: UUID


class PredictIn(StrictModel):
    station_key: str = Field(min_length=1, max_length=500)
    port_type: str = Field(min_length=1, max_length=120)
    arrival_date: date
    arrival_time: str = Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")


class ChargerCreateIn(StrictModel):
    display_name: str
    timezone: str = Field(default="UTC", min_length=1, max_length=64)
    latitude: float | None = None
    longitude: float | None = None
    port_types: list[str] = Field(default_factory=list, max_length=10)
    service_capacity: int | None = Field(default=None, ge=1, le=20)
    app_status: Literal["unknown", "available", "occupied", "offline", "paused"] = "unknown"


class ChargerUpdateIn(StrictModel):
    display_name: str | None = None
    timezone: str | None = Field(default=None, min_length=1, max_length=64)
    app_status: Literal["unknown", "available", "occupied", "offline", "paused"] | None = None
    service_capacity: int | None = Field(default=None, ge=1, le=20)
    port_types_to_add: list[str] = Field(default_factory=list, max_length=10)
    port_power_updates: list[PortPowerIn] = Field(default_factory=list, max_length=20)


class CloseSessionIn(IdKeyIn):
    reason: str = Field(min_length=5, max_length=500)


class RemindIn(StrictModel):
    user_id: UUID


class UserOut(BaseModel):
    id: UUID
    email: str
    display_name: str
    role: str
    is_demonstration: bool


class VehicleOut(BaseModel):
    id: UUID
    nickname: str
    model_name: str | None
    port_preference: str | None
    battery_capacity_kwh: float | None
    max_ac_kw: float | None
    max_dc_kw: float | None


class MessageCreated(BaseModel):
    created_at: datetime


class DepartureIn(StrictModel):
    expected_at: datetime | None = None


class ReminderIn(IdKeyIn):
    due_at: datetime


class SwitchQueueIn(ChargerActionIn):
    expected_charger_id: UUID
    confirm_leave: Literal[True]


class ReportIn(IdKeyIn):
    category: Literal["not_working", "access_blocked"]
    details: str = Field(min_length=3, max_length=1000)


class ReportUpdateIn(StrictModel):
    state: Literal["acknowledged", "resolved"]
    response: str = Field(min_length=3, max_length=1000)


class DemonstrationIn(PredictIn):
    driver_id: UUID


class HistoricalAssistantIn(PredictIn):
    plan: ChargeEstimateIn
    lead_minutes: int = Field(default=10, ge=1, le=120)


class AssistantOut(BaseModel):
    available: bool
    reason: str | None = None
    mode: str | None = None
    warning: bool | None = None
    port_type: str | None = None
    port_types: list[str] | None = None
    arrival_local: str | None = None
    arrival_station: str | None = None
    station_timezone: str | None = None
    checked_at: datetime | None = None
    historical_arrival_local: str | None = None
    timezone: str | None = None
    title: str | None = None
    suggestion: str | None = None
    explanation: str | None = None
    action_label: str | None = None
    action_href: str | None = None


class DemonstrationContextOut(BaseModel):
    active: bool
    charger_id: UUID | None = None
    charger_name: str | None = None
    historical_arrival_local: str | None = None
    timezone: str | None = None
