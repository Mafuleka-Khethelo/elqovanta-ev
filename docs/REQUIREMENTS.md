# Elqovanta EV requirements and acceptance criteria

Charging Assistant addition (30 October 2026): combine the target/advisory, optional during-charging return reminder and next action; persist explicit consent and reschedule only an enabled reminder with revised estimates; cancel obsolete schedules. Add time-budget energy/percentage estimates bounded by the chosen target, comparisons capped by known vehicle and manager-reported per-port power, clear unavailable states for missing ratings, and personal session summaries. The labelled historical assistant demonstration remains researcher-only and read-only. No new model or automatic full-battery detection is introduced. See `CHARGING_ASSISTANT.md`.

Vehicle-first addition (29 October 2026): Drivers manage up to five saved cars, choose a default and a persistent current vehicle, search/type model names or supply a missing version manually. Exact sourced presets are distinguished from generic suggestions. The new browser journey requires vehicle selection, current/target percentages, an explicit average-power assumption and a reviewed pre-start estimate; no session clock runs during planning. Both direct start and queue-offer acceptance require a plugged-in confirmation. A waiting driver's plan is provisional/private and their current percentage is re-entered when accepting. Existing API clients and sessions remain compatible. Automatic durable in-app near-target/target notices use the actual server start and stay separate from full-battery confirmation and unplug handover.

The approved `Elqovanta_EV_Codex_Build_Brief.md` governs the foundation, with the user's subsequent automatic-driver-advisory update documented in `DRIVER_ADVISORY.md`. This supersedes the examiner-selected driver-context requirement. No second app or new model was introduced. The current design uses green navigation and a white working area.

## Roles

| Role | Provisioning | Allowed scope |
| --- | --- | --- |
| Driver | Public registration | Own account, vehicles, favourites, sessions, app waiting list, departure expectations, return reminders, help reports, assigned-manager conversations and notifications |
| Station Manager | Local `create-manager` and charger assignment | Assigned-charger status/capacity, current app activity, abandoned-session closure with a reason, reminders, private reports and authorised conversations |
| Examiner / Researcher | Separate local `create-researcher` | Independent Model lab, historical summaries/evaluation and model card; no assignment needed for drivers |

Manager access does not grant research access. Examiner access does not grant private conversation or station-operation access. Backend dependencies and ownership/assignment checks enforce these boundaries, including guessed IDs and direct URLs. Signup/profile requests reject privileged-role fields.

## Main journeys

1. Register/sign in, browse database-backed chargers, inspect App-reported status/source/time and save a favourite.
2. Start directly only when an app slot is free and no earlier participation is being bypassed. Report charging finished and report unplugged. New driver screens have no Pause/Resume controls; historical intervals remain intact.
3. Join one FIFO app waiting list, receive an expiring coordination offer, accept once, or leave. Unplugging reconciles the queue in the same request transaction.
4. Share, revise or retract a voluntary expected departure. Waiting drivers see an anonymous, expiring report in charger time. That report never completes a session or guarantees a turn.
5. After reporting charging finished, choose a return reminder. Cancel or snooze it. A backend worker creates one persistent notification when due. Resume/unplug cancels obsolete pending reminders.
6. Compare app-enabled operational alternatives using stated deterministic rules. An explicit confirmation is required before atomic queue switching; a failed switch preserves the old participation.
7. Submit a private charger-help report. Only its reporter and assigned managers see the details. Managers acknowledge/resolve and send private updates; reports do not automatically change public charger status.
8. Exchange persistent plain-text messages with assigned managers, use editable starters, observe pending/sent/failure states, and retain unread/history state after refresh.
9. Manage only assigned chargers and inspect meaningful current-app counts. Historical model evaluation is absent from the manager workspace.
10. As a researcher, compare genuine 2020 model results across months, days and hours without reading private messages or controlling a driver's guidance. Ordinary drivers automatically receive supported current-arrival experimental advisories and may continue after a warning. They can also preview a planned station-local arrival within seven days, without a reservation or participation. Starting/accepting rechecks now; real session timestamps remain authoritative.

## Acceptance boundaries

- Drivers may save usable battery capacity and AC/DC limits, preview a charging-time calculation, attach it when starting or add it to an accepted/current session. Inputs include current/target percentages and an explicit assumed average battery-delivered power. Updated readings use server time and a new revision. Estimates never confirm full, automatically finish a session or release capacity. Anonymous completion context is shared with waiting drivers; private battery and vehicle details are not. Persistent near-target/target in-app alerts use the active revision and deduplicate delivery. See `CHARGING_ESTIMATES.md`.

- App status is reported, with source and time. It is not verified physical bay availability. Historical observed port labels are not verified compatibility or connector inventory.
- One active participation per driver; outstanding unexpired offers count against configured capacity. FIFO does not use model scores.
- Queue/session mutations use server timestamps, parent-row locks, uniqueness constraints and retry identifiers. Background offer expiry and reminder delivery are restart-safe and deduplicated.
- Leaving soon is optional and anonymous. Reminders are user-selected and independent of inference. No punishment, fees or forced session closure follows a model warning.
- Driver screens and DTOs exclude raw risk scores, thresholds, features, artifact identifiers and evaluation tables. Ordinary registered drivers receive automatic, clearly experimental advisories for supported station/port pairs. No account flag, examiner selection or backdated arrival is required. No warning is invented for unsupported inputs.
- The supplied fitted pipeline, seven features, history protocol, outcome and cutoff remain unchanged. No fitting, tuning, calibration or new weights occur. Operational records never enter the historical frame.
- Every visible new control has a persisted backend action or an explicit unavailable state. Failed active-page updates retain known data with a stale message and disable consequential actions.
- Passwords use Argon2id; login tokens are hashed server-side and held in HttpOnly browser cookies. CSRF, bounded requests, trusted CORS and private ownership checks remain in place.
- Frontend build, meaningful backend/PostgreSQL/concurrency checks, migration consistency, real-model parity and desktop/mobile user journeys must be recorded in `VERIFICATION.md`.

## Outside scope

Charger hardware, payments, penalties, battery/location telemetry, email/SMS/OS push, driving-time routing, prospectively validated model deployment, automatic retraining, and a full administration website. Current-day model use is an experimental extrapolation, not fresh validation. The product is an EV coordination prototype and makes no global novelty claim.
