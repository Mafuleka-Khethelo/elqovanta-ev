# Elqovanta EV on Render and Neon

Use the private GitHub repository, one Render **Free Docker web service**, and one Neon Free PostgreSQL database. The web service serves the React build, API and original model from one HTTPS origin. No model is created or retrained. The source bundle is 29,604,322 bytes; its SHA-256 remains `b1cfde621dd23950b18c73cddf7bee97072f334e8e1355920abeb85318cac626`.

## Deployment order

1. Create a Neon project in the same region as the service (Frankfurt where available). Keep its TLS connection string secret. Settings accept Neon's `postgresql://` URL and select the installed psycopg 3 driver without changing SSL parameters.
2. Before starting Render, copy the existing local accounts and activity into the **empty** Neon database with `backend/.venv/Scripts/python.exe scripts/migrate_to_neon.py`. Enter the Neon URL at the hidden prompt. This upgrades the target schema and copies operational records in one transaction, preserving IDs and password hashes. It refuses a destination containing app records, never changes the source, and excludes existing login sessions and login-attempt logs. Existing users sign in again. No database export or connection string belongs in Git.
3. Create a Render service from `render.yaml` using the private repository. The blueprint explicitly selects **free**, Docker, Frankfurt and `/api/v1/ready`. Set the secret `DATABASE_URL` to the Neon connection string. No Render database or paid resource is requested. Automatic deployment is off to keep the presentation version stable.
4. Docker builds React and installs the existing locked dependencies using **Python 3.13.9**. One Uvicorn worker loads the original bundle once. Thread counts are bounded through environment variables, without modifying the classifier or its parameters. The original artifact checksum is checked during image build.
5. Cloud startup applies additive Alembic migrations to the already-provisioned database. It imports the historical catalogue only if none exists, preserving transferred accounts, charger IDs, statuses, assignments and activity. Existing demo seeds are never run automatically in production.
6. `/api/v1/ready` must return HTTP 200 with database OK and prediction ready. Test login, supported current/planned advisories, queue, session, manager and Model lab access. `scripts/check_deployment.py HTTPS_URL --email DRIVER_EMAIL` performs a read-only smoke test after login, with a hidden password prompt and logout afterward.

## Configuration and limits

`Dockerfile` enables `SERVE_FRONTEND=true` and `INITIALIZE_DATABASE=true`, with the original artifact/manifest under `/app`. The blueprint sets `ENVIRONMENT=production`, `COOKIE_SECURE=true`, same-origin CORS only, and a small database pool. Credentials are runtime variables; `.env`, local data, test account guides, browser profiles, backups and database files are excluded from Git/build context. Frontend route refreshes work; missing API routes/assets and private file paths remain 404.

The preliminary **Windows** probe peaked at about **410 MiB resident RAM** during two predictions and two password verifications. This does not establish Linux/Render memory safety. The GitHub workflow builds the exact Linux container, runs backend checks and original-model parity, and probes under a **512 MiB** hard container limit when workflow permissions are available. A real Render smoke test and service memory/log inspection are still required; successful build alone is not deployment verification.

Render Free sleeps after 15 minutes with no inbound traffic. Cold starts may delay the first page and in-app reminders; saved reminder times survive, and the existing worker processes overdue records when awake. No on-time reminder guarantee or external push/email/SMS is claimed. Open the app and verify readiness before the presentation. Keep the existing local app available as a backup. Do not upgrade to a paid plan without the owner's choice.

## Presentation readiness

For the planned presentation on **30 October 2026 (Africa/Johannesburg)**, rehearse with separate driver, manager and researcher browser sessions. Demonstrate planned arrival, a genuine warning example, Continue/Go back, reported charging, queue handover, optional return reminder and private manager messaging. Use the separate Model lab for 2020 comparisons and evaluation; current/future advisories remain visibly experimental. Follow `DEMO_SCRIPT.md` and retain a local backup if the free service is waking or unavailable.

Official references: [Render Docker](https://render.com/docs/docker), [Blueprint fields](https://render.com/docs/blueprint-spec), [free-service limits](https://render.com/docs/free), [Neon connections](https://neon.com/docs/connect/connect-from-any-app).
