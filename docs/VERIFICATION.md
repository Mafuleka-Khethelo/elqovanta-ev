# Verification

## Administrator driver oversight - 30 October 2026

- New administrator-only directory and driver details are covered by **2 additional PostgreSQL integration tests**: public privilege escalation rejection, driver/researcher/ordinary-manager denial, explicit admin access, current states, literal search, charger association, needs-attention, pagination, period boundaries, unread-message assignment and exact reported-duration totals.
- Local backend checks: **103 passed across runs**. The first complete run passed 100; three existing temporary-file fixture checks were blocked by Windows sandbox permissions and then passed outside that sandbox. No application assertion failed.
- Frontend: **5 tests passed**; TypeScript and production build passed. The existing large-bundle and Starlette/httpx deprecation warnings remain.
- Migration `20261030_0007` applied to the existing local database; `alembic check` found no missing schema operations. The existing sole manager gained the explicit oversight flag without changing credentials.
- Actual browser: existing manager sign-in, Drivers sidebar, name/email search, charging filter, session-period filter, clear filters, real driver detail sections, and driver/researcher API plus direct-URL denial passed. Directory and details fit 320, 390, 768 and 1440 px without horizontal overflow or JavaScript exceptions; screenshots inspected. These checks created no charging sessions, queue entries or vehicle changes.
- Deployment verification is recorded in [Deployment](DEPLOYMENT.md) after the release becomes live. This feature neither changes nor retrains the saved model.

## Elqovanta Charging Assistant - 30 October 2026

**Live release: `df949f454e0f9a70e5c2862aaed2d012711c4461` at https://elqovanta-ev.onrender.com.** Render reported this exact commit Live and applied migration `20261030_0006` to the existing Neon database. The same free service, accounts and saved model were retained.

This update connects the existing calculator/advisory to an explicitly optional pre-target return reminder, limited-time planning, reported-port-power comparisons and personal session summaries. The historical reminder illustration uses a genuine 2020 prediction with separately labelled hypothetical battery inputs; it creates no live operational records.

- Full local PostgreSQL regression suite: **101 passed**. Final affected assistant/advisory checks: **26 passed**. The initial attempt without a running local database skipped integration checks; PostgreSQL was restored and the full suite then ran successfully.
- Frontend: **5 tests passed** and TypeScript/Vite production build passed. Existing bundle-size and Starlette/httpx deprecation warnings remain.
- Additive migration `20261030_0006` applied locally; `alembic check` found no missing operations. No model/dependency replacement or account reseeding.
- Real local browser checks cover manager power configuration, a 30-minute 60 kWh example giving 6 kWh / 40→50%, different durations under 7/11 kW port ratings, and honest unknown-power comparison states. A preview starts no clock.
- Reminder checks cover default-off state, explicit Not now across reload, consent, chosen lead, reading-based rescheduling, cancellation surviving subsequent readings, actual worker delivery to the owner, and anonymous target notices to waiting drivers. Timer delivery alone leaves charging/queue states unchanged. Finish cancels pre-target reminders; reported unplug triggers FIFO handover. The next driver inherits no consent.
- Personal summaries show reported duration categories, saved target/last reading and reminder delivery without claiming measured battery completion or delivered energy.
- The historical browser illustration shows the real HAMILTON #2 / Level 1 warning at 22:00 and no risk warning at 08:00 on 15 June 2020. Its optional illustrated reminder sends no live notice. Backend checks also verify that changing hypothetical battery capacity changes only the calculator duration, not the warning.
- Layouts checked at **320/390/768/1440 px**; completed journeys have no horizontal overflow or JavaScript exceptions. Temporary local QA drivers and their three isolated chargers are removed after verification, preserving all 16 original accounts and 50 chargers.

- Exact final Linux image: **101 backend tests passed**, **144 independent original-model comparisons matched**, and the hard **512 MiB** probe passed with **422.1 MiB** observed peak for the tested workload. [Successful release workflow](https://github.com/Mafuleka-Khethelo/elqovanta-ev/actions/runs/41025003852). Stored evaluation and 259,366 historical rows remain unchanged.
- Final combined local browser journey completed for manager, two drivers and researcher after correcting startup/encoding/async waits in the QA helper. All created local QA activity was removed; original 16 accounts and 50 chargers retained. The inactive legacy after-finish reminder card is hidden while charging, avoiding a second contradictory reminder prompt.
- Live HTTPS checks passed new time-budget/port-comparison endpoints, owner-scoped reminder data, existing three-role logins, driver research denial, original runtime artifact hash, anonymous summaries and positive/negative historical assistant previews. These checks created no live charging, queue or reminder activity.
- Live driver browser saved one temporary car, reviewed/cleared/recalculated a pre-start two-hour estimate and 30-minute budget, and checked layouts at 320/390/768/1440 px. That car was deleted and the previous vehicle list/selection restored exactly. Existing session identity/state stayed unchanged.
- Live browser also viewed the existing session's assistant and ran the actual historical model at 22:00 and 08:00, exercised the labelled optional reminder illustration and checked all four widths without JavaScript exceptions. Actual durable reminder delivery and FIFO mutation were verified locally rather than altering a user's live session.

Private evidence: `.local/showcase/assistant-browser-results.json`, `assistant-research-browser-results.json`, `live-assistant-readonly.json`, `live-assistant-browser-results.json`, `live-assistant-research-browser-results.json`, related QA/cleanup scripts and `.local/model-check/assistant-*.png` / `live-assistant-*.png`.

## Vehicle-first planning - 29 October 2026

**Live release: `2f56569f0bc79b55d56559cd9a268f061fb1c30f` at https://elqovanta-ev.onrender.com.** Render reported this exact commit Live. The same free service and Neon database were retained; no accounts, passwords or saved model were reset.

The revised driver flow is My vehicles → select today's car → find charger → enter current/target battery and assumed average power → review duration → confirm plugged in → start. Queue offers require a fresh reading and reviewed calculation before acceptance; the dashboard links to that review. Compatibility API clients and existing sessions keep working.

- **88 PostgreSQL backend tests passed**, including owned selection, default fallback/deletion, persisted private provisional queue inputs, invalid-plan transaction rollback, atomic acceptance/estimate attachment and acceptance retries.
- **5 frontend tests passed** and the TypeScript/Vite production build passed. Existing bundle-size and Starlette/httpx deprecation warnings remain.
- Additive migration `20261029_0005` applied locally; `alembic check` found no missing operations. Existing data is retained.
- **144 original-model probabilities matched** within `1e-12`; artifact hash, 259,366 history rows and stored evaluation unchanged. No new trained model or changed numerical dependency.
- Actual local browser journey checked a first-vehicle search gate, filtering model suggestions, exact-version manufacturer-prefilled capacity, two saved cars, default choice, selection across reloads, and a 60 kWh two-hour preview before any session exists. Start stayed disabled until plug confirmation. A 90 kWh car produced a three-hour preview with identical percentages/power.
- A real waiting driver retained a private provisional plan with no session clock. The actual durable worker delivered target-time notices to owner and waiting driver without finishing or freeing the bay. Reported unplug triggered an offer. The offer required a new battery reading and plug confirmation; acceptance attached the reviewed estimate with its actual server start time.
- Layouts checked at **320/390/768/1440 px** with no horizontal overflow or JavaScript exceptions. Screenshots inspected. Temporary QA activity was isolated and removed; all 16 original local accounts and 50 chargers were preserved.
- The final browser regression also clears/recalculates a preview while retaining the selected saved car. The accept action appears after the offer's plan and plug confirmation.
- Final exact Linux container checks passed: **88 backend tests**, **144 original-model comparisons**, and a successful hard-512-MiB probe with **430.2 MiB** observed peak in the tested workload. [Successful final release workflow](https://github.com/Mafuleka-Khethelo/elqovanta-ev/actions/runs/40866921515).
- Actual final live-browser login, vehicle save/selection across navigation, two-hour pre-start preview, Clear details/recalculation, plug-confirmation gate, model-suggestion filtering and all four widths passed with no JavaScript exceptions. The single temporary vehicle was deleted and the previous selection/vehicle list restored exactly. Existing session ID/state stayed unchanged; no live start/join/accept/finish/unplug action was performed. The real worker/handover journey was verified locally, as described above. Live HTTPS checks also confirmed existing driver/manager/researcher logins, the calculator, schema and original runtime model hash.

Evidence is private/ignored in `.local/showcase/check_vehicle_first_browser.mjs`, `charging-browser-results.json`, `check_live_vehicle_first_browser.mjs`, `live-vehicle-first-results.json` and `.local/model-check/vehicle-first-*.png` / `live-vehicle-first-*.png`.

## Car-specific charging estimates and redeployment - 29 October 2026

**Live release: `87f640d4f2144e7e5d31e71c33ab261dd5181a2b` at https://elqovanta-ev.onrender.com.** Render reported this exact manually selected commit Live. The same service, free plan and Neon database were retained; no accounts were reseeded or model changed.

| Check | Result |
| --- | --- |
| Linux release checks | **85 backend tests passed**. [Successful run](https://github.com/Mafuleka-Khethelo/elqovanta-ev/actions/runs/40860685362). Coverage includes energy/power arithmetic, different capacities, AC/DC limits, invalid/nonfinite inputs, read-only previews, atomic estimate attachment, ownership, version conflicts, stale edits, anonymous summaries, cancellation, restart catch-up, duplicate workers and competing updates. |
| Original model and memory | **144 independent probabilities matched**; stored evaluation and 259,366 frozen history rows unchanged. Original hash remains `b1cfde621dd23950b18c73cddf7bee97072f334e8e1355920abeb85318cac626`. Peak **428.9 MiB** in the exact Linux image under a hard 512 MiB container limit for the tested probe workload. |
| Frontend | **5 tests passed**; TypeScript/Vite production build passed. Existing Starlette/httpx deprecation and frontend bundle-size warnings remain. |
| Additive migration | `20261029_0004` adds nullable vehicle details and versioned estimate records. Applied locally; `alembic check` reported no new operations. New live vehicle/estimate endpoints returned successfully, verifying the deployed schema. Existing identities, passwords, participation and history retained. |
| Actual browser journeys | Ordinary temporary drivers saved/edited a vehicle, calculated 60 kWh / 40% to 80% / assumed 12 kW as **24 kWh and two hours**, attached it on start, updated actual battery readings and saw recomputed target times. Accepted driver then calculated a different 40 kWh example as **8 kWh and 48 minutes**. No examiner selection or new model involved. |
| Actual worker/queue | The real local background worker delivered near-target and target-time notices to the owner and waiting driver. Estimated time alone left the session charging and the queue waiting. A driver-reported finish produced its separate queue update; actual unplug created the next offer. A second complete journey passed after the reported-status regression fix. |
| Status regression | Attaching an estimate initially refreshed the charger before its newly reported occupied state had flushed. The start endpoint now flushes that change before acquiring the estimate service's locks. A real HTTP regression and the final browser journey confirm a full configured slot remains Reported occupied. |
| Layout and controls | Local calculator, active-session and queue pages passed at **320, 390, 768 and 1440 px** without horizontal overflow or JavaScript exceptions; screenshots inspected. Pause/Resume buttons removed from driver pages. Historical intervals and deprecated old-client endpoints preserved. Station-level manager closure is labelled Coordination closed. |
| Local QA cleanup | Temporary drivers, their vehicle/calculations, isolated charger and linked activity removed after checking scope. All **16 original local accounts and 50 chargers** preserved, including identity/role/password hashes. No unrelated participation reset. |
| Live HTTPS checks | Existing driver, manager and researcher logins passed. New read-only previews calculated two hours for 60 kWh and three hours for 90 kWh at the same percentages/power; lower-than-current target rejected. New schema, anonymous station summary, driver research denial and unchanged runtime artifact hash verified. These live checks changed authentication records only, with no new charging/queue activity. |
| Live browser | Actual existing-driver UI login, calculator preview, vehicle fields, absence of Pause/Resume buttons and a single advisory through polling passed. Layouts passed at **320/390/768/1440 px**, screenshots inspected and no JavaScript exceptions. The existing driver's session ID/state stayed unchanged. |

Evidence: ignored `.local/showcase/charging-browser-results.json`, `live-charging-readonly.json`, `live-charge-browser-results.json`, related QA scripts and `.local/model-check/charge-*.png` / `live-charge-*.png`. The durable-notification journey above was performed against the real local backend; the deployed release was checked through HTTPS and the real browser without modifying existing operational participation. Current battery values remain owner-entered or explicitly calculated estimates. No vehicle telemetry, trained charging curve, guaranteed full-battery detection or exact-time guarantee on sleeping free hosting is claimed. See [Charging estimates](CHARGING_ESTIMATES.md).

## Live Render + Neon deployment — 29 October 2026

This section records the initial deployment of **https://elqovanta-ev.onrender.com** at revision `4ae432081609e934173f791e95589d13cf47762b` in the private `Mafuleka-Khethelo/elqovanta-ev` repository. The newer release and checks appear above. Render runs one Free Docker service in Frankfurt; Neon Free PostgreSQL 16 stores persistent activity in the same region. Automatic deployment remains off.

| Check | Result |
| --- | --- |
| Exact Linux image | **70 backend tests passed**, using PostgreSQL 16 and the original saved model; React production build passed. [Successful workflow](https://github.com/Mafuleka-Khethelo/elqovanta-ev/actions/runs/40784376568). Existing Starlette/httpx deprecation and frontend bundle-size warnings remain. |
| Saved-model preservation | **144 independent probability comparisons passed** at tolerance 1e-12. Artifact SHA-256 remains `b1cfde621dd23950b18c73cddf7bee97072f334e8e1355920abeb85318cac626`; stored evaluation matches and history remains **259,366 rows**. No training, replacement or new-session history ingestion. |
| Memory | Linux API/model probe completed under a hard **512 MiB** container limit; peak **429.0 MiB**. Hashing and verification share a one-at-a-time guard; existing Argon2 cost parameters remain unchanged. This verifies the measured workload rather than arbitrary traffic or Render's whole-service memory chart. |
| Account/data transfer | **16 existing users, 50 chargers, 56 ports and existing activity** copied to Neon, preserving IDs and password hashes. Existing sessions, queues, reminders, conversations, messages and reports persisted. Old authentication sessions/login attempts were excluded. Source database unchanged. The copy tool refuses populated targets and performs records in one target transaction. |
| One-address HTTPS | Database/model readiness passed. React deep-link refresh, real driver cookie login/logout, original-model guidance, session/queue reads and research denial passed on the public origin. Secure HTTPS cookies verified. Missing API/assets and private file paths remain 404. |
| Real driver onboarding/advisory | Two temporary drivers registered through public signup and immediately obtained current/planned advisories without an examiner context. Planned previews created no participation and exposed no raw score. Unsupported QA charger honestly showed unavailable while manual charging worked. |
| Real charging/queue | Deployed start, pause, resume, finish while plugged in, event history, anonymous departure, waiting position 1, unplug-to-offer handover, accepted port and completed histories passed. Other participants' original operational activity was preserved. |
| Real reminder worker | A chosen short return reminder produced a persistent in-app notification through the deployed background worker. This is an awake-service delivery check; free-service sleeping still prevents an exact-time guarantee. |
| Private features | Favourite add/remove, driver-manager messages and private blocked-access report acknowledgement/resolution passed. A second driver was denied the first driver's conversations/reports. Manager and researcher role boundaries passed. |
| Real model illustration | Researcher sign-in, historical insights and Hamilton #2 / Level 1 / 15 June 2020 at 07:00 versus 22:00 returned actual different saved-model results with opposite warning flags. These requests created normal private prediction logs without changing frozen history. |
| Real deployed browser | Driver, manager and researcher sign-ins/pages passed. Green sidebar and white workspace verified. Current/planned advisory, station time zone and experimental limitation visible at **320, 390, 768 and 1440 px** without page-width overflow. Desktop/mobile screenshots inspected. No JavaScript exceptions. |
| Repeated advisory regression | Actual live active session stayed at exactly **one advisory** and one plans section through timer ticks and multiple polling cycles. Browser checks made no charging, queue or messaging changes. |
| QA cleanup | Temporary signup drivers, their isolated charger and linked test records removed after checks. **All 16 original accounts and 50 chargers preserved**, with identity/role/password hashes checked. No existing users' participation was reset. |
| Repository/security | Private repository includes the original trusted model and deployable source. Secrets, `.env`, `.local`, credential guides, database/runtime files, browser profiles and raw dataset excluded. GitHub's Render installation is limited to this repository. No paid plan selected. |

Evidence remains in ignored `.local/showcase/live-features.json`, `live-browser-results.json`, related QA scripts and `.local/model-check/live-*.png`. Local single-origin backup remains at **http://127.0.0.1:8000** while its processes run; it is separate from Neon and does not synchronize later cloud changes. See [Deployment](DEPLOYMENT.md) and [Presentation notes](PRESENTATION_NOTES.md).

Older dated sections below are a chronological verification record. Current driver advisories are automatic and experimental; raw model details belong to the separate researcher workspace. Earlier role/policy descriptions are superseded by the later changes above.

## Repeated session advisory fix — 29 October 2026

The advisory and coordination components on My session shared the same sibling React key. Each clock update could leave another advisory card behind. They now use distinct, session-specific keys, preserving the existing per-session reset behaviour.

The browser reproduction produced **66 advisory cards after 65 accelerated clock ticks** before the fix. Afterward, exactly **one advisory, one plans section and one departure input** remained through **399 clock ticks**, multiple real five-second polls, a session-state change, offline rendering and **320/390/768/1440 px** layouts. The entered departure value survived polling, no duplicate-key warnings or JavaScript exceptions remained, and the browser fixtures sent no operational mutations. Frontend **5 tests** and the production build passed; the existing bundle-size warning remains. No backend/model changes were needed.

Evidence: ignored `.local/showcase/check_session_advisory.mjs`, `session-advisory-before.json`, `session-advisory-after.json` and `.local/model-check/session-single-advisory-*.png`. Checks used isolated browser fixtures and preserved existing charging records.

## Planned arrivals and visible advisory — 29 October 2026

The charger page now places **When will you arrive?** near the top. Now checks automatically; Later accepts a station-local future arrival within seven days and displays the checked time, port, result, Experimental badge and accuracy limitation. The dashboard has a compact Plan your arrival link. Longer explanations remain under Details.

| Check | Result |
| --- | --- |
| Backend | **62 tests passed**, including real-pipeline planned-time parity, different station/model zones across midnight, exact seven-day bounds, naive/aware input validation, skipped/repeated DST times, read-only previews and session timestamps immune to planned overrides. Existing Starlette/httpx deprecation warning remains. |
| Frontend | **5 tests passed**, including station-local date and DST formatting. TypeScript/Vite production build passed; existing bundle-size warning remains. |
| Real browser/model | Ordinary public registration immediately obtained actual current and future saved-model results without an examiner. Changed planned times displayed the chosen station-local arrival; editing hid the old result. Past dates were rejected and previews created no participation. No raw model score was returned. |
| Action separation | Browser-only fixtures checked a negative future preview followed by a positive **current** warning on Start. Go back created nothing; Continue sent one request with the selected port. Both offer-acceptance screens retained warnings, offline Continue was disabled while Back worked, and unsupported guidance left manual coordination available. Fixtures persisted no activity. |
| Responsive/visibility | Planner, result, confirmation and session layouts checked at **320, 390, 768 and 1440 px** without horizontal overflow or JavaScript exceptions. Desktop/mobile screenshots inspected. The advisory and experimental limitation are visible without opening Details. |
| Model preservation | **144 independent comparisons passed** at 1e-12 tolerance, original hash and stored evaluation match, frozen history remains **259,366 rows**. No artifact/training/schema changes. |

Evidence: ignored `.local/showcase/arrival-planner-results.json`, `check_arrival_planner.mjs` and `.local/model-check/arrival-*.png`. The temporary QA driver was removed after asserting no persisted operational activity; the requested accounts were preserved. Current/future accuracy remains unvalidated, and unchanged inputs may legitimately produce unchanged warnings.

## Automatic advisories and concise driver screens — 28 October 2026

This later user-directed change removes examiner selection from the ordinary driver journey. The original historical model is unchanged; current-day use is explicitly labelled experimental and is outside its 2020 evaluation. See `DRIVER_ADVISORY.md` for the superseding policy.

| Check | Result |
| --- | --- |
| Backend suite | **55 passed**, including original model integration, normal non-demonstration driver access, direct-pipeline current-input parity, missing-history handling, caching, changed-input warning changes, port handover, session privacy and model-unavailable operation. Existing Starlette/httpx warning remains. |
| Frontend checks | **3 tests passed**, TypeScript/Vite production build passed. Existing bundle-size warning remains. |
| Migration/schema | Additive revision **20261028_0003** applied. `alembic check`: no new upgrade operations detected. Existing data/timestamps retained. |
| Real registration/advisory | A temporary ordinary driver registered through the real UI (`is_demonstration=false`), immediately obtained a real saved-model current-arrival advisory for Hamilton #2 / Level 1, had no examiner context, and could not read research metadata. Current arrival remained 2026, with no raw score returned. |
| Warning controls | Browser-only positive-warning fixtures verified Start -> warning -> Go back creates nothing; Continue sends one request with selected port. Dashboard and queue-page accept flows also warned and accepted once. Continue was disabled offline while Back remained usable. Queue-switch confirmation required its target port; cancelling kept the original place. Fixtures persisted no session/queue activity. |
| Concise/responsive UI | Normal dashboard has only two visible paragraph elements (greeting/status label), short facts/actions and collapsed Details. Driver charger/session/confirmation pages checked at **320, 390, 768 and 1440 px**. No page-width overflow or JavaScript exceptions. Screenshots inspected. |
| Independent Model lab | Actual research-account browser comparisons used 15 June 2020 at 07:00 and 22:00 and 1 January 2020 at 07:00. Real probabilities differed, including opposite warning flags. The former driver-selector URL redirected to the lab and was absent from navigation. Layouts passed at 320–1440 px. |
| Artifact preservation | **144 independent probability comparisons passed** at tolerance 1e-12; loaded/original artifact and saved evaluation still match; frozen history remains **259,366 rows**. SHA-256 unchanged: `b1cfde621dd23950b18c73cddf7bee97072f334e8e1355920abeb85318cac626`. |

The temporary public-registration check account was removed after asserting it had no persisted operational activity. The requested ten practice drivers and six original accounts remain intact. Driver warning UI scenarios used explicit browser fixtures; real-model behaviour was separately checked through direct pipeline comparisons and live HTTP calls. Evidence is in ignored `.local/showcase/automatic-advisory-results.json`, `model-lab-results.json` and `.local/model-check/automatic-*.png`. Research comparison requests produced normal private prediction logs, without altering frozen model history.

## Clean dashboard and ten fresh drivers — 28 October 2026

At the user's request, the internal workspace now uses a green sidebar (`#24645d`), white content (`#ffffff`), lime active navigation (`#cef695`), compact counts and plain charging/status lists. The large dashboard car illustration and promotional panels were removed. The supplied reference informed the layout; unrelated financial data/charts were not added.

| Check | Result |
| --- | --- |
| Account replacement | Exactly the previous **28 account IDs** and **six unused fictional stations** removed. Their sessions, waiting lists, reminders, messages, reports, favourites, vehicles and logins were cleared. No unrelated links existed at those stations. |
| Original account protection | All **six original accounts** preserved, with identity, role and password-hash snapshots compared inside the transaction. Original catalogue and model preserved. |
| Fresh drivers | **Ten driver accounts** created with one shared password, separate salted hashes and fresh IDs. No starting session, waiting-list place, vehicle, favourite, report, message, notification or history. Private guide updated; the old 28-person login document is replaced. |
| Actual account checks | All ten shared-password logins passed HTTP and real browser checks. Own-session/queue/favourites/conversations/history were empty. Research access was rejected. Sign-out succeeded. |
| Production/frontend checks | TypeScript/Vite production build passed; **3 frontend tests passed**. Existing bundle-size warning remains. No new dependencies. |
| Browser layouts | Ten driver dashboards plus the original manager and examiner tested. Representative pages checked at **320, 390, 768, 1024 and 1440 px** as applicable. White workspace and green navigation verified through computed styles. No page-width overflow or JavaScript exceptions. Screenshots inspected. |
| Retained behaviour | Manager add form, original role restrictions, sidebar links, mobile drawer/Escape/focus restoration and offline/reconnect controls verified. |
| Active-state presentation | Browser-only fixtures exercised charging, paused, finished-but-connected, waiting and offered states on the new white status card. Correct actions remained visible. Offline controls disabled. These fixtures made no session/queue mutation requests and left the ten drivers empty. |

Evidence: ignored `.local/showcase/clean-dashboard-results.json`, `check_ten_drivers.py` output and `.local/model-check/clean-*.png`. The local account guide is `.local/showcase/DRIVER_ACCOUNTS.md`. The earlier populated-pack results below are historical; those scenarios are no longer present. Backend application logic and model code were unchanged in this dashboard/account simplification, so the previously passing backend suite was not rerun for these visual edits and the scoped data replacement. The account operation was verified directly against the database and HTTP app.

The 28-person populated account pack documented below was subsequently removed at the user's request. The current dataset uses ten fresh drivers with a shared password; original accounts and the model were preserved. See `ACCOUNT_SCENARIOS.md` and its private login guide. Older results describe the scenarios that existed when those checks were run.

## Populated account walkthrough — 28 October 2026

The account pack contains **25 fictional drivers, two station managers and one examiner** with realistic names and individual passwords. Emails contain no "demo". All accounts remain internally labelled as demonstration activity. Login details and personal steps are in the ignored local guide linked from `ACCOUNT_SCENARIOS.md`.

| Check | Result |
| --- | --- |
| Persistent starting setup | Rosebank has **5 actively charging and 8 waiting in FIFO order**. Other stations cover paused charging, finished-but-connected sessions, pending/delivered reminders, current/expired offers, blocked access, an offline fault and a resolved private report. |
| Additional examples | Favourite/vehicle variety, a fresh empty account, **23 completed sessions** and **42 archived private messages** for pagination. |
| Backend suite | **49 passed** against the isolated PostgreSQL test database, including state transitions, concurrency, permissions, model integration, reset safety and status/capacity consistency. Existing Starlette/httpx deprecation warning remains. |
| Frontend tests/build | **3 tests passed** and the final TypeScript/Vite production build passed. Existing main-bundle size warning remains. |
| All credentials | **28 distinct email/password pairs** authenticated through HTTP and the real browser, with the correct role/workspace. |
| Live HTTP features | **15 feature groups passed**: counts/order, anonymous departures/ownership, catalogue/favourites, profile/vehicles/passwords, history/message pagination, private replies/read markers, help reports, manager scope/capacity/timezone, session/reminder lifecycles, queue switching, handover, notification cooldown/read state, saved model/context, and logout. |
| Reminder worker | A two-second chosen reminder was delivered by the independent backend worker with no open browser page. Snooze, cancel, replacement and cancellation on resume verified. |
| Live handover | Thabo unplugged; Nomsa received the first offer and accepted once. Replaying returned the same session. Trying to charge and wait together was rejected. Starting situations were restored afterward. |
| Real browser checks | **28 UI sign-ins** and individual states verified. All account workspaces checked at 390/1440 px; selected sessions, queues, reports, manager details, profile and examiner controls also at 320 px. No page-width overflow or JavaScript exceptions in completed journeys. Screenshots inspected. |
| Controls/offline | Alternatives confirmation/cancel, history next/previous, older-message loading, pending/delivered reminders and offline/recovery checked. Last known data stayed visible and session mutations were disabled offline. |
| Repairs found | Fixed the waiting-reminder manager destination. Finished sessions no longer offer finish again. Older-message loading disables after the last page. Focused browser regressions passed. Fixture public status is reconciled with final occupied-slot counts. |
| Seed safety | No-reset preserves progress. Reset restores only owned rows and the same passwords, invalidates old pack logins, preserves unrelated people, and refuses cross-scope/collision resets. Production seeding is refused. No fictional map coordinates are added. |
| Original model | **144-probability parity check passed**, tolerance 1e-12. Original and loaded artifact match; saved evaluation matches. SHA-256 remains `b1cfde621dd23950b18c73cddf7bee97072f334e8e1355920abeb85318cac626`; frozen history remains **259,366 rows**. No retraining/replacement. |

Test journeys changed only the fictional pack. Its starting setup was restored after verification. Offers, reminders and departures use real server timestamps and continue to expire/deliver normally. `seed-showcase --reset` restores fresh presentation timers; browser reloads do not reset them. Original accounts, the historical catalogue/model and unrelated participation were preserved.

Ignored evidence: `.local/showcase/live-results.json`, `.local/showcase/browser-results.json`, `.local/showcase/browser-fix-results.json` and `.local/model-check/people-*.png`. Local frontend/API servers remain running; verification browsers are closed.

The earlier approved-build-brief checks below were run on 28 October 2026. Older dated runs describe the application at that time; their manager-only research and automatic-advisory descriptions are superseded by the current examiner-only, explicit-demonstration policy. A row is a pass only when its command or complete journey finished successfully.

## Approved build brief — 28 October 2026

| Check | Result |
| --- | --- |
| Complete specification read | All **448 lines** of `Elqovanta_EV_Codex_Build_Brief.md` read; existing compatible application extended. |
| Backend suite | **44 passed** using PostgreSQL, including the actual saved model. Existing Starlette/httpx deprecation warning remains; no compatibility warning was suppressed. |
| Frontend tests | **3 passed**. |
| Production frontend build | Pass: TypeScript and Vite. Existing main-bundle warning remains; no animation/framework dependencies were added. |
| Additive migration | `20261028_0002` applied successfully to the existing application database; current revision is head. |
| Schema consistency | `alembic check`: **No new upgrade operations detected.** The older email constraint declaration was aligned with the existing database constraint. |
| Independent model check | **144 probabilities** matched independently constructed direct pipeline calls within absolute tolerance **1e-12**; stored evaluation matches the project reference; includes the no-history case. |
| Artifact preservation | Original and backend-copy SHA-256 both remain `b1cfde621dd23950b18c73cddf7bee97072f334e8e1355920abeb85318cac626`, matching the pre-change hashes. Python is **3.13.9** and the recorded numerical package versions are unchanged. |
| Role boundaries | Real separate driver, assigned-manager and examiner browser contexts. Driver/manager research requests return **403**. Examiner manager-overview and private-conversation requests return **403**. Backend tests also reject a research role through signup and real-driver demo configuration. |
| Session and queue correctness | Tests cover durations, impossible transitions, retries, competing last-slot starts/joins, competing accepts, expiry, and one handover notification. Atomic switch tests require confirmation, preserve participation on failure and replay without duplicates. |
| Departure lifecycle | Anonymous two-timestamp public response, expiry/retraction/ownership, no automatic session completion, and cleanup on unplug verified. A real waiting driver saw the other participant's anonymous report. |
| Durable reminders | Tests cover persistent delivery, deduplication, two simultaneous workers, snooze/replacement and cancellation on resume/unplug. In the real browser journey a driver tab stayed closed while the backend created the notification; it was present on return. |
| Private help and communication | Real driver help report, assigned-manager resolution/update, editable starter, sent state, manager reply and persistence after refresh. Other-driver report list stayed private. Concurrent read-marker test passes after fixing the observed first-insert race. |
| Historical demonstration | Real examiner-selected Hamilton #2 / Level 1 / 15 June 2020 at 22:00 context. Labelled driver banner and optional reminder suggestion visible; DTO excludes probability/cutoff/artifact/features. Ordinary current sessions have no automatic model forecast. Context was cleared after the check. |
| Manager timezone and stale state | Real manager timezone saved/read back, then restored on the isolated demo charger. Browser offline emulation retained known data, showed a stale/offline message, disabled changes and recovered online. Explicit offline detection handles paused queries as well as failed requests. |
| Responsive/browser checks | Driver historical-demo page and manager add/details forms checked at **320, 390, 768 and 1440 px**, with no page-width overflow. Desktop/mobile screenshots inspected. Earlier account/dashboard checks cover 1024 px as well. No JavaScript exceptions in the completed journeys. |
| Running local services | API health reports **database: ok**, **prediction: ready**; frontend serves the current app. No external deployment performed. |

Browser checks used labelled demo accounts and clearly named, isolated demonstration charger records. Working unrelated participation was not reset. Completed check sessions were unplugged, accounts signed out and temporary historical contexts cleared. Test-generated demonstration messages/reports/history remain persisted and labelled; they were not represented as historical training data. The browser was closed after verification and local app servers remain running for review.

Verification scripts, screenshots and runtime logs remain in ignored local paths. PostgreSQL software-test fixtures use the separate test database; real-browser records use labelled demonstration accounts. No real account was created for the registration-response fixture check. The original notebook, dataset and model binaries were not rewritten. See `BUILD_BRIEF_IMPLEMENTATION.md` and `DEMO_SCRIPT.md` for the implementation mapping and presentation flow.

## Account and dashboard redesign — 28 October 2026

| Check | Result |
| --- | --- |
| Frontend production build | Pass: TypeScript and Vite. Existing main-bundle size warning remains. |
| Existing frontend tests | Pass: **3 tests**. |
| Real account flows | Pass: driver and manager sign-in to their respective dashboards; unsuccessful sign-in feedback; sign-out after verification. |
| Responsive layouts | Pass: sign-in, registration and both dashboards at **320, 390, 768, 1024 and 1440 px** with no page-width overflow. Desktop/mobile screenshots inspected. |
| Driver role visibility | Pass: driver dashboard has no research navigation or model metadata. |
| Mobile navigation | Pass: drawer opens, Escape closes it, focus returns to the menu button. |
| Manager interactions | Pass: real assigned-station search and add-form disclosure; fixture-based status filtering, next/previous pagination and add-form server errors. |
| Driver states | Pass with browser-only fixtures: no stop, charging, paused, finished while plugged in, waiting, offered and request failure. Visible-page five-second session polling observed. |
| Registration | Pass with browser-only responses: native short-password validation, field-associated server errors, exact registration payload and returning to the intended protected destination. No real account was created for this check. |
| Browser stability | Pass: no JavaScript exceptions in completed journeys. |

See `WORKSPACE_DESIGN.md` for design sources and the boundary between real-account checks and browser-only fixtures. No backend code or model artifacts changed; the backend suite was not rerun for this frontend redesign.

## Homepage redesign — 28 October 2026

| Check | Result |
| --- | --- |
| Frontend production build | Pass: TypeScript and Vite build. The existing main-bundle size warning remains. |
| Frontend tests | Pass: **3 tests**. |
| Car assets and typography | Pass: all five supplied car illustrations load and cycle correctly; local Manrope font loads. |
| Browser interactions | Pass: walkthrough controls, ArrowDown keyboard navigation, five FAQ disclosures, mobile menu and section links. |
| Motion accessibility | Pass: pause/resume and system reduced motion stop running animations; content stays visible; reduced motion disables smooth scrolling. |
| Responsive layout | Pass: **320, 360, 390, 768, 1024 and 1440 px** widths. No page-width overflow or horizontal headline clipping. |
| Search through authentication | Pass: `HAMILTON #2` and `Level 2` survive a real driver sign-in and return the matching charger. |
| Browser stability | Pass: all page images load; no JavaScript exceptions in the tested journey. Desktop/mobile screenshots inspected. |

See `HOMEPAGE_DESIGN.md` for the palette, source inspiration, asset provenance and implementation details. No backend model or operational rules changed in this homepage work, so the backend suite was not rerun.

## Driver and manager separation — 26 October 2026

| Check | Result |
| --- | --- |
| Full backend suite: `.venv\Scripts\python -m pytest -q -p no:cacheprovider` from `backend` | Pass: **30 tests**. Includes driver denial for model metadata, research options, insights, raw predictions and charger outlook; manager access; driver guidance with no research fields; time-dependent guidance from the real saved model; generic unavailable responses. Existing Starlette/httpx deprecation warning remains. |
| Frontend production build | Pass: TypeScript and Vite build. Existing main-bundle size warning remains. |
| Browser: driver views | Pass: real driver sign-in; no research navigation, model forms, percentages, feature tables or artifact details on the charger page. Compact advisory and current station reports are visible. |
| Browser: direct access | Pass: driver requests to all research pages, including `/about`, show access denied. Raw research and outlook APIs return **403**. |
| Browser: automatic guidance refresh | Pass: observed a second guidance request after the visible page's one-minute interval, with no manual action. Matching inputs may keep the same advisory. |
| Browser: mobile | Pass: the compact driver card fits **390×844** without page-width overflow. Desktop checked at **1440×1000**. Screenshots inspected. |
| Browser: manager presentation | Pass: manager navigation retains research tools. A 15 June 2020, 22:00 Hamilton #2 / Level 1 scenario returns **20.39%**, with 24 hourly bars. About the model still displays the stored evaluation. |
| API health after restart | Pass: `database: ok`, `prediction: ready`. Frontend returns **200**. |

Checks used an isolated headless-browser profile and the configured demonstration accounts. The browser signed out and closed after verification. Local script and screenshots are under `.local/model-check/`. The saved model and its frozen history were not retrained or rewritten, and no new-session data pipeline was introduced. The existing classifier cannot provide a minute-based waiting-time prediction; driver guidance is explicitly labelled as a historical example.

## Interactive model verification — 22 October 2026

| Check | Result |
| --- | --- |
| Full backend suite: `.venv\Scripts\python -m pytest -q` from `backend` | Pass: **27 tests**. Includes real-model hourly parity, repeatability, input sensitivity, empty history, unsupported ports, 2020 date bounds, driver access, API logging and invalid-hour rejection. Warnings: existing Starlette/httpx deprecation and sandbox restriction on pytest cache creation. |
| Frontend: `npm test` | Pass: **3 tests**. Vite's configuration loader needed execution outside the filesystem sandbox. |
| Frontend: `npm run build` | Pass: TypeScript and production build. Existing main-bundle size warning remains. The build needed execution outside the filesystem sandbox. |
| Independent artifact check: `scripts/check_model.py` | Pass: **144 predictions**, across two stations and three dates, matched independently constructed direct pipeline calls within absolute tolerance `1e-12`. Repeat inference passed the same tolerance. The loaded model hash matched the original. |
| Running API health | Pass: `database: ok`, `prediction: ready`. |
| Browser: driver sign-in and charger card | Pass: real driver sign-in, 24 hourly bars, lowest-hour **5.07%** and highest-hour **20.39%** at Hamilton #2 on 15 June 2020; warning changes at the 17% cutoff. |
| Browser: changed date | Pass: editing shows a pending-input notice; submitting 1 January 2020 recomputes **5.94%** at 08:00 and updates the earlier count to **304**. |
| Browser: Prediction Lab | Pass: driver can open the lab, submit 07:00 and 22:00 scenarios, and see both submissions and **+15.32 percentage points** in the comparison. |
| Browser: desktop/mobile | Pass: inspected at **1440×1100** and **390×844**. Lab and charger pages have no page-width overflow, mobile hour controls work, and no JavaScript exceptions occurred in the tested journey. |

Browser checks used the installed headless Chromium, a separate project-local profile and the configured demonstration driver. Screenshots are local verification files under `.local/model-check/`, which is ignored by Git. The original model and raw data were not rewritten. See `MODEL_CHECK.md` for inference examples and `DEMO_SCRIPT.md` for the model-first presentation.

## Environment — original 19 October 2026 verification

- Python 3.13.9 via `py -3.13`, virtual environment `backend\.venv`
- Packages from `backend/requirements.txt`, including scikit-learn 1.7.2, pandas 2.3.3, numpy 2.3.5, scipy 1.16.3, joblib 1.5.2 and threadpoolctl 3.5.0
- Node.js 24.14.1
- PostgreSQL 16 started from the binaries in `.tools`, after extracting `share` and `lib` from `.tools\installers\postgresql-16.15-5-windows-x64-binaries.zip`. The first extract contained only `bin`, and `initdb` failed until `share\postgres.bki` was present
- Docker was not used. An earlier Docker version check did not return

## Commands and results

| Check | Result |
| --- | --- |
| `python -m app.cli init-db` | Pass. Alembic applied revision `20261019_0001` |
| `python -m pytest` in `backend` | Pass. 18 tests, 1 Starlette deprecation warning about httpx. First run failed `test_login_is_throttled` because a rejected login rolled the attempt back with the error. Failed attempts are now committed before the 401, and the suite then passed |
| `npm test` in `frontend` | Pass. 3 tests for duration, status wording and coordinate notes |
| `npm run build` | Pass. TypeScript and Vite production build completed. Vite noted the main JavaScript file is larger than 500 kB because the map library is included |
| `import-catalogue` | Pass. Created 47 charger names and 56 observed port types. 0 inconsistent coordinates, 0 omitted from the map |
| `seed-demo` | Pass. Demonstration manager assigned to `PALO ALTO CA / HAMILTON #2` with application capacity 1 |
| API health | Pass. `database: ok`, `prediction: ready` |
| Saved model contract | Pass. Startup log: `metrics_match=True`. The stored 2020 comparison agreed with the project reference |
| Model parity test | Pass. `test_saved_bundle_matches_direct_pipeline_calls` ran against `ev_charger_bundle.joblib`, not a synthetic stand-in |

The parity test and the other backend tests cover registration, manager privilege, private notifications, queue capacity, offer expiry, session durations including multiple pauses, idempotent import, the strict 0.17 warning rule, the 30-minute label boundary, and the 30-day history window.

## Live two-account journey

Against the running API, with the three demonstration accounts:

- A driver request to the manager overview returned 403
- Driver 1 saved Hamilton #2 once; a second save did not duplicate the favourite
- Driver 1 was offered the only app slot and accepted it, which created a charging session
- Driver 2 joined and was position 1. A direct start returned 409 because that driver was already waiting
- Driver 1 paused, resumed and unplugged. The durations were 0 seconds because those reports happened within the same second. The automated duration tests use separated timestamps and check non-zero pauses
- Driver 2 was then offered the slot and accepted it
- Driver 2 messaged the manager and the manager replied. Driver 2’s notification list contained the new message and the coordination offer. Refreshing the favourite and history endpoints still showed the saved charger and one completed session
- Historical prediction for `PALO ALTO CA / HAMILTON #2`, the first observed port type, 15 June 2020 at 08:30 returned mode `historical`, probability about 0.055077, warning `false`, 64 earlier sessions and a long-session rate of 0.125. That number came from the saved pipeline. It is not a live availability forecast

Driver 2’s verification session was then reported unplugged, so neither demonstration driver is left in an open session.

## Browser

The site was opened at http://localhost:5173 . The landing page showed the service explanation, Register and Sign in. The sign-in form accepted the demonstration email and showed “Signing in…”. The browser tool then disconnected and did not reconnect, so these were not completed in the browser:

- finishing sign-in and clicking through both drivers
- desktop and mobile layout
- an unauthorised page address such as `/app/manage` while signed in as a driver
- map tiles and the list/map toggle

The same journeys were completed through the HTTP API, as listed above. Open http://localhost:5173 while the two development servers are running to click through the demonstration script.
