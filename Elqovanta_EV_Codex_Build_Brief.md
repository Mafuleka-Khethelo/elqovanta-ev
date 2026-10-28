# Elqovanta EV — Codex Build Brief

Put this file in the project root and ask Codex to follow it in full while working in the existing project. This is a specification for building the application, not evidence that the application has already been built or tested.

---

You are my full-stack engineering partner. Build **Elqovanta EV**, a complete EV charging coordination website for my final-year Computer Science project. I want a functioning website with accounts, station discovery, session management, waiting lists, messaging, notifications and manager tools. My existing machine learning model is one supporting feature in this platform.

**Approved product update — 28 October 2026:** Keep the existing fitted model, preprocessor, seven features, history protocol, 30-minute outcome and 17% warning cutoff unchanged. Do not create another model, retrain, tune, calibrate or replace this artifact. Add the coordination and driver-experience features below around it. The ordinary driver interface shows useful actions and personal progress; model internals and evaluation pages belong in a protected examiner workspace. Any changes to an existing application should preserve working features and follow this updated visibility policy.

I am a student. Keep the implementation understandable, modular and well documented. Explain your important decisions in simple English. Implement real, persistent behaviour behind visible controls. Work through the stages below; do not stop after a plan, homepage, static dashboard or prediction form.

## 1. Start by inspecting my workspace

- Read any applicable repository instructions and inspect existing files before editing. Preserve unrelated work, the original notebook, dataset and model files.
- If this is an empty project, create the structure specified below. If there is already a compatible application, adapt it instead of creating a second competing app.
- Look for `ev_charger_bundle.joblib` and `model_environment.json` in the project root and `backend/artifacts/`. My original bundle was saved at `C:/Users/CASH/Documents/EV Charger/ev_charger_bundle.joblib`. My notebook and CSV stay in that original project folder.
- Copy the trusted model files into `backend/artifacts/` when needed. Preserve the originals. Keep model binaries, raw data, environment secrets and private exports out of Git and frontend assets.
- Read `model_environment.json` before installing Python dependencies or loading the bundle. Use the Python version and numerical-library versions it records. Do not guess the training scikit-learn version, upgrade its dependencies blindly, suppress compatibility warnings, or retrain to make a loading error disappear.
- If an artifact is missing, clearly report the exact missing file and continue independent application work. Prediction must show an honest unavailable state until the real artifact works. Do not generate replacement model weights or invented probabilities.
- Briefly state your implementation plan, then begin implementation. Continue through the authorised scope without repeatedly asking whether to proceed. Record a real blocker when something cannot run in your environment.

## 2. Product purpose and two clearly labelled modes

The product helps participating drivers find charging locations, coordinate use of chargers, communicate with managers and keep records of their sessions.

### A. Current application activity

Accounts, messages, waiting lists, notifications, favourites and charging sessions are real records created in this website's database. Charger status comes from participating drivers and managers. Label it **App-reported status**, show when it was last updated and identify its source.

This version has no charger hardware connection. It cannot verify that a physical parking bay is vacant or enforce an actual station reservation. A free app-managed slot is not proof of physical availability. Describe queue offers as coordination offers for participating users.

### B. Historical research and prediction

The supplied data covers Palo Alto charging sessions from 2011–2020. The frozen model was tested on 2020 sessions. Provide a protected examiner-only **Historical Prediction Lab** with arrival dates restricted to 1 January–31 December 2020. Do not put this lab, historical dataset charts or model evaluation in the normal driver navigation.

For assessment, provide an explicitly labelled historical demonstration of the normal driver journey. In that mode, an examiner-selected supported 2020 arrival context may produce a small contextual Charging Assistant suggestion inside the usual charger/session page. Show its historical demonstration date clearly. Do not silently backdate a current session, require ordinary drivers to fill in a research form, or call a 2020 estimate a current forecast. Ordinary current-app sessions use reported status and user-controlled reminders; prospective ML use needs fresh records and validation outside this build's scope.

Historical predictions must not appear to be current forecasts, live availability, predicted departure times or guaranteed waiting times. The live application database and historical research history are separate sources. Newly recorded application sessions must not silently change the frozen research evaluation or feed this model.

The distinctive experience is the connection between discovery, an app waiting list, session updates, reminders, messaging and research insights. Do not market this as the world's first EV charging platform or claim global novelty.

## 3. Technology and project structure

Use this practical architecture unless an existing compatible repository requires a small, documented adjustment:

| Layer | Choice |
| --- | --- |
| Website | React, TypeScript and Vite |
| Navigation | React Router |
| Server data | TanStack Query |
| Styling | Tailwind CSS and reusable accessible components |
| Icons | Lucide or a similarly consistent icon set |
| Map | Leaflet / React Leaflet with proper tile attribution |
| Python API | FastAPI with Pydantic request/response schemas |
| Database | PostgreSQL, SQLAlchemy and Alembic migrations |
| ML inference | The existing joblib bundle, pandas, numpy and scikit-learn |
| Testing | pytest for backend behaviour; appropriate frontend tests and browser checks |

Check current official documentation for setup and compatible package versions. Use a frontend lockfile. Pin the ML dependencies to my recorded environment and produce a reproducible backend dependency file. Use a Vite development proxy for `/api` so the normal local frontend uses same-origin requests.

Keep one frontend and one Python backend, rather than introducing microservices. Use ordinary REST endpoints and short polling for messages, queue updates and notifications. Poll only while the relevant view is active, avoid overlapping requests, and clean up timers. WebSockets, Redis, external email, SMS, payments, charger hardware, deep learning, camera input and automatic model retraining are outside this first version.

Suggested directories:

| Path | Responsibility |
| --- | --- |
| `frontend/src/app/` | Router, providers and application shell |
| `frontend/src/components/` | Shared interface components |
| `frontend/src/features/` | Auth, chargers, sessions, queues, messages, research and manager modules |
| `frontend/src/lib/` | API client, query keys, validation and formatting |
| `backend/app/api/` | Versioned routes and request/response handling |
| `backend/app/core/` | Settings, authentication and shared configuration |
| `backend/app/db/` | Engine, database sessions and model definitions |
| `backend/app/services/` | Business rules, queue transitions and notifications |
| `backend/app/ml/` | Artifact loading, historical features and prediction |
| `backend/artifacts/` | Trusted local bundle and environment manifest; ignored by Git |
| `backend/alembic/` | Database migrations |
| `backend/tests/` | Behaviour and integration tests |
| `docs/` | Architecture, requirements, model card and demonstration script |

Use environment variables, relative/configurable paths and `.env.example`. Do not hardcode my Windows username into application logic. Document a Windows PowerShell quick start. Provide Docker Compose for a local PostgreSQL instance with a persistent named volume; allow an existing PostgreSQL connection through `DATABASE_URL`. Keep application startup simple with a frontend terminal and a backend terminal. Do not deploy to an external host as part of this task.

## 4. Visual direction and usability

Use **Elqovanta EV** as the exact website name in the wordmark, page titles, navigation, authentication screens, notifications and documentation. Preserve working internal identifiers where changing them is unnecessary; model keys and feature column names remain exactly as specified.

Make the website look like a coherent charging coordination product. Use a restrained blue, navy and teal palette, a light background, clear typography and consistent spacing. Suggested colours: navy `#0F172A`, primary blue `#2563EB`, teal `#0D9488`, background `#F8FAFC`. Use amber for warnings and red for errors. Pair status colours with readable words.

Use a public landing page, a desktop app sidebar/top bar and sensible mobile navigation. Support keyboard interaction, visible focus, proper form labels, readable contrast and responsive layouts. Keep loading, empty, success, error, expired-session and permission-denied states consistent. Render user messages as plain text.

Create shared buttons, fields, cards, status badges, dialogs, toast messages, pagination, skeletons and error panels. Keep page files focused. Every visible action must work or have a clear, justified unavailable state. Do not show invented counters, random dashboard trends, fake online users, unsupported ratings or promised integrations.

## 5. Users and permissions

### Driver

Can register, sign in/out, edit their own profile, save optional vehicle information, browse chargers, save favourites, participate in a waiting list, manage their own session, report an expected departure, manage reminders, contact an assigned station manager, submit a charger help report and view their own notifications. Drivers see their own app history, not the training dataset or other users' private records. The optional labelled demonstration can show a simple assistant suggestion, not model internals.

### Station Manager

Can sign in, manage only assigned charger records, update app-reported status and configured service capacity, view activity for those chargers, respond to messages, send appropriate reminders, and close an abandoned app session with a recorded reason.

### Examiner / Researcher

A separately provisioned `researcher` role can access the historical lab, dataset summaries, model card, evaluation results and controlled demonstration settings. This is a limited research workspace, not a full user-administration website. Researcher access alone grants no right to read private driver messages, manage real charger operations or change model weights/settings. Manager access alone does not grant research access.

Public registration always creates a Driver. Manager and researcher access, plus manager charger assignments, are provisioned through a documented local administrative CLI. Do not let a public signup field or editable profile grant either privileged role. No full administration website is required in this version.

Validate permissions on every backend request, including ownership of messages, sessions, notifications and saved records. Frontend route guards are only an interface convenience.

## 6. Required pages and useful behaviour

| Page | Required behaviour |
| --- | --- |
| Landing page | Explain the service, show meaningful product navigation and clear Register / Sign in actions |
| Register / Sign in | Validated forms, real authentication, useful errors and correct post-login destination |
| Driver dashboard | One prominent card for the user's next action, current participation, compact unread counts and favourites; no model metrics or dataset charts |
| Find chargers | Search, list/map toggle, filters and synchronised charger selection |
| Charger details | Identity, coordinates when available, observed port types, fresh app-reported status, app queue, reported departure information, manager contact and quick help actions |
| My charging session | Current state, elapsed connected/charging/noncharging time, session actions and timeline |
| My waiting list | Current position or offer, offer expiry and Join / Leave / Accept actions |
| My history | Paginated completed app sessions and their recorded durations |
| Favourites | Persistent saved chargers with working navigation |
| Messages | Persistent conversation list, messages, unread state, timestamps and send errors |
| Notifications | Persistent list, unread count and mark-read actions |
| Profile / vehicles | Own profile, optional vehicle nickname/model/port preference and password change |
| Historical Prediction Lab — researcher only | Select a historical charger, observed port type and 2020 arrival date/time; receive the real saved model's result |
| Historical insights — researcher only | Date-filtered historical usage summaries and charts, visibly separate from current app activity |
| Manager dashboard | Assigned chargers, active app sessions, queue/offer state and meaningful activity counts |
| Manager charger details | Update allowed metadata/status/capacity, manage reported sessions and view related messages |
| About the model — researcher only | Target definition, dataset period, measured results and limitations in simple language |
| Driver demonstration journey | Normal driver interface with a visible historical-demo banner and contextual assistant suggestion; no technical prediction form or evaluation panel |
| Error pages | Useful 404, access denied, API unavailable and expired-login states |

Map filters can include charger name, observed port type, app-reported operational status and favourites. Do not claim nearest-by-driving-time or connector compatibility from information the dataset does not contain. If optional browser location is used, request it only after the user chooses a location action, handle denial and label straight-line distance accurately. The list must still work when map tiles or location permission are unavailable.

### 6A. Driver dashboard: show the next useful action

Make one journey card the visual centre of the dashboard. Its actual database-backed state determines its content:

| State | Example content and actions |
| --- | --- |
| No active participation | "Where would you like to charge?" — Find a charger / Open favourites |
| Waiting | "You're second in the app queue" — View queue / Compare alternatives / Leave queue |
| Offer received | "A charging space has been offered to you" — Accept offer / Decline; show server-backed offer expiry |
| Charging | "Your reported charging session is active" — Pause / Report charging finished / Contact manager |
| Charging finished, still connected | "Remember to unplug when you're ready" — Set a return reminder / Report unplugged |
| Session completed | "Your session is complete" — View summary / Find a charger |

Keep important queue offers visible rather than hiding them behind an assistant card. Position messages, notifications and favourites as secondary actions. Use empty states rather than invented activity. On mobile, keep the primary action reachable and avoid multiple competing dashboard panels.

Technical details excluded from driver screens include Random Forest settings, feature tables, ROC/F1/precision/recall, confusion matrices, training/test splits, the 17% decision cutoff, raw risk scores and global research charts. Protect research API responses and routes too; hiding a sidebar link is insufficient. Keep plain-language information such as "App-reported", "Updated 2 minutes ago", "Historical demonstration" and a short explanation of an experimental suggestion visible where it matters.

### 6B. Approved coordination features

**1. "I'm leaving soon" reports.** An active participant can voluntarily provide an expected unplug time, revise it or clear it. Store the report time and expire the report after its expected time passes, the session ends or the participant retracts it. Waiting participants see an anonymous message such as "A participating driver expects to unplug around 14:20 — reported 2 minutes ago". This is self-reported information, not a model prediction or promise. Display it in the charger's local timezone, validate unreasonable dates and never imply it is the time a particular waiting user will receive a turn. Do not display the driver's name, plate number or private contact information to the queue.

**2. Return-to-car reminders.** Let drivers choose a reminder when they report charging finished but remain plugged in, and cancel or snooze it. An explicit scheduled time or a short user-selected interval determines the reminder; the current model cannot detect charge completion or predict a return time. Make a reminder easy to enable when an app waiting list exists, without shaming or penalising the driver. A backend job creates one persistent notification when due; delivery does not depend on an open page. Without a separate push integration, an open app can show the new notification on refresh/poll, and a closed app retains it for the next visit. Do not claim SMS, OS push or automatic physical charging detection.

**3. Queue handover.** A reported unplug event releases the app slot, reconciles the waiting list and creates an offer for the next eligible user in one reliable flow. Notification links open the relevant queue/session page. An expected-departure report alone must never release the slot or trigger an offer.

**4. Helpful alternatives.** When a queue exists, offer a short comparison of other app-enabled operational chargers, observed charger types, reported queue sizes and status freshness. Use transparent deterministic filtering/sorting; this is not a second ML model. Explain the reason, such as "Smaller app queue" or "Same observed port type". An optional location filter may use labelled straight-line distance. Do not turn a smaller queue into a predicted waiting time, claim verified vehicle compatibility from `Port Type` alone, or promise a physically free bay. Switching requires explicit confirmation and transactional handling of the user's current participation.

**5. Quick help.** Provide "Charger not working", "Access blocked" and "Contact manager" actions. Operational reports create a persistent, charger-scoped ticket with acknowledgement/resolution status. Authorised managers can respond, resolve it and send a private update to the reporter. A user report does not automatically establish a verified fault or change official hardware status. Keep report details private to the reporter and assigned managers; display only an appropriate manager-confirmed public status.

**6. Trustworthy updates.** Show the source and age of reports, use server timestamps and refresh active views without full-page reloads. Distinguish the last successful app refresh from the time someone last reported physical status. If updates fail, retain the last value with an obvious stale/offline message and disable actions whose outcome cannot be confirmed. Never animate a fabricated live car location, battery percentage or charger connection.

**7. Private, convenient communication.** Retain the existing driver–manager conversation permissions. Add editable quick-message starters such as "I need help with this charger". Show sent/pending/failed states honestly and keep other users' contact details private. Favourites and the driver's own session summaries remain available through short, clear navigation.

### 6C. Useful model output without a model dashboard

Keep the current classifier as the only ML model. In the explicitly labelled historical demonstration, the server can translate its unchanged warning flag into a non-punitive, optional suggestion: "A return reminder may be helpful for this session" with an Enable reminder action. Call it an experimental suggestion in accessible supporting text. Do not label a 17% cutoff crossing "high confidence" or "you will block this charger". Drivers can choose reminders regardless of the score; a low score does not mean no noncharging time.

Provide a driver-facing assistant response schema containing only the demonstration context, suggestion, action and plain-language explanation. Keep the detailed probabilities, raw feature values, artifact identifiers and evaluation data in the protected research endpoint and server logs as appropriate. Recalculate a demonstration suggestion only when its supported charger/arrival inputs change; a queue refresh or vehicle movement is not a new signal for this model. Operational session and queue updates come from application events.

Never add a charger-free-time, remaining-charge-time, battery-life or wait-time model. Never convert the existing classifier's probability into minutes or a clock time. The current model remains an experiment trained before 2019, selected on 2019 and tested on 2020; this build adds website functionality rather than new modelling.

## 7. Importing the historical charger catalogue

The bundle contains `Station Name`, `Port Type`, `Latitude` and `Longitude`. It does not contain a verified inventory of physical connectors or current station capacity.

- Use each distinct exact `Station Name` as a historical charger identity. Preserve the exact string separately from any friendly display name. A suffix such as `#2` must not be removed from the model key.
- Do not treat the number of distinct charger names as a verified number of distinct geographical station sites. Grouping into physical sites requires independently verified metadata.
- Import distinct observed port types per historical charger. Do not turn those type counts into physical connector capacity.
- Validate coordinates; retain a documented representative coordinate only when appropriate. Flag inconsistent coordinates and omit invalid positions from the map without hiding them from the list. Do not invent street addresses, prices or hours.
- Make the import idempotent. Rerunning it must not duplicate records or overwrite manager-maintained operational fields.
- Keep historical metadata and current manager-reported metadata distinct. New manager-created chargers can use normal app features, but the Historical Prediction Lab only accepts exact charger/port combinations supported by the supplied history.
- Queue service capacity is a separately configured application value, not a value inferred from historical names. Historical imports begin with app coordination disabled until configured. A labelled local demonstration setup may explicitly configure a capacity of one for a sample charger; this is a demonstration assumption, not verified hardware capacity.

## 8. Authentication and persistence

Use a maintained password hashing library with Argon2id. Store password hashes, not passwords. Use cryptographically random server-managed login sessions, with only a hash of the session token stored in the database. Use HttpOnly cookies, an expiry, logout revocation, suitable SameSite settings and Secure cookies in HTTPS production configuration.

Protect cookie-authenticated mutations against CSRF using a documented implementation. Use explicit trusted origins and no credentialed wildcard CORS. Do not keep authentication tokens or sensitive user records in localStorage. Use parameterised database access, request validation, reasonable pagination/message limits and login throttling.

Registration, login, logout, current-user lookup and authenticated password change must function. Revoke other sessions after a password change. Do not add a pretend password-reset flow or emails that are never sent. Keep secrets out of logs and Git.

Provide an explicit development seed command with clearly marked demo users. It must never run automatically in production. Use an operator-supplied local demo password and document how to provision a manager and assign a charger. Label demonstration activity; do not present seeded conversations or sessions as real historical user activity.

## 9. Session tracking: measure the right thing

A driver reports plugging in and starting charging. Store the server timestamp and create an app session. Offer actions to pause charging, resume charging, report charging finished while still plugged in, and report unplugging. Treat these as user reports, not charger telemetry.

Track charging intervals and a session event timeline. Calculate durations from timestamps:

- Connected duration: unplug timestamp minus plug-in timestamp, or current server time for an open session.
- Active charging duration: sum the valid, non-overlapping charging intervals; include the running interval for an active session.
- Noncharging occupancy: connected duration minus active charging duration.

This includes pauses before final charging completion. Do not equate all noncharging time with time after the battery became full.

Reject impossible transitions, overlapping intervals and negative durations. Do not accept arbitrary calculated totals from the browser. Repeated requests must not create duplicate sessions/events. A manager override must record who acted, when and why. Do not charge fees or impose penalties based on this prototype's reports or predictions.

Keep expected departure reports and reminder schedules separate from actual observed session timestamps and calculated durations. Resuming charging must cancel any obsolete return reminder associated with a finished-charging report; unplugging cancels all remaining session reminders and clears its departure report. These actions must remain correct under request retries.

## 10. Waiting lists, offers and notifications

Use a first-in-first-out waiting list for an app-enabled charger. A user may have only one active participation across a waiting-list entry, outstanding offer or active session. Make the UI explain how to leave existing participation before switching.

Recommended waiting-list states: `waiting`, `offered`, `accepted`, `left`, `expired`, `cancelled`. Active sessions have their own lifecycle; an accepted queue record references its resulting session.

Rules:

1. Joining creates one persistent waiting entry. Repeated clicks or retries must not duplicate it.
2. An outstanding unexpired offer reserves one configured app slot, just as an active session does.
3. When a slot opens, offer it to the earliest eligible waiting participant. Store a server-side expiry, initially ten minutes, and notify the recipient.
4. Accepting an unexpired offer consumes it and creates at most one session. Expired offers cannot be accepted.
5. On expiry or leaving, release the slot and offer it to the next eligible participant. Recheck after session completion and capacity changes.
6. Support a direct start only when an app slot is free and it does not jump an existing waiting list.
7. Periodically reconcile expired offers on the backend. Do not rely on browser timers or an open page. Make reconciliation and notification creation idempotent.
8. Use PostgreSQL transactions, appropriate row locking, database constraints and a consistent lock order. Test simultaneous joins, offer acceptance and completion so two users cannot obtain the last slot.
9. Prevent capacity being reduced below slots already occupied or offered. Define a clear paused/offline policy that stops new offers and informs affected users without silently deleting active participation.
10. Provide a polite reminder action for an eligible waiting user and a manager. Validate the recipient server-side and apply a cooldown so it cannot become repeated notification spam. A driver can report they are still charging; a model warning is never grounds to remove them.

Show app waiting position and offer countdown, not an invented minute-by-minute wait estimate. Never use predicted risk to reorder the queue or give preferential access.

Notifications should cover new relevant messages, queue offers/expiry, session reminders and manager changes affecting the user's participation. Persist them, support read state and deduplicate repeated events. Notifications are inside the website; no external messages are sent in this version.

## 11. Messaging

Provide driver-to-assigned-manager conversations associated with a charger. A driver sees only their own threads. A manager sees threads for assigned chargers. Do not expose every driver's private profile or allow arbitrary user-ID access to conversations.

Implement persistent messages, chronological pagination, unread counts/read markers, server timestamps, input validation and reliable send error states. Use a client request identifier or equivalent to avoid duplicate messages on retry. Poll for updates while the conversation is visible. Do not show an online indicator unless real presence is implemented. Attachments and public group chats are outside this version.

## 12. Data model and APIs

Use foreign keys, migrations, useful indexes and explicit response schemas. Suggested entities are listed below; combine tables where it improves clarity without losing required behaviour.

| Entity | Purpose |
| --- | --- |
| User | Profile, unique normalised email, password hash and role |
| AuthSession | Hashed login token, user, expiry and revocation |
| Vehicle | Optional user-owned vehicle details |
| Charger | Exact historical key, display metadata, coordinates, app configuration/status and report timestamp/source |
| ChargerPortType | Distinct historical/manual observed type metadata |
| ManagerAssignment | Which manager may administer which charger |
| Favourite | Unique user/charger saved record |
| ChargingSession | User, charger, lifecycle and connected timestamps |
| ChargingInterval | Start/end timestamps for active charging |
| SessionEvent | Auditable reports, transitions and manager override reasons |
| QueueEntry / Offer | Participation order, state, offer expiry and resulting session |
| Conversation / Message / ReadMarker | Authorised threads, persistent messages and read progress |
| Notification | Recipient, event key, content, destination and read timestamp |
| DepartureReport | Active session, user-reported expected unplug time, creation/update time, expiry and retraction |
| Reminder | Owning session/user, chosen due time, state, snooze/cancellation and deduplicated notification reference |
| ChargerReport | Reporter, charger, issue category, authorised manager response and acknowledgement/resolution state |
| PredictionLog | Historical request, artifact identity, result and creation timestamp; separate from current app sessions |

Store operational timestamps as timezone-aware UTC and return ISO 8601 values with offsets. Store historical bundle timestamps according to their separate contract below. Do not apply operational timezone conversions to the already corrected historical wall-clock values.

Use `/api/v1` routes covering health, auth, profiles/vehicles, charger search/details, favourites, own sessions/history, queue participation/offers, conversations/messages, notifications, historical insights/prediction and manager operations. Validate identifiers, ownership, field limits and date ranges. Return consistent errors with suitable 401, 403/404, 409, 422 and 503 responses. Use idempotency keys or equivalent constraints for consequential repeatable POSTs.

Expose OpenAPI documentation appropriately for the environment; keep technical documentation out of the driver navigation. Research lab, model evaluation, historical dataset summaries and demonstration configuration endpoints require the researcher role. Use separate minimal driver response schemas so privileged research data is not merely hidden with CSS. Health should report database and prediction readiness without exposing secrets or private file paths. Model unavailability should disable research inference and historical assistant suggestions while allowing accounts, queues, communication, reported updates and manually chosen reminders to function.

## 13. Exact saved ML bundle contract

The trusted artifact is `ev_charger_bundle.joblib`, saved with `joblib.dump(..., compress=3)`. It contains already fitted objects. Do not call `fit`, `fit_transform`, model selection or threshold tuning while building or running this website.

| Bundle key | Meaning |
| --- | --- |
| `schema_version` | `1` |
| `pipeline` | Fitted sklearn Pipeline: `preprocessor`, then `classifier` |
| `model_name` | `Random Forest` |
| `feature_columns` | Exact ordered seven input columns below |
| `warning_cutoff` | `0.17` |
| `noncharging_threshold_minutes` | `30` |
| `history_window_days` | `30` |
| `exclude_arrival_day` | `True` |
| `timezone` | `America/Los_Angeles` |
| `history` | Cleaned historical sessions DataFrame |
| `validation_year` | `2019` |
| `test_year` | `2020` |
| `test_comparison` | Evaluation DataFrame; metrics as rows and model/baseline labels as columns |
| `test_confusion_matrix` | Two-by-two matrix with labels `[0, 1]` |

Read metadata from the artifact and validate the expected schema. Fail prediction readiness clearly if the contract differs; do not silently reinterpret a different model.

### Target and warning rule

The observed label is `long_noncharging = (total_minutes - charging_minutes) > 30`. Exactly 30 minutes is class 0. This is a project research threshold, not an official parking rule.

The warning rule is **strictly** `probability > warning_cutoff`. Exactly `0.17` produces no warning. The 17% probability cutoff and the 30-minute outcome threshold are different concepts.

### Exact raw feature columns

1. `Station Name`
2. `Port Type`
3. `arrival_hour`
4. `arrival_day`
5. `arrival_month`
6. `station_sessions_30d`
7. `station_long_rate_30d`

`arrival_hour` is an integer 0–23; `arrival_day` is an English weekday name such as `Monday`; `arrival_month` is an integer 1–12. The fitted preprocessor handles these first five as categorical inputs. The last two are numeric. The complete pipeline transforms the seven raw fields into its trained representation; do not duplicate encoding/scaling in JavaScript or manually pre-transform the request before passing it to this pipeline.

### Historical DataFrame columns

`Station Name`, `Port Type`, `Latitude`, `Longitude`, `start_datetime`, `end_datetime`, `total_minutes`, `charging_minutes`, `noncharging_minutes`, `long_noncharging`.

The datetime columns are already corrected, **timezone-naive Palo Alto local wall-clock timestamps**. Do not parse them as UTC or apply the raw source PST/PDT corrections again.

### Historical feature calculation at arrival

Accept a supported exact charger key, observed port type, arrival date and local arrival time. The server derives all seven model fields. Do not let clients submit their own historical rates/counts or post-session values.

Let `D` be midnight at the start of the selected local arrival date. For the **same exact `Station Name` only**, select historical rows satisfying:

`end_datetime >= D - 30 calendar days` and `end_datetime < D`.

Count the selected rows to obtain `station_sessions_30d`. Average their `long_noncharging` labels to obtain `station_long_rate_30d`. If there are zero rows, use count `0` and numeric `np.nan` for the rate. Do not replace the unknown rate with zero or refit the imputer. The fitted pipeline handles its training-defined missing-value treatment.

Important details:

- Group history by charger name only, not by port type or user.
- Use the completion/end timestamp to establish when the historical outcome became known. Do not filter the reference sessions by their arrival timestamp instead.
- Exclude the **entire** selected arrival day, even for an evening arrival. This matches the notebook's daily history protocol.
- Never include later completions or any result from the queried session itself.
- Earlier completed 2020 sessions are legitimate past observations for later 2020 arrivals. The fitted pipeline remains unchanged during this historical replay.
- Use the bundle's history for these features, not newly generated app records or seeded operational sessions.
- Do not use the current session's total duration, charging time, end date, energy or fee as arrival-time model inputs.
- Build a one-row pandas DataFrame and order it with `bundle['feature_columns']`.
- Determine the positive class column from the fitted classifier's class labels and call `pipeline.predict_proba`. Use class `1`, not an assumed unrelated score.
- Keep `np.nan` internal to feature construction. Use JSON `null` for an unavailable historical rate in API responses.

Load the trusted artifact once per backend process using the FastAPI lifespan mechanism. Serve blocking inference through an appropriate worker-thread path, with bounded concurrency. Do not load the binary for every request, expose it publicly, accept arbitrary pickle uploads, or mutate/retrain the shared pipeline.

The protected research response should include the historical mode, selected local arrival timestamp/timezone, model name and artifact identity, outcome threshold, warning cutoff, probability, warning flag, historical session count, historical rate or null, and a short limitations statement. The contextual driver assistant uses the minimal response defined in section 6C. Record historical requests separately if logged.

### Existing measured results — report honestly

Training used pre-2019 sessions, validation used 2019, and the final test used 2020. The selected classifier has 200 trees, `max_depth=None`, `min_samples_leaf=20` and `random_state=42`. Selection and evaluation are finished; preserve them.

| 2020 test measure | Recorded result |
| --- | --- |
| Sessions | 20,094 |
| Precision | approximately 14.43% |
| Recall | approximately 70.43% |
| F1 | approximately 0.2396 |
| ROC AUC | approximately 0.5906 |
| Average precision | approximately 0.1741 |
| True negatives | 7,175 |
| False positives | 10,423 |
| False negatives | 738 |
| True positives | 1,758 |

Use the bundle's stored evaluation objects as authoritative and check they agree with this reference. A simple explanation is: **about 14 out of every 100 warnings were correct, and the model detected about 70 out of every 100 actual long noncharging sessions**.

Do not call recall '70% accuracy', present a probability as a confidence guarantee, describe this as a reliable enforcement tool, or hide the false alarms. For context, always warning had F1 around 0.2210, so the improvement is modest. Show a measured-results panel on the research pages without flooding ordinary user journeys with technical details.

## 14. Historical insights and manager analytics

Researcher-only charts must use the supplied history and explicit filters. Useful summaries include total historical sessions, median connected/charging/noncharging minutes, percentage over 30 minutes, arrivals by hour/day and long-noncharging rate by charger. Label sample sizes and distinguish a percentage from a count. If showing multiple chargers at the same coordinates, do not invent distinct physical sites. These charts and model metrics are not driver dashboard content.

Manager charts must use current app records for assigned chargers: active sessions, waiting participants, completed app sessions and reported noncharging time. Show a real empty state when there is no activity. Keep historical research labels, demo activity labels and current app activity labels visible. Do not infer actual energy delivered, revenue, battery health or carbon savings from fields absent from the bundle.

## 15. Meaningful verification

Prioritise tests that catch real failures rather than tests that repeat implementation details:

1. Registration/login/logout/password change; expiry/revocation; driver cannot obtain manager privileges through request fields.
2. Cross-user and unassigned-manager access is rejected for private sessions, messages and notifications.
3. Queue retries, simultaneous joins and competing accepts do not duplicate participation or overfill app capacity; PostgreSQL is used for concurrency checks.
4. Expired offers cannot be accepted; reconciliation promotes the next eligible participant once and creates one notification.
5. Session pause/resume/unplug sequences produce correct connected, charging and noncharging durations, including multiple pauses; invalid transitions are rejected.
6. Charger imports are idempotent and preserve separately managed operational fields.
7. Historical feature fixtures cover inclusion at the 30-day lower boundary, exclusion at arrival-day midnight, zero history, another charger, another port on the same charger and future completions. Include a year boundary and a leap-day example.
8. The warning comparison is strict: exactly 0.17 is not a warning. Exactly 30 observed noncharging minutes is not a positive outcome.
9. With the actual trusted bundle and recorded environment present, backend probabilities match direct pipeline calls using independently calculated historical features to absolute tolerance `1e-12`. Use representative supported dates, including a no-history case if the history contains one. Do not claim actual-bundle integration passed when only synthetic fixtures ran.
10. Browser-check two separate users: join queue, end another user's participating session, receive/accept an offer, exchange a manager message, refresh and verify persistence. Check desktop and mobile layouts and unauthorised direct URLs.
11. A driver or manager cannot access researcher routes or detailed model/evaluation responses. Ordinary driver screens show no research form or dataset charts; the driver assistant DTO contains only its approved minimal fields. Research access does not grant private conversation access.
12. An expired/retracted departure report disappears and never becomes an automatic session completion. A reminder triggers once, can be cancelled/snoozed, and is cancelled on unplug or an obsolete finished-charging state. Closed-browser notification records persist without claiming external push delivery.
13. Alternative suggestions explain their rule-based reason and never claim an ML waiting-time estimate. Private help reports are visible only to their reporter and assigned managers. Status freshness and failed-refresh states accurately reflect the underlying timestamps.

Run a production frontend build, relevant backend tests and migration checks. Correct observed failures. Record unavailable checks accurately if the environment lacks a browser, PostgreSQL or model artifact. Test fixtures are software-test data, never substitutes for model evaluation or real users.

## 16. Implement in working stages

### Stage 1 — Foundation and first complete journey

Inspect files, create the structure, configure dependencies/database/migrations, implement authentication and role checks, import the charger catalogue, and finish landing/auth/driver dashboard/charger list/details pages. Make a real driver able to register, sign in and browse database-backed charger records.

### Stage 2 — Coordination and manager tools

Implement session events/intervals, waiting lists, offers/expiry, notifications, manager assignments, the changing driver journey card and the manager dashboard. Add expected-departure reports, user-controlled return reminders and reliable queue handover. Verify queue/capacity correctness and reminder/report lifecycle with multiple users.

### Stage 3 — Communication and personal features

Implement persistent driver–manager messaging, read states and quick-message starters, favourites, profile/vehicle editing and app session history. Add charger help reports, rule-based alternatives and clear status freshness. Complete error/empty states, the simple driver dashboard and responsive navigation.

### Stage 4 — Research integration

Validate and load my exact saved bundle and implement the unchanged historical feature builder. Add the researcher-only prediction lab, evaluation views and historical charts. Integrate a minimal contextual driver assistant suggestion in an explicitly labelled historical demonstration, using the same fitted model and warning rule. Verify real artifact parity and role/data separation. Do not create, tune, refit or retrain any model.

### Stage 5 — Finish and document

Run the relevant checks, complete meaningful remaining user journeys, fix observed failures and produce the documentation below. Summarise implemented functionality, checks actually run, outstanding blockers and exact commands to start the app on Windows.

After each stage, give a short progress update and continue to the next authorised stage. Prefer a working vertical slice over many disconnected screens. Do not silently drop accounts, persistence, queue correctness, messaging, manager permissions or real model integration.

## 17. Required documentation and definition of done

Deliver:

- `README.md`: prerequisites, compatible Python/Node versions, setup, PostgreSQL configuration, migrations, catalogue import, explicit demo seeding, manager provisioning/assignment, frontend/backend start commands and troubleshooting.
- `.env.example`, frontend lockfile, backend dependency lock/pins and database migrations.
- `docs/REQUIREMENTS.md`: roles, main use cases, implemented scope and acceptance criteria.
- `docs/ARCHITECTURE.md`: components, frontend/backend boundaries, permissions and a small accurate architecture diagram.
- `docs/DATA_DICTIONARY.md`: operational tables and separation from historical data; queue/session lifecycle diagrams where useful.
- `docs/MODEL_CARD.md`: target, features, time split, historical history protocol, package/artifact requirements, recorded metrics, limitations and requirements for a future prospective deployment.
- `docs/DEMO_SCRIPT.md`: a short presentation walkthrough using two driver accounts, one assigned manager and a separately provisioned researcher. Cover the changing driver card, waiting list, departure report, reminders, messages/help reports and minimal historical assistant suggestion; show technical results only after signing in to the research workspace.
- `docs/VERIFICATION.md`: checks actually performed, their results and any checks blocked by missing resources.

Done means I can start the website locally, register/sign in, browse imported chargers, save a favourite, participate in a correctly managed app queue, report a charging session and optional expected departure, set a return reminder, compare rule-based alternatives, submit a help report, exchange an authorised manager message, receive persistent notifications, use manager tools and demonstrate a genuine historical prediction through my unchanged saved pipeline. The driver dashboard answers what is happening and what to do next without showing model internals. Technical research details require researcher access. Refreshing preserves database-backed records, and the interface clearly distinguishes app reports, self-reported departure expectations, demonstration activity and historical research. No new model is part of the delivery.

Start now by inspecting this workspace and implementing Stage 1. Keep progressing through the stages rather than returning only recommendations.

---

## Official technical references for implementation

Consult current primary documentation when implementing rather than copying outdated setup commands:

- React/Vite with TypeScript: https://react.dev/learn/build-a-react-app-from-scratch
- FastAPI: https://fastapi.tiangolo.com/
- scikit-learn model persistence and environment compatibility: https://scikit-learn.org/stable/model_persistence.html
- PostgreSQL transaction locking: https://www.postgresql.org/docs/current/explicit-locking.html

