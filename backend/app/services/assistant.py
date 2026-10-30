"""Consent-based return reminders and read-only personal charger comparisons.

The model does not schedule notifications. Only the owner's explicit PUT can
enable a reminder. Charger/session locks match the existing coordination worker.
"""
from datetime import timedelta
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.clock import utcnow
from app.core.errors import fail
from app.db.models import AssistantReminder, Charger, ChargingSession
from app.db.session import SessionLocal
from app.services.coordination import own_session
from app.services.notifications import notify, short_label
from app.services.participation import lock_charger


def _session(db, user, session_id):
    session = db.get(ChargingSession, session_id)
    if session is None or session.user_id != user.id:
        fail(404, "not_found", "Session not found.")
    return session


def get_reminder(db, user, session_id):
    session = _session(db, user, session_id)
    row = db.get(AssistantReminder, session_id)
    charger = db.get(Charger, session.charger_id)
    from app.services.queues import waiting_count
    return {"enabled": bool(row and row.enabled), "lead_minutes": row.lead_minutes if row else 10,
        "has_choice": row is not None, "waiting_count": waiting_count(db, session.charger_id),
        "due_at": row.due_at if row else None, "delivered_at": row.delivered_at if row else None,
        "version": row.version if row else 0, "estimate_version": row.estimate_version if row else None,
        "server_time": utcnow(), "timezone": charger.timezone_name}


def set_reminder(db, user, session_id, body, now):
    session = own_session(db, user, session_id, open_only=False)
    row = db.scalar(select(AssistantReminder).where(AssistantReminder.session_id == session_id).with_for_update())
    if row and row.enabled == body.enabled and row.lead_minutes == body.lead_minutes:
        return get_reminder(db, user, session_id)
    version = row.version if row else 0
    if body.expected_version != version:
        fail(409, "reminder_changed", "Your reminder changed in another tab or after a battery update. Refresh before saving.")
    from app.services.charging_estimates import active_estimate
    estimate = active_estimate(db, session_id)
    if body.enabled and (session.state != "charging" or session.unplugged_at or not estimate):
        fail(409, "estimate_required", "Save a current charging estimate before enabling a return reminder.")
    if body.enabled and estimate.estimated_target_at <= now:
        fail(409, "target_time_reached", "Check your car or update its battery reading before setting a future return reminder.")
    if row is None:
        row = AssistantReminder(session_id=session_id, user_id=user.id, version=0)
        db.add(row)
    row.enabled, row.lead_minutes = body.enabled, body.lead_minutes
    row.due_at = max(now, estimate.estimated_target_at-timedelta(minutes=body.lead_minutes)) if body.enabled else None
    row.estimate_version = estimate.version if body.enabled else None
    row.delivered_at, row.updated_at = None, now
    row.version += 1
    db.flush()
    return get_reminder(db, user, session_id)


def sync_reminder(db, session, estimate, now):
    row = db.scalar(select(AssistantReminder).where(AssistantReminder.session_id == session.id).with_for_update())
    if row is None or not row.enabled:
        return
    row.due_at = max(now, estimate.estimated_target_at-timedelta(minutes=row.lead_minutes))
    row.estimate_version, row.delivered_at = estimate.version, None
    row.version += 1
    row.updated_at = now
    db.flush()


def cancel_assistant_reminder(db, session_id, now):
    row = db.scalar(select(AssistantReminder).where(AssistantReminder.session_id == session_id).with_for_update())
    if row and row.enabled:
        row.enabled, row.due_at, row.updated_at = False, None, now
        row.version += 1


def deliver_due_once(now=None):
    now = now or utcnow()
    with SessionLocal() as db:
        candidates = list(db.execute(select(AssistantReminder.session_id, ChargingSession.charger_id)
            .join(ChargingSession).where(AssistantReminder.enabled.is_(True), AssistantReminder.delivered_at.is_(None),
                AssistantReminder.due_at <= now).order_by(AssistantReminder.due_at).limit(100)))
    count = 0
    for session_id, charger_id in candidates:
        with SessionLocal() as db:
            charger = lock_charger(db, charger_id)
            session = db.scalar(select(ChargingSession).where(ChargingSession.id == session_id).with_for_update())
            row = db.scalar(select(AssistantReminder).where(AssistantReminder.session_id == session_id).with_for_update(skip_locked=True))
            if not row or not row.enabled or row.delivered_at or not row.due_at or row.due_at > now:
                continue
            from app.services.charging_estimates import active_estimate
            estimate = active_estimate(db, session_id)
            if not session or session.state != "charging" or session.unplugged_at or not estimate:
                row.enabled, row.due_at = False, None
                row.version += 1
            elif row.estimate_version != estimate.version:
                sync_reminder(db, session, estimate, now)
            else:
                notify(db, user_id=row.user_id, event_key=f"assistant-return:{session_id}:{row.version}",
                    title="Time to return to your car",
                    body=f"You asked to return before your estimated {estimate.target_percent:g}% target at {short_label(charger.display_name)}. Please check your car. Report charging finished, then unplug when ready. This reminder does not confirm battery level or release a bay.",
                    destination="/app/session")
                row.delivered_at = now
                count += 1
            row.updated_at = now
            db.commit()
    return count


def compare(db, user, body, now):
    from app.services.charging_estimates import preview
    # Validate ownership/input even if every candidate has unknown power.
    preview(db, user, body.plan.model_copy(update={"charger_id": None, "port_type": None}), now)
    chargers = {c.id: c for c in db.scalars(select(Charger).where(Charger.id.in_(body.charger_ids)).options(selectinload(Charger.port_types)))}
    result = []
    for charger_id in dict.fromkeys(body.charger_ids):
        charger = chargers.get(charger_id)
        if not charger:
            result.append({"charger_id": charger_id, "available": False, "reason": "Charger not found."})
            continue
        choices = [p for p in charger.port_types if p.power_kw and p.charging_kind == body.plan.charging_kind]
        if body.plan.port_type:
            exact = [p for p in choices if p.name == body.plan.port_type]
            choices = exact or choices
        if not choices:
            result.append({"charger_id": charger_id, "available": False, "reason": f"No manager-reported {body.plan.charging_kind} port power. Enter an assumption on the charger page to plan separately."})
            continue
        estimates = [preview(db, user, body.plan.model_copy(update={"charger_id": charger.id, "port_type": p.name}), now) for p in choices]
        best = min(estimates, key=lambda e: e["duration_seconds"])
        result.append({"charger_id": charger_id, "available": True, "estimate": best,
            "notice": "Charging duration if starting now, using your average-power assumption and the listed port limit. Queue time is excluded; observed port labels do not guarantee vehicle compatibility."})
    return {"items": result, "server_time": now}
