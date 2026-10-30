# Elqovanta EV automatic driver advisory

This records the user's subsequent product decision: a registered driver must not wait for an examiner to select them. Drivers receive an optional automatic advisory; the independent Model lab is for comparing historical months, dates and arrival hours. This supersedes the older build brief's examiner-selected driver-context workflow. The saved model contract remains unchanged.

## Driver journey

1. Register or sign in normally. No demonstration flag or researcher assignment is required. The dashboard links to **Plan your arrival**.
2. Choose a charger and an observed port type. Exact station/port coverage is required by the saved model.
3. The prominent **When will you arrive?** card defaults to **Now**, automatically evaluating the actual current arrival. Choose **Later**, enter a future station-local date/time within seven days and press **Check arrival** for a planned preview. The visible result states the checked arrival, station time zone, port, warning and **Experimental** label. Editing the time hides the previous result until checked again. Neither result promises a physical bay or a waiting time.
4. A flagged result before starting or accepting an offer opens **Continue anyway / Go back**. Going back creates no session. Continuing uses the existing session/queue API and all its capacity, status, expiry, ownership and FIFO checks. It is not a penalty or waiver, and does not override station availability.
5. The selected port is saved with the session or waiting-list entry and carried through offer acceptance. An active session's advisory uses its real plugged-in timestamp; every refresh is not a new arrival.
6. Planned arrival is a read-only preview. It creates no reservation, queue entry, session, reminder, examiner context or prediction log. Joining the waiting list means joining now. Starting or accepting an offer rechecks the actual current arrival, independently of the planned preview. The selected plan resets when leaving the charger page.
7. The Charging Assistant offers an optional return reminder **during charging**, anchored to the estimated target. A warning may suggest it, but only the driver's explicit choice enables it. Updated battery readings move an enabled reminder; opting out persists. The existing separate reminder after reporting charging finished remains available. An advisory never detects hardware completion, supplies consent or ends a session. See `CHARGING_ASSISTANT.md` for the labelled historical illustration and limits.

Unsupported chargers/ports or an unavailable model show **Advisory unavailable** in the same visible card. Manual charging coordination and reminders continue to work. Older sessions with no recorded port may be unscorable rather than receiving an invented connector assumption.

## Planned time and validation

`GET /api/v1/chargers/{id}/guidance?port_type=...&planned_arrival=2026-10-30T15:45` accepts a local date/time **without an offset**, in the charger's configured IANA time zone. The server resolves that wall time to an instant and validates that it is strictly in the future and at most seven days ahead. Offset-bearing values, past dates, malformed values and out-of-range dates are rejected. Nonexistent spring-clock times and ambiguous autumn-clock times are rejected with a readable instruction to choose another time; the server never silently guesses an offset. Without `planned_arrival`, the endpoint uses server now.

The model continues using the original bundle time zone, America/Los_Angeles. The same instant is returned as `arrival_station`/`station_timezone` for the driver and `arrival_local`/`timezone` for the model context in Details. This preserves the original feature definition even for a station with a different configured time zone. Session guidance does not accept a planned-time override.

## Scientific limits

The artifact was trained before 2019, selected on 2019 and evaluated on 2020 sessions. Current-day and future use are **experimental extrapolations**, not prospectively validated forecasts. The card visibly states **Historical model · current conditions have not been validated**; fuller details are collapsed. The original evaluation and its modest performance remain in the Model lab/model card, not as current-day performance claims.

Actual current or explicitly planned inputs are used, never a silently chosen 2020 replacement date. The original seven columns use the same time zone and completion-based previous-30-day window, excluding the entire arrival day. For a date after the frozen history, that window normally has **zero sessions and a missing rate (`np.nan`)**. The application does not substitute a fabricated average or append website sessions to the research history.

The outcome remains strictly more than 30 minutes plugged in without charging. The saved cutoff remains strictly greater than 0.17. A negative flag does not mean zero risk. No probability becomes remaining charge time, departure time or queue waiting minutes. The model uses the arrival **hour**, so changing minutes within the same hour can leave the result unchanged; changed hours can also legitimately produce the same warning flag. No model is created, fitted, tuned, calibrated or replaced.

## Implementation and visibility

- `ml/driver_advisory.py` adapts aware current, planned or real session arrivals to the original fitted pipeline. Results are cached by artifact hash, exact station, selected port, model-local date and arrival hour. Repeated polls and minute-only changes reuse the same inference.
- Driver endpoints return a boolean warning, short suggestion, checked arrival/port context and limitations. They omit probability, cutoff, artifact identifiers, feature values and evaluation metrics. No researcher context or user history is required. Planned results use `mode=experimental_planned`; current/session results retain `experimental_current`.
- `charging_sessions.port_type` and `queue_entries.port_type` remain the nullable additions in migration `20261028_0003`. Planned previews require no schema changes and never replace operational timestamps.
- Research endpoints retain the original **2020-only** date bounds. The lab varies historical months, days, hours, stations and ports independently of drivers. The old driver-selector URL redirects to the lab; legacy context records are not consulted by guidance.
- Normal driver screens show status, counters, actions and visible advisory results. Longer status, reminder, privacy and model explanations sit under **Details**. Offline/stale controls still disable consequential actions; cancelling a warning remains possible offline.

Tests cover original-pipeline parity, station/model-zone conversion across dates, DST rejection, arrival bounds, no backdating/history substitution, new non-demonstration driver access, caching, real changed-hour warning changes, port handover, session privacy and unavailable-model operation. Browser evidence separates real future/current model calls from UI-only warning/continue fixtures, which persist no activity.
