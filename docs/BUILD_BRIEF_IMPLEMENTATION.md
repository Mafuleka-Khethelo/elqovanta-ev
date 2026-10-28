# Elqovanta EV approved brief implementation

Subsequent user-directed update: normal drivers now receive automatic experimental advisories without an examiner assignment. The separate Model lab illustrates historical month/day/hour comparisons. This supersedes the earlier selected-driver demonstration workflow in the original brief; model weights, features, cutoff and frozen history remain unchanged. Current implementation and scientific limits are in `DRIVER_ADVISORY.md`.

The complete 448-line `Elqovanta_EV_Codex_Build_Brief.md` was read before these changes. The existing compatible React/FastAPI/PostgreSQL application was extended. The original notebook, dataset, fitted model and environment manifest were preserved.

| Stage | Existing functionality retained | Approved additions |
| --- | --- | --- |
| 1 — Foundation | Landing/account pages, database-backed catalogue, Argon2id/cookie/CSRF authentication, profiles and existing design | Separate researcher role and local provisioning; Elqovanta EV naming across current documentation and interface |
| 2 — Coordination | Session intervals/events, FIFO waiting, expiry, configured capacity, manager assignments | Anonymous departure expectations; durable return reminders with cancel/snooze; cancellation on resume/end; direct driver next actions; reliable handover |
| 3 — Communication and personal features | Favourites, personal history, private conversations and notifications | Private help tickets and manager responses; editable message starters; pending/sent/error states; atomic read receipts; deterministic alternatives and explicit atomic switching; status/report freshness |
| 4 — Research | Original fitted pipeline, seven fields, completion-based historical window, evaluation and hourly comparisons | Examiner-only API/routes; explicit eight-hour 2020 context for labelled demo drivers; minimal cached driver assistant; removal of automatic current-clock replay |
| 5 — Finish | Existing deployment-free local setup and working app data | Additive migration, concurrency/privacy/lifecycle checks, real multi-user browser journey, updated setup/model/demonstration documentation |

## Important decisions in simple terms

- Saying “I expect to leave” does not mean the car has unplugged. Only an actual unplug report or an authorised recorded manager closure releases its app slot.
- A reminder is something the driver chooses. PostgreSQL stores it, and the backend creates one in-app notification when due. A closed page does not erase the schedule.
- Switching queues first checks both chargers and the driver's current participation inside one transaction. It either completes the whole switch or leaves the original place intact.
- Help reports and messages stay private. A user report is not treated as a verified hardware fault.
- Managers run station operations. Examiners inspect historical research. Neither role silently inherits the other's access.
- The old automatic selection of a current-clock 2020 example has been removed. Historical suggestions appear only after an examiner explicitly selects a supported context for a labelled demo driver. Normal current sessions receive no model forecast.
- The model is applied as saved. Its probabilities are never converted to departure or waiting times, and new app records never become model inputs.

## Where to look

`backend/app/services/coordination.py` contains departure/reminder/help rules. `backend/app/api/v1/coordination.py` exposes the protected coordination and demonstration APIs. `frontend/src/features/coordination/` contains the driver controls and plain-language updates. `frontend/src/features/research/DemonstrationPage.tsx` is the examiner setup screen. The schema extension is `20261028_0002_coordination.py`.

The approved white/forest/lime identity was retained as an existing-project design adjustment. Internal database names, legacy demo email identifiers and model feature keys were preserved where renaming would disrupt working records. The product name is Elqovanta EV.

See `VERIFICATION.md` for evidence and limits of completed checks, `README.md` for exact Windows commands and `DEMO_SCRIPT.md` for the presentation flow. No external host was used.
