# Verification

## Render + Neon deployment preparation — 29 October 2026

The built React application can now be served by FastAPI at one origin, with refreshable nested routes, missing API/assets remaining 404, secure cloud cookies and a readiness endpoint requiring both database and original model. The pinned Python 3.13.9 Docker image and free Render blueprint preserve the original artifact. Cloud initialization upgrades the existing Neon schema and imports only an empty catalogue. A tested copy tool preserves IDs/password hashes/activity into an empty target, refuses overwrites, excludes old login sessions and never changes the source.

Local checks: **69 backend tests passed**, React production build passed, and the actual single-origin app at port 8000 passed driver login, original-model guidance, session/queue reads and research restrictions through `check_deployment.py`. The staged-file audit excluded `.env`, `.local`, database/runtime data and account guides. Existing Starlette/httpx and bundle-size warnings remain. The earlier Windows process probe peaked at approximately 410 MiB resident RAM; it does not verify Linux container/Render memory limits. Cloud connections, the GitHub Linux workflow and deployed smoke checks must be verified separately before claiming a live deployment.

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
