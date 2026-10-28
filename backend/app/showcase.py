"""Local fictional people and repeatable, database-backed feature walkthroughs.

Operator-only: never called during app startup or public registration. Passwords
are generated once and kept in the ignored local guide, not in source control.
The fitted model, catalogue and unrelated accounts are never reset here.
"""
import json
import secrets
from datetime import datetime, timedelta
from pathlib import Path
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import delete, func, or_, select, text
from sqlalchemy.orm import Session

from app.core.clock import utcnow
from app.core.config import get_settings, project_root
from app.core.security import hash_password
from app.db.models import (
    AuthSession, Charger, ChargerPortType, ChargerReport, ChargingSession,
    Conversation, Favourite, HistoricalDemonstration, LoginAttempt,
    ManagerAssignment, Message, Notification, PredictionLog, QueueEntry,
    ReadMarker, Reminder, User, Vehicle,
)
from app.db.session import SessionLocal
from app.services.coordination import create_report, respond_report, schedule_reminder, set_departure
from app.services.messages import mark_read, open_conversation, send_message
from app.services.queues import join_queue, reconcile_charger
from app.services.sessions import direct_start, driver_action, manager_close, refresh_reported_status, report_still_charging

VERSION = 1
SCOPE = "elqovanta-ev-personas-v1"

# Each tuple is name, role, starting situation and a concrete action to try.
PEOPLE = {
    "thabo.mokoena": ("Thabo Mokoena", "driver", "Charging at Rosebank; leaving in about 35 minutes", "Open My session. Edit or clear the departure time, pause/resume, then finish and unplug. Nomsa should receive the next offer."),
    "aisha.khan": ("Aisha Khan", "driver", "Charging at Rosebank; saved chargers and a manager reply", "Open Saved chargers and Messages. Reply to Sarah, then check the saved departure estimate in My session."),
    "daniel.jacobs": ("Daniel Jacobs", "driver", "Charging again after an earlier pause", "Open My session. Compare charging time with connected time and inspect the pause/resume events."),
    "lerato.dlamini": ("Lerato Dlamini", "driver", "Charging; already sent a still-charging update", "Check session events and Sarah's notifications. The still-charging cooldown prevents repeat reminders for ten minutes."),
    "michael.naidoo": ("Michael Naidoo", "driver", "Charging; no departure estimate yet", "Share an expected unplug time, finish charging, choose a return reminder, then report unplugged."),
    "nomsa.nkosi": ("Nomsa Nkosi", "driver", "Rosebank queue position 1", "Open Waiting list. See anonymous departures. After Thabo unplugs, accept the offer within ten minutes and verify your new session."),
    "james.petersen": ("James Petersen", "driver", "Rosebank queue position 2; waiting reminder sent", "Open Messages and Waiting list. Check Sarah received the reminder. Another reminder is allowed after the ten-minute cooldown."),
    "zanele.khumalo": ("Zanele Khumalo", "driver", "Rosebank queue position 3", "Compare alternatives. Review the confirmation before switching queues. Refresh to see that only the new participation remains."),
    "sipho.dube": ("Sipho Dube", "driver", "Rosebank queue position 4", "Leave the waiting list, refresh, and join it again. Rejoining places you at the back."),
    "olivia.smith": ("Olivia Smith", "driver", "Rosebank queue position 5; three saved chargers", "Open Saved chargers, remove one, return to the charger and save it again. Your queue place stays unchanged."),
    "fatima.patel": ("Fatima Patel", "driver", "Rosebank queue position 6; private access report acknowledged", "Open Rosebank Quick help to read Sarah's private reply. Other drivers cannot see this report."),
    "kabelo.molefe": ("Kabelo Molefe", "driver", "Rosebank queue position 7; car and favourites saved", "Open My profile to edit your vehicle and port preference. Then check the waiting-list position."),
    "emma.brown": ("Emma Brown", "driver", "Rosebank queue position 8; unread manager reply", "Read and reply to Sarah in Messages; watch the unread count change and persist after refresh."),
    "noah.williams": ("Noah Williams", "driver", "Paused, still connected at Sandton Square", "Resume charging. Finish and set a reminder, or unplug. Pausing alone does not release the app slot."),
    "priya.singh": ("Priya Singh", "driver", "Finished, still plugged in at Sandton; reminder due in 15 minutes", "Open My session. Replace, snooze or cancel the reminder. Unplugging or resuming cancels any pending reminder."),
    "ethan.taylor": ("Ethan Taylor", "driver", "Finished, still plugged in at Parkhurst; overdue reminder", "Open Notifications, then My session. The backend delivers the overdue reminder even with your browser closed. Snooze or unplug."),
    "amahle.ndlovu": ("Amahle Ndlovu", "driver", "Access blocked at Braamfontein; help report open", "Open the saved Braamfontein charger and read your private access report. Message David; he can acknowledge or resolve it."),
    "yusuf.ahmed": ("Yusuf Ahmed", "driver", "Faulty Rivonia charger; private report acknowledged; public status offline", "Read David's reply. New starts are blocked while offline. Compare working alternatives; resolving a report alone does not change charger status."),
    "chloe.adams": ("Chloe Adams", "driver", "Melrose issue resolved; reply saved", "Open Melrose Quick help and Messages to see the resolved report and Sarah's reply. Reports remain private."),
    "lucas.meyer": ("Lucas Meyer", "driver", "23 completed sessions and a long manager conversation", "Use Next/Previous in Charging history. In Messages choose Load older messages. One history entry was closed by Sarah with a reason."),
    "grace.williams": ("Grace Williams", "driver", "No active stop; ready for the explicit historical model walkthrough", "Helen can select Grace in Driver demo and choose a supported 2020 example. Open the selected historical charger to see the labelled suggestion; no probability is exposed."),
    "sibusiso.mthembu": ("Sibusiso Mthembu", "driver", "Fresh account: no vehicle, favourites, history or participation", "Try the empty states, edit your profile, add/edit/remove a vehicle, find a charger, save it, message its manager and start at a free station."),
    "mia.johnson": ("Mia Johnson", "driver", "Fresh ten-minute coordination offer at Melrose Arch", "Open Waiting list immediately after reset. Accept or decline the offer. If it expires, rejoin; the server decides expiry, not the browser timer."),
    "benjamin.nkosi": ("Benjamin Nkosi", "driver", "Missed offer; expiry notification; no active queue", "Read the expired-offer notification. Join again to receive a new place. The missed offer does not create a charging session."),
    "naledi.maseko": ("Naledi Maseko", "driver", "Four saved chargers across available, occupied, paused and offline states", "Compare saved charger statuses, open the map, filter the catalogue, then remove and re-add a favourite."),
    "sarah.vandermerwe": ("Sarah van der Merwe", "manager", "Manages Rosebank, Sandton, Melrose and Parkhurst", "Inspect five charging drivers and eight waiting at Rosebank. Reply to messages, respond to private reports, send reminders, edit capacity/status/timezone and inspect session events."),
    "david.maseko": ("David Maseko", "manager", "Manages Braamfontein and Rivonia only", "Acknowledge Amahle's blocked-access report, resolve Yusuf's fault and update public status separately. Rosebank management is unavailable to David."),
    "helen.roberts": ("Dr Helen Roberts", "researcher", "Separate examiner workspace; no driver messages or management access", "Open Historical prediction lab, Historical insights and About model. Configure Grace's explicit 2020 Driver demo, compare another time, and clear the context afterward."),
}

# These are fictional locations for app coordination. Map markers are deliberately
# omitted: invented charging facilities must not be shown as real infrastructure.
STATIONS = {
    "rosebank": ("Rosebank Central Charging Hub", 5, "sarah.vandermerwe"),
    "sandton": ("Sandton Square Charging Lounge", 2, "sarah.vandermerwe"),
    "melrose": ("Melrose Arch Charging Point", 1, "sarah.vandermerwe"),
    "parkhurst": ("Parkhurst Corner Charging Point", 2, "sarah.vandermerwe"),
    "braamfontein": ("Braamfontein City Charging Point", 1, "david.maseko"),
    "rivonia": ("Rivonia Business Park Charging Point", 1, "david.maseko"),
}


def identity(kind: str, key: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"{SCOPE}/{kind}/{key}")


def email(key: str) -> str:
    return f"{key}@elqovanta.test"


def _preflight(db: Session, reset: bool) -> bool:
    """Refuse collisions and cross-scope resets before changing any record."""
    user_ids = {identity("user", key) for key in PEOPLE}
    charger_ids = {identity("charger", key) for key in STATIONS}
    present = 0
    for key, (_, role, _, _) in PEOPLE.items():
        row = db.scalar(select(User).where(or_(User.id == identity("user", key), User.email == email(key))).with_for_update())
        if row:
            if row.id != identity("user", key) or row.email != email(key) or not row.is_demonstration or row.role != role:
                raise ValueError(f"Refusing to change the existing unrelated account {email(key)}.")
            present += 1
    for key in STATIONS:
        row = db.scalar(select(Charger).where(or_(Charger.id == identity("charger", key), Charger.station_key == f"ELQOVANTA / {key.upper()}" )).with_for_update())
        if row and (row.id != identity("charger", key) or row.station_key != f"ELQOVANTA / {key.upper()}" or row.is_historical):
            raise ValueError("A walkthrough station conflicts with an existing charger. Nothing was changed.")
    if present and present != len(PEOPLE):
        raise ValueError("The walkthrough accounts are incomplete. No records were reset; inspect the account conflict first.")
    if reset:
        for model, owner in ((ChargingSession, ChargingSession.user_id), (QueueEntry, QueueEntry.user_id), (Conversation, Conversation.driver_id), (ChargerReport, ChargerReport.reporter_id)):
            outsider = db.scalar(select(model.id).where(model.charger_id.in_(charger_ids), owner.not_in(user_ids)).limit(1))
            outside = db.scalar(select(model.id).where(owner.in_(user_ids), model.charger_id.not_in(charger_ids)).limit(1))
            if outsider or outside:
                raise ValueError("Reset stopped: a walkthrough person or station now interacts with unrelated records. Those records have been preserved.")
        if db.scalar(select(ManagerAssignment.id).where(ManagerAssignment.charger_id.in_(charger_ids), ManagerAssignment.manager_id.not_in(user_ids)).limit(1)):
            raise ValueError("Reset stopped: an unrelated manager is assigned to a walkthrough station.")
    return bool(present)


def _clear_owned_records(db: Session) -> None:
    ids = [identity("user", key) for key in PEOPLE]
    threads = select(Conversation.id).where(Conversation.driver_id.in_(ids))
    db.execute(delete(ReadMarker).where(ReadMarker.conversation_id.in_(threads)))
    db.execute(delete(Message).where(Message.conversation_id.in_(threads)))
    db.execute(delete(Conversation).where(Conversation.driver_id.in_(ids)))
    db.execute(delete(QueueEntry).where(QueueEntry.user_id.in_(ids)))
    db.execute(delete(ChargingSession).where(ChargingSession.user_id.in_(ids)))
    db.execute(delete(ChargerReport).where(ChargerReport.reporter_id.in_(ids)))
    db.execute(delete(HistoricalDemonstration).where(HistoricalDemonstration.driver_id.in_(ids)))
    db.execute(delete(PredictionLog).where(PredictionLog.user_id.in_(ids)))
    db.execute(delete(Notification).where(Notification.user_id.in_(ids)))
    db.execute(delete(Favourite).where(Favourite.user_id.in_(ids)))
    db.execute(delete(Vehicle).where(Vehicle.user_id.in_(ids)))
    db.execute(delete(AuthSession).where(AuthSession.user_id.in_(ids)))
    db.execute(delete(LoginAttempt).where(LoginAttempt.email.in_([email(key) for key in PEOPLE])))
    db.flush()
    db.expire_all()


def populate(db: Session, credentials: dict[str, str], now: datetime, *, reset: bool = False) -> bool:
    """One atomic fixture transaction. Returns False if already present and kept."""
    db.execute(text("SELECT pg_advisory_xact_lock(726420281)"))
    exists = _preflight(db, reset)
    if exists and not reset:
        return False
    if exists:
        _clear_owned_records(db)
    users = {}
    for key, (name, role, _, _) in PEOPLE.items():
        user = db.get(User, identity("user", key))
        if user is None:
            user = User(id=identity("user", key), email=email(key), role=role, is_demonstration=True)
            db.add(user)
        user.display_name, user.password_hash = name, hash_password(credentials[email(key)])
        users[key] = user
    db.flush()
    chargers = {}
    for key, (name, capacity, manager_key) in STATIONS.items():
        charger = db.get(Charger, identity("charger", key))
        if charger is None:
            charger = Charger(id=identity("charger", key), station_key=f"ELQOVANTA / {key.upper()}", display_name=name, display_name_custom=True, is_historical=False)
            db.add(charger)
        charger.display_name = name
        charger.service_capacity, charger.coordination_enabled = capacity, True
        charger.app_status, charger.status_updated_at = "available", now
        charger.status_source, charger.timezone_name = f"Manager: {users[manager_key].display_name}", "Africa/Johannesburg"
        charger.status_version = (charger.status_version or 0) + 1
        db.flush()
        if not db.scalar(select(ChargerPortType.id).where(ChargerPortType.charger_id == charger.id, ChargerPortType.name == "Level 2")):
            db.add(ChargerPortType(charger_id=charger.id, name="Level 2", origin="manager"))
        if not db.scalar(select(ManagerAssignment.id).where(ManagerAssignment.manager_id == users[manager_key].id, ManagerAssignment.charger_id == charger.id)):
            db.add(ManagerAssignment(manager_id=users[manager_key].id, charger_id=charger.id))
        chargers[key] = charger
    db.flush()

    # Real session services construct all intervals, transitions and duration data.
    lucas, hub = users["lucas.meyer"], chargers["rosebank"]
    for day in range(23, 0, -1):
        start = now - timedelta(days=day, minutes=80)
        session = direct_start(db, lucas, hub.id, f"showcase-history-{day}", start)
        if day % 3 == 0:
            driver_action(db, lucas, session.id, "pause", f"history-pause-{day}", start + timedelta(minutes=20))
            driver_action(db, lucas, session.id, "resume", f"history-resume-{day}", start + timedelta(minutes=28))
        driver_action(db, lucas, session.id, "finish", f"history-finish-{day}", start + timedelta(minutes=48))
        if day == 2:
            manager_close(db, users["sarah.vandermerwe"], hub.id, session.id, "Driver confirmed the cable was removed; closing the forgotten app session.", "history-manager-close", start + timedelta(minutes=68))
        else:
            driver_action(db, lucas, session.id, "unplug", f"history-unplug-{day}", start + timedelta(minutes=55 + day % 10))
    active = {}
    for index, key in enumerate(list(PEOPLE)[:5]):
        start = now - timedelta(minutes=75 - index * 8)
        active[key] = direct_start(db, users[key], hub.id, f"showcase-start-{key}", start)
    daniel = active["daniel.jacobs"]
    driver_action(db, users["daniel.jacobs"], daniel.id, "pause", "daniel-pause", now - timedelta(minutes=25))
    driver_action(db, users["daniel.jacobs"], daniel.id, "resume", "daniel-resume", now - timedelta(minutes=15))
    report_still_charging(db, users["lerato.dlamini"], active["lerato.dlamini"].id, "lerato-update", now)
    for key, minutes in (("thabo.mokoena", 35), ("aisha.khan", 55)):
        set_departure(db, users[key], active[key].id, now + timedelta(minutes=minutes), now)
    for index, key in enumerate(list(PEOPLE)[5:13]):
        join_queue(db, users[key], hub.id, f"showcase-queue-{key}", now - timedelta(minutes=16 - index))

    noah = direct_start(db, users["noah.williams"], chargers["sandton"].id, "noah-start", now - timedelta(minutes=65))
    driver_action(db, users["noah.williams"], noah.id, "pause", "noah-pause", now - timedelta(minutes=12))
    for key, station, age, finish_age, due in (("priya.singh", "sandton", 90, 10, 15), ("ethan.taylor", "parkhurst", 105, 20, -1)):
        user = users[key]
        current = direct_start(db, user, chargers[station].id, f"{key}-start", now - timedelta(minutes=age))
        driver_action(db, user, current.id, "finish", f"{key}-finish", now - timedelta(minutes=finish_age))
        schedule_reminder(db, user, current.id, now + timedelta(minutes=due), f"{key}-reminder", now - timedelta(minutes=finish_age - 1))
        set_departure(db, user, current.id, now + timedelta(minutes=30), now)

    # Expire an actual previous offer, then create Mia's current ten-minute offer.
    join_queue(db, users["benjamin.nkosi"], chargers["melrose"].id, "benjamin-missed-offer", now - timedelta(hours=1))
    reconcile_charger(db, chargers["melrose"], now)
    join_queue(db, users["mia.johnson"], chargers["melrose"].id, "mia-current-offer", now)

    tickets = [
        ("amahle.ndlovu", "braamfontein", "access_blocked", "The entrance barrier is down and I cannot reach the charging bay.", None, None),
        ("yusuf.ahmed", "rivonia", "not_working", "The charger screen is blank and a charging session will not start.", "acknowledged", "The fault is being checked. I have marked this station offline; please compare alternatives."),
        ("chloe.adams", "melrose", "access_blocked", "A delivery vehicle was blocking the charging entrance.", "resolved", "The delivery vehicle has moved and the entrance is clear. Thank you for reporting it."),
        ("fatima.patel", "rosebank", "access_blocked", "The pedestrian gate beside the charging area appears locked. Is there another entrance?", "acknowledged", "Please use the north pedestrian entrance. The charging area remains accessible from that side."),
    ]
    for key, station, category, details, state, response in tickets:
        ticket = create_report(db, users[key], chargers[station].id, category, details, f"showcase-report-{key}", now)
        if state:
            respond_report(db, users[STATIONS[station][2]], ticket.id, state, response, now)
    from app.services.manager import send_driver_reminder, update_charger
    for station, state in (("braamfontein", "paused"), ("rivonia", "offline")):
        update_charger(db, users[STATIONS[station][2]], chargers[station].id, display_name=None, app_status=state, service_capacity=None, capacity_supplied=False, port_types_to_add=None)
    send_driver_reminder(db, users["james.petersen"], hub.id)

    chats = [
        ("aisha.khan", "rosebank", "I am charging and expect to leave later this afternoon. Is the north exit open?", "Yes, the north exit is open. Thank you for sharing your expected departure."),
        ("james.petersen", "rosebank", "I am waiting in the app queue. Could you check whether the occupied bays are still charging?", "I will check with the connected drivers. Keep your app place while you wait."),
        ("emma.brown", "rosebank", "Does an app offer reserve a physical bay?", "It coordinates app users but does not reserve a physical bay. Please check access when you arrive."),
        ("amahle.ndlovu", "braamfontein", "I have reported the blocked entrance. Can someone help me get access?", None),
        ("yusuf.ahmed", "rivonia", "I have reported the blank charger screen. Should I try another station?", "Yes, please compare another available station while we investigate this fault."),
        ("chloe.adams", "melrose", "Thank you for checking the blocked entrance.", "You are welcome. Your private report is now resolved."),
    ]
    for key, station, question, reply in chats:
        thread = open_conversation(db, users[key], chargers[station].id)
        send_message(db, users[key], thread, question, f"showcase-question-{key}")
        if reply:
            send_message(db, users[STATIONS[station][2]], thread, reply, f"showcase-reply-{key}")
    thread = open_conversation(db, lucas, hub.id)
    thread.created_at = now - timedelta(days=2)
    for index in range(42):
        sender = lucas if index % 2 == 0 else users["sarah.vandermerwe"]
        body = (f"Visit {index // 2 + 1}: I have checked in and will update my session before leaving." if index % 2 == 0 else f"Visit {index // 2 + 1}: Thanks, Lucas. Please report unplugged once you have removed the cable.")
        message = send_message(db, sender, thread, body, f"showcase-archive-{index}")
        message.created_at = now - timedelta(days=1, minutes=60 - index)
        db.flush()
    mark_read(db, thread.id, lucas.id, now - timedelta(days=1, minutes=8))

    # Vehicle and favourite variety, including deliberately empty fresh-account UI.
    for index, (key, (_, role, _, _)) in enumerate(PEOPLE.items()):
        if role != "driver" or key == "sibusiso.mthembu":
            continue
        db.add(Vehicle(user_id=users[key].id, nickname=["Daily drive", "City car", "Weekend car"][index % 3], model_name=["Nissan Leaf", "BMW i3", "Hyundai Kona Electric", "MG4 Electric"][index % 4], port_preference="Level 2"))
        count = 4 if key == "naledi.maseko" else 3 if key == "olivia.smith" else 2 if index % 3 == 0 else 1
        choices = ["rosebank", "parkhurst", "braamfontein", "rivonia"]
        if key == "amahle.ndlovu":
            choices = ["braamfontein", "parkhurst"]
        elif key == "yusuf.ahmed":
            choices = ["rivonia", "parkhurst"]
        for station in choices[:count]:
            db.add(Favourite(user_id=users[key].id, charger_id=chargers[station].id))
    # Reconcile once after this multi-action fixture transaction. Services refresh
    # locked rows between actions; pending report changes must match final counts.
    for charger in chargers.values():
        refresh_reported_status(db, charger, "Driver session report", now)
    # Historical construction must not leave today's public status dated last month.
    hub.status_updated_at, hub.status_source = now, "Driver session report"
    db.flush()
    return True


def write_guide(directory: Path, credentials: dict[str, str], seeded_at: str) -> None:
    root = "http://localhost:5173"
    lines = ["# Elqovanta EV - account and feature walkthrough", "", f"Starting setup created: **{seeded_at}** (UTC).", "", "These are fictional local test people, not real customers. Their email addresses contain no 'demo'; the reserved `.test` domain does not deliver email. Every account is marked internally as demonstration activity. Passwords below are for this local walkthrough only. This file is ignored by source control.", "", f"Open {root}/sign-in. Use separate browser profiles or private windows for different people; ordinary tabs share sign-in cookies.", "", "## All login details and starting situations", "", "| Person | Role | Email | Password | Starting situation |", "| --- | --- | --- | --- | --- |"]
    for key, (name, role, situation, _) in PEOPLE.items():
        lines.append(f"| {name} | {'Examiner' if role == 'researcher' else role.title()} | `{email(key)}` | `{credentials[email(key)]}` | {situation} |")
    lines += ["", "## Stations to open", "", "Fictional app stations are deliberately not plotted as real charging facilities. Existing historical catalogue map markers remain available for testing search and map navigation.", "", "| Station | Capacity | Starting use | Manager | Direct page |", "| --- | --- | --- | --- | --- |"]
    use = {"rosebank": "5 charging, 8 waiting", "sandton": "1 paused, 1 finished while plugged in", "melrose": "Mia's ten-minute offer", "parkhurst": "Ethan finished while plugged in; 1 spare app slot", "braamfontein": "Paused: blocked access; open private report", "rivonia": "Offline: fault; acknowledged private report"}
    for key, (name, capacity, manager_key) in STATIONS.items():
        lines.append(f"| {name} | {capacity} | {use[key]} | {PEOPLE[manager_key][0]} | [Open]({root}/app/chargers/{identity('charger', key)}) |")
    lines += ["", "## Each person's individual walkthrough", ""]
    for index, (key, (name, _, situation, steps)) in enumerate(PEOPLE.items(), 1):
        lines += [f"### {index}. {name}", "", f"Sign in: `{email(key)}` / `{credentials[email(key)]}`", "", f"**Starting situation:** {situation}.", "", f"**Try this:** {steps}", ""]
    lines += ["## Best presentation order", "", "1. Sarah: open Rosebank in Manage chargers. See five active charging drivers, capacity five and eight people waiting.", "2. Thabo + Nomsa in separate browser profiles: edit Thabo's departure; Nomsa sees the anonymous report. Finish alone keeps the slot occupied. Unplug releases it; Nomsa gets an offer and can accept it once.", "3. Noah: paused charging. Resume, finish, set a reminder and unplug. Compare the server-recorded durations.", "4. Priya: pending return reminder. Replace, cancel and snooze. Ethan: delivered reminder in Notifications, then snooze. Closing the browser does not stop the backend reminder worker; notifications are read inside the app, not external push/SMS/email.", "5. Zanele: compare alternatives and explicitly confirm a queue switch. Sipho: leave/rejoin. Benjamin: expired offer then rejoin. Mia: accept/decline a fresh offer within ten minutes of the reset.", "6. Amahle + David: open blocked-access help report, editable message, manager reply, acknowledge then resolve. Yusuf: fault report and public offline state. Update the public station status separately after resolving the issue.", "7. Aisha/Emma + Sarah: private messages, replies, read markers and notifications. Lucas: older-message loading, history pagination, and a manager closure reason.", "8. Olivia/Naledi: save/remove chargers. Kabelo/Sibusiso: edit profile and add/edit/delete a vehicle. Sibusiso also shows empty states and can start a session at the spare Parkhurst slot.", "9. Sarah: edit a station's name, timezone, status and capacity. Capacity below occupied/offered slots must fail. Pausing/offline stops new offers while preserving existing participants. A manager can close a forgotten session only with a reason. Adding a charger is available in the manager workspace.", "10. Helen: examiner-only historical prediction, insights, model information and explicit Driver demo for Grace. Select PALO ALTO CA / HAMILTON #2, Level 1, 15 June 2020 at 22:00. Grace opens that historical charger to see a labelled suggestion. Change the selected time in Helen's lab to demonstrate real inference with different inputs. This does not feed today's app records into the saved model. Clear the context afterward.", "11. Disconnect the browser network while viewing a current session or manager station. Known information stays visible, the offline notice appears and mutations stop. Reconnect to recover. Check layouts on desktop and mobile.", "12. Sign out and sign in again. Profile, favourites, session state, reports and messages must persist. A driver or manager cannot open research APIs; David cannot manage Sarah's chargers; Helen cannot read private conversations.", "", "## Timers and restoring the starting situations", "", "The five/eight setup is real persisted state, not a frozen screen. Your actions change it. Mia's offer expires after ten minutes; Ethan's reminder is already due; Priya's reminder is due about fifteen minutes after reset; departure estimates expire too. Reloading does not reset timers.", "", "To recreate the starting setup, sign out of these accounts, then run from the backend folder:", "", "```powershell", ".\\.venv\\Scripts\\python.exe -m app.cli seed-showcase --reset", "```", "", "This resets only these owned walkthrough records and invalidates their old logins. It keeps the same passwords, rebuilds relative timers and rewrites this guide. It refuses to reset when unrelated people have interacted with these stations or these people have created operational records outside the walkthrough stations. It does not delete other accounts or change the saved model. Manually added chargers are preserved.", "", "Running `seed-showcase` without `--reset` keeps your current progress. If the credential manifest is missing while accounts exist, the command stops rather than silently inventing replacement passwords.", "", "## What is intentionally not claimed", "", "Blocked access means a physical-access report or a charger paused/offline by its manager; there is no account-suspension feature. An app offer does not reserve a physical bay. Charger data is participant-reported, not hardware telemetry. Queue alternatives use clear sorting rules, not a fabricated predicted wait. The unchanged saved model supports explicit historical examples only. No real person's credentials are included here."]
    (directory / "ACCOUNTS_AND_WALKTHROUGHS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def seed_showcase(*, reset: bool = False, directory: Path | None = None) -> None:
    if get_settings().is_production:
        raise SystemExit("Fictional walkthrough accounts cannot be seeded in production.")
    directory = directory or project_root() / ".local" / "showcase"
    manifest_path = directory / "accounts.json"
    with SessionLocal() as db:
        db.execute(text("SELECT pg_advisory_xact_lock(726420281)"))
        exists = _preflight(db, reset)
        if manifest_path.exists():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if manifest.get("version") != VERSION or set(manifest.get("credentials", {})) != {email(key) for key in PEOPLE}:
                raise SystemExit("The local credential manifest does not match this walkthrough. Nothing was changed.")
        elif exists:
            raise SystemExit("Existing walkthrough accounts have no credential manifest. Nothing was reset; restore .local/showcase/accounts.json first.")
        else:
            manifest = {"version": VERSION, "credentials": {email(key): f"{key.split('.')[0].title()}!{secrets.token_urlsafe(8)}" for key in PEOPLE}, "seeded_at": ""}
        directory.mkdir(parents=True, exist_ok=True)
        # Persist generated credentials before committing accounts, so an interrupted
        # operator command never leaves working users with lost passwords.
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        now = utcnow()
        changed = populate(db, manifest["credentials"], now, reset=reset)
        db.commit()
    if changed:
        manifest["seeded_at"] = now.isoformat()
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    write_guide(directory, manifest["credentials"], manifest["seeded_at"])
    print("Created/restored 25 drivers, 2 managers and 1 examiner." if changed else "Existing walkthrough kept; no account progress or timers were reset.")
    print(f"Private account guide: {directory / 'ACCOUNTS_AND_WALKTHROUGHS.md'}")
    print("Rosebank starting setup: 5 charging and 8 waiting. Other people cover pause, finish, reminders, access reports, messages, favourites, history and expiry.")
