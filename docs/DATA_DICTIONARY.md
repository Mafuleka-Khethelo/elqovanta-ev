# Data dictionary

Vehicle-first planning adds `vehicle_preferences`: one private row per user with owned selected/default vehicle references (`ON DELETE SET NULL`). `queue_entries.charge_plan` is nullable JSON of that user's provisional calculation inputs, returned only in their own queue view. It has no target timestamp, session clock or reminder until actual start; the offer UI requires a fresh reading before atomic session/estimate creation. Existing rows are preserved by additive migration `20261029_0005`.

Migration `20261028_0003` adds nullable `port_type` (up to 120 characters) to `charging_sessions` and `queue_entries`. It records the driver's selected observed port, is retained through offer acceptance, and supplies automatic advisory context with the real session arrival. Older rows remain nullable rather than receiving invented port values. Advisories use the unchanged frozen model history, not these operational tables; see `DRIVER_ADVISORY.md`.

Timestamps in the tables below are timezone-aware UTC and are returned as ISO 8601 strings with an offset. Historical bundle timestamps are a separate kind of value: timezone-naive Palo Alto wall-clock times. They are not converted to UTC.

## Operational tables

| Table | What it stores |
| --- | --- |
| `users` | Email, Argon2id password hash, display name, role (`driver`, `manager` or `researcher`), demonstration flag |
| `auth_sessions` | SHA-256 of the login token, expiry, revocation time |
| `login_attempts` | Recent sign-in successes and failures, used for throttling |
| `vehicles` | Optional nickname, model and port preference owned by one user |
| `chargers` | Exact station key, display name, coordinate flag, App-reported status, status time/source, timezone, service capacity, coordination on/off |
| `charger_port_types` | Observed type labels. `origin` is `historical` or `manager`. A label is not a physical connector count |
| `manager_assignments` | Which manager may administer which charger |
| `favourites` | One saved pair of user and charger |
| `charging_sessions` | One driver’s report at one charger, with plug-in and unplug times |
| `charging_intervals` | Periods while charging was reported as active |
| `session_events` | The timeline, including who acted and a manager’s reason |
| `queue_entries` | Waiting-list place, state, offer expiry and the session created if the offer was accepted |
| `conversations` | One thread for one driver and one charger |
| `messages` | Message text, sender, server time, and a client request id that prevents a retry from inserting a duplicate |
| `read_markers` | How far each participant has read a thread |
| `notifications` | Recipient, unique event key, text, in-site destination, read time |
| `charge_estimates` | Immutable session calculation revisions: owner-only vehicle/capacity/percentage/power snapshots, anchor/target timestamps, version, request key, one active revision and near/target notification flags. Anonymous shared DTOs omit identity and battery details. No row enters model history. |
| `prediction_logs` | A historical lab request and the model’s result. This is not an app charging session |
| `departure_reports` | One report per session: owner, expected UTC unplug time, report time and active/retracted/expired/ended state. Public DTOs contain only the two timestamps |
| `reminders` | Session/owner, user-chosen due time, pending/delivered/cancelled state, unique owner/request key and notification reference |
| `charger_reports` | Private reporter/charger issue, details, open/acknowledged/resolved state, manager response, responder and timestamps |
| `historical_demonstrations` | One explicit 2020 context per labelled demo driver, selecting examiner, charger/port, cached reminder suggestion, selection time and eight-hour expiry |

`chargers.station_key` is the exact `Station Name` string. A suffix such as `#2` is part of the key. `display_name` may be edited by a manager. A later catalogue import refreshes coordinates and historical port labels, and leaves status, capacity, coordination and a custom display name alone.

Coordinate flags:

| Flag | Meaning |
| --- | --- |
| `ok` | Valid points agree closely enough to show a median pin |
| `missing` | No coordinates were recorded |
| `invalid` | Values were present but not a usable latitude and longitude |
| `inconsistent` | Valid points spread by more than 0.01 degrees, so no single pin is invented |

Invalid and inconsistent chargers stay in the list and are omitted from the map.

## Session lifecycle

```text
plug-in report --> charging
charging -- pause --> paused
paused -- resume --> charging
finished_plugged -- resume --> charging (cancel obsolete pending return reminders)
charging or paused -- finished --> finished_plugged
any open state -- unplug or manager close --> unplugged
```

Connected duration is unplug time minus plug-in time, or the current server time while the session is open. Charging duration is the sum of non-overlapping charging intervals, including the open interval when charging is active. Noncharging occupancy is connected minus charging. It includes pauses and time after the driver says charging has finished. It is not “time after the battery became full”.

A driver may have only one open session. The partial unique index `uq_active_session_per_user` enforces that.

Unplug/manager close ends departure reports and cancels pending return reminders. Replaying a successful action key does not add another event or notification.

## Departure and reminder lifecycle

```text
share departure --> active -- expected time passes --> expired
active -- clear --> retracted
active -- session ends --> ended

choose reminder after finish --> pending -- due worker --> delivered + one notification
pending -- cancel, resume or unplug --> cancelled
pending or delivered -- snooze --> new pending occurrence (old pending cancelled)
```

The departure record never modifies plug/unplug timestamps, capacity or queue state. Each snoozed reminder occurrence has its own unique request/notification identity. Notification and delivery state commit together. Closed browsers receive the persisted in-app record on the next visit, with no claim of external push delivery.

## Waiting-list lifecycle

```text
join --> waiting
waiting -- slot free and charger offering --> offered (10 minutes)
offered -- accept --> accepted, and one session is created
offered -- time passes --> expired, then the next waiting driver may be offered
waiting or offered -- leave --> left
paused or offline charger: an open offer returns to waiting; places are kept
```

`waiting` and `offered` are the active states. The partial unique index `uq_active_queue_per_user` allows only one of those per driver. An unexpired offer occupies one configured app slot, just as an open session does. Direct start is allowed only when a slot is free and nobody is already waiting or holding an offer.

Capacity cannot be reduced below the slots already taken. The service capacity is an application setting. Historical import starts with coordination disabled and capacity empty.

## Historical data, kept apart

The bundle key `history` is a pandas DataFrame with `Station Name`, `Port Type`, `Latitude`, `Longitude`, `start_datetime`, `end_datetime`, `total_minutes`, `charging_minutes`, `noncharging_minutes` and `long_noncharging`. Feature construction reads that frame. It does not read `charging_sessions`.

For an arrival date D, the 30-day window is sessions at the same exact station name whose `end_datetime` is on or after D minus 30 days and strictly before midnight at the start of D. The whole arrival day is excluded. If the window is empty, the rate is missing and the fitted pipeline handles that missing value. The website does not replace it with zero.
