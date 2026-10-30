# Elqovanta EV on Render and Neon

Use the private GitHub repository, one Render **Free Docker web service**, and one Neon Free PostgreSQL database. The web service serves the React build, API and original model from one HTTPS origin. No model is created or retrained. The source bundle is 29,604,322 bytes; its SHA-256 remains `b1cfde621dd23950b18c73cddf7bee97072f334e8e1355920abeb85318cac626`.

## Live deployment - 30 October 2026

- Website: **https://elqovanta-ev.onrender.com**
- Private source: **https://github.com/Mafuleka-Khethelo/elqovanta-ev**
- Validated application revision: **`df949f454e0f9a70e5c2862aaed2d012711c4461`**, adding the Charging Assistant, consent-based pre-target reminders, limited-time planning, per-port-power comparisons, session summaries and the labelled historical assistant illustration. Later documentation-only changes do not require redeploying this version. Automatic deployment is off.
- Render: one **Free** Docker service in **Frankfurt**, serving both the website and API. Neon: **Free PostgreSQL 16**, also in Frankfurt. No paid plan was selected.
- The existing **16 accounts, 50 chargers and operational activity** were copied to Neon with IDs and password hashes preserved. Existing credentials work on the live website. Old login sessions were excluded, so users sign in again. The local source database remains available as a separate backup; subsequent cloud changes do not synchronize back to it.

The exact Linux image passed **101 backend tests**, **144 independent saved-model comparisons**, and a memory probe under a hard **512 MiB** container limit. Observed peak was **422.1 MiB**, including API imports, the original bundle, predictions and competing password checks. Password hashing and verification share a one-at-a-time guard to bound memory; the existing Argon2 settings are unchanged. This measured workload supports the student demo, without establishing capacity for arbitrary traffic. See the [successful Linux checks](https://github.com/Mafuleka-Khethelo/elqovanta-ev/actions/runs/41025003852).

The current update applied additive migrations through `20261030_0006` to the same database. Real local journeys verified reported port power, limited-time planning/comparisons, explicit reminder consent and rescheduling, actual private/anonymous worker notices, history and unplug-to-offer handover; temporary QA activity was removed afterward. Live HTTPS checks confirmed new calculator/reminder/comparison schema, role logins, anonymous summaries and the unchanged model. Live browsers verified the driver assistant, time-budget preview and actual labelled historical model illustration at all four checked widths. A temporary live vehicle was removed and the original selection restored; existing charging/queue/reminder activity stayed intact. Read [Charging Assistant](CHARGING_ASSISTANT.md) for assumptions, privacy, historical illustration and free-host delivery limits.

Real HTTPS checks passed for transferred logins, public driver signup, automatic and planned advisories, charging transitions, FIFO handover, reminders delivered by the deployed worker, favourites, private messages/help reports, history and role restrictions. Temporary QA drivers, their charger and linked records were removed afterward; all 16 original accounts were preserved. Browser checks also passed at 320, 390, 768 and 1440 px, with one session advisory through repeated timer/poll updates and no JavaScript exceptions. Details are in [Verification](VERIFICATION.md).

## Deployment order

1. Create a Neon project in the same region as the service (Frankfurt where available). Keep its TLS connection string secret. Settings accept Neon's `postgresql://` URL and select the installed psycopg 3 driver without changing SSL parameters.
2. Before starting Render, copy the existing local accounts and activity into the **empty** Neon database with `backend/.venv/Scripts/python.exe scripts/migrate_to_neon.py`. Enter the Neon URL at the hidden prompt. This upgrades the target schema and copies operational records in one transaction, preserving IDs and password hashes. It refuses a destination containing app records, never changes the source, and excludes existing login sessions and login-attempt logs. Existing users sign in again. No database export or connection string belongs in Git.
3. Create a Render service from `render.yaml` using the private repository. The blueprint explicitly selects **free**, Docker, Frankfurt and `/api/v1/ready`. Set the secret `DATABASE_URL` to the Neon connection string. No Render database or paid resource is requested. Automatic deployment is off to keep the presentation version stable.
4. Docker builds React and installs the existing locked dependencies using **Python 3.13.9**. One Uvicorn worker loads the original bundle once. Thread counts are bounded through environment variables, without modifying the classifier or its parameters. The original artifact checksum is checked during image build.
5. Cloud startup applies additive Alembic migrations to the already-provisioned database. It imports the historical catalogue only if none exists, preserving transferred accounts, charger IDs, statuses, assignments and activity. Existing demo seeds are never run automatically in production.
6. `/api/v1/ready` must return HTTP 200 with database OK and prediction ready. Test login, supported current/planned advisories, queue, session, manager and Model lab access. `scripts/check_deployment.py HTTPS_URL --email DRIVER_EMAIL` performs a read-only smoke test after login, with a hidden password prompt and logout afterward.

## Configuration and limits

`Dockerfile` enables `SERVE_FRONTEND=true` and `INITIALIZE_DATABASE=true`, with the original artifact/manifest under `/app`. The blueprint sets `ENVIRONMENT=production`, `COOKIE_SECURE=true`, same-origin CORS only, and a small database pool. Credentials are runtime variables; `.env`, local data, test account guides, browser profiles, backups and database files are excluded from Git/build context. Frontend route refreshes work; missing API routes/assets and private file paths remain 404.

The GitHub workflow builds the exact Linux container, runs backend checks and original-model parity, and probes under a **512 MiB** hard container limit. The successful probe described above measures process memory in the tested workload; it is not a reading of Render's service-wide memory chart. Recheck memory if dependencies, concurrency, model artifacts or worker count change.

Render Free sleeps after 15 minutes with no inbound traffic. Cold starts may delay the first page and in-app reminders; saved reminder times survive, and the existing worker processes overdue records when awake. No on-time reminder guarantee or external push/email/SMS is claimed. Open the app and verify readiness before the presentation. Keep the existing local app available as a backup. Do not upgrade to a paid plan without the owner's choice.

## Presentation readiness

For the planned presentation on **30 October 2026 (Africa/Johannesburg)**, rehearse with separate driver, manager and researcher browser sessions. Demonstrate planned arrival, a genuine warning example, Continue/Go back, reported charging, queue handover, optional return reminder and private manager messaging. Use the separate Model lab for 2020 comparisons and evaluation; current/future advisories remain visibly experimental. Follow [Presentation notes](PRESENTATION_NOTES.md) and [the full walkthrough](DEMO_SCRIPT.md). The local backup currently serves the website and API at **http://127.0.0.1:8000** while its PostgreSQL/backend processes are running.

Official references: [Render Docker](https://render.com/docs/docker), [Blueprint fields](https://render.com/docs/blueprint-spec), [free-service limits](https://render.com/docs/free), [Neon connections](https://neon.com/docs/connect/connect-from-any-app).
