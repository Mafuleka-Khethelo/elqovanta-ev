# Elqovanta EV administrator overview

The approved project-owner update adds **Drivers** to the existing manager account's sidebar. This is read-only operational oversight, separate from charger management and the protected researcher workspace.

## What the administrator can see

- A paginated directory of registered drivers, including drivers with no charging activity.
- Search by name or email; filter by current charging/queue state, no saved vehicle, saved chargers, charger and needs-attention state.
- Session periods: all time or sessions started in the last 7, 30 or 90 days. Current participation and help/message counts remain current; they are not backdated by this filter.
- Matching-driver counts, charging, waiting, valid offers, finished-but-connected sessions, open help reports, unread messages addressed to this manager and completed sessions.
- Each driver's reported connected/charging/noncharging duration totals and paginated session details, vehicle information, saved chargers, manager-conversation references, help reports, saved charging estimate and return-reminder delivery state.
- Needs attention means finished but connected, expired offer awaiting reconciliation, an unresolved help report or messages unread by this assigned manager. It does not mean an account is blocked or a driver should be penalised.

The charger filter includes drivers associated through a session, queue entry, favourite, conversation or help report. State and session totals then use that charger. Vehicles and registration details remain account-wide. The session period applies to sessions by plug-in/start timestamp; favourite, report and conversation sections show their most recent 20 records, with total counts. Driver/session pagination runs in PostgreSQL and updates while the page is visible.

Battery percentages and target times are saved estimates or driver-entered readings. No hardware battery measurement, actual energy delivered, guaranteed availability or model probability is inferred. Demonstration accounts/activity stay labelled. Passwords, password hashes, login tokens and model internals are never returned by these endpoints.

## Permissions and existing login

`User.is_admin` defaults to false. Both `role == manager` and the explicit flag are required by `/api/v1/admin/drivers` and `/api/v1/admin/drivers/{id}`. Public registration and profile requests cannot grant it. Driver, researcher and ordinary manager accounts cannot access the directory or detail endpoints, even with a known driver ID.

Migration `20261030_0007` preserves every account and password hash. For this existing single-manager project it grants the sole existing manager the new oversight flag, so the owner's existing login works. If multiple managers already exist, the migration grants nobody; an operator must choose explicitly. Future managers receive no automatic grant.

From `backend`, grant or revoke an existing manager without resetting their password:

```powershell
.venv/Scripts/python.exe -m app.cli set-admin --email manager@example.com
.venv/Scripts/python.exe -m app.cli set-admin --email manager@example.com --revoke
```

Administrator oversight does not extend charger assignments or private conversation access. Links to change a charger or read/reply to messages are offered only for this manager's assigned chargers; the existing backend assignment checks still apply. Model internals remain researcher-only. This release adds no account deletion, impersonation, password viewing, public role editor or automatic account blocking.
