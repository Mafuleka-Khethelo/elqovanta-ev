# Elqovanta EV

**Live website: [elqovanta-ev.onrender.com](https://elqovanta-ev.onrender.com)**. Render serves the website, Python API and unchanged saved model; Neon stores accounts and activity. All 16 existing accounts were preserved. See [presentation notes for 30 October 2026](docs/PRESENTATION_NOTES.md).

For the one-address Render + Neon setup and presentation checks, see [Deployment](docs/DEPLOYMENT.md). Cloud deployment keeps the exact saved model and existing accounts; secrets and database files stay outside the private source repository.

For the 10 practice driver accounts with one shared password, see [Driver accounts](docs/ACCOUNT_SCENARIOS.md). Their private local login guide replaces the previous 28-person walkthrough. Existing activity was retained when moving to Neon.

Elqovanta EV helps participating drivers find charging locations, coordinate an app waiting list, report charging sessions, plan their return, and contact assigned station managers. Operational records persist in PostgreSQL. Charger status is **App-reported status**, not hardware telemetry or proof that a physical bay is vacant.

The original saved Random Forest is a supporting historical experiment. A separately provisioned **Examiner / Researcher** account owns the Historical Prediction Lab, evaluation, historical charts and demonstration configuration. Managers have station-operation tools only. Ordinary drivers see charging, queues, reminders, messages, help reports and clear next actions.

## What is implemented

- Driver registration, cookie sign-in/out, profile, optional vehicles, password change, favourites and paginated personal history.
- Charger search/map/list, observed port types, reported status source/time, and honest map/location fallbacks.
- Driver-reported pause/resume/finish/unplug events and timestamp-derived durations.
- FIFO waiting lists, ten-minute coordination offers, transactional acceptance and handover, expiry jobs and private in-app notifications.
- Anonymous, voluntary expected-departure reports; they expire and never release an app slot by themselves.
- User-chosen return reminders, cancellation and snoozing. The backend creates a persistent notification when due, including while the browser is closed.
- Deterministic alternative-charger comparisons and explicitly confirmed, atomic queue switching.
- Persistent private help reports, assigned-manager acknowledgement/resolution and private updates to the reporter.
- Driver–assigned-manager conversations, editable message starters, request identifiers, unread state and honest send errors.
- Automatic experimental driver advisories from the unchanged model, plus a separate Model lab for historical comparisons.

There are no payments, penalties, charger hardware, battery telemetry, SMS, email or external push integrations. Nothing predicts waiting minutes, departure times or a physical bay's vacancy. Application records never enter the frozen historical evaluation.

## Prerequisites

- Windows PowerShell, Node.js 20+ (checked with Node 24), PostgreSQL 16 or the supplied Docker Compose service.
- **Python 3.13.9**, matching `model_environment.json`.
- Original root files `ev_charger_bundle.joblib` and `model_environment.json`. Keep the original notebook and dataset in place.

The recorded numerical packages are scikit-learn 1.7.2, pandas 2.3.3, numpy 2.3.5, scipy 1.16.3, joblib 1.5.2 and threadpoolctl 3.5.0. Use the existing pinned dependency files; do not upgrade them to silence a warning. The server copies missing trusted artifacts into ignored `backend/artifacts/`, validates the contract and loads once per process. It never creates, fits, calibrates or replaces a model.

## First-time setup

From the project root:

```powershell
Copy-Item .env.example .env
py -3.13 -m venv backend\.venv
backend\.venv\Scripts\python -m pip install -r backend\requirements.txt
Set-Location frontend
npm ci
Set-Location ..
```

Edit `.env`: set `DATABASE_URL` for your PostgreSQL server. Set an operator-chosen `DEMO_PASSWORD` of 10–128 characters before using the optional demo seed. Do not commit `.env`.

For Docker PostgreSQL:

```powershell
docker compose up -d postgres
```

The local default database/user is `chargeconnect`; these retained internal identifiers keep existing data working and do not change the product name. The database volume is persistent. An existing PostgreSQL installation can be used through `DATABASE_URL`. `scripts/start-postgres.ps1` supports the supplied local tooling where a complete installation is available.

Apply migrations and import the historical catalogue **from the backend directory**:

```powershell
Set-Location backend
.venv\Scripts\python -m app.cli init-db
.venv\Scripts\python -m app.cli import-catalogue
Set-Location ..
```

`init-db` creates the configured database if needed and runs Alembic. The import is idempotent and preserves manager-maintained status, capacity and display names. Historical port labels do not establish physical connector counts. Historical imports start with app coordination disabled until configured.

## Provisioning roles

Public registration always creates a driver. A profile or signup field cannot grant privileged access. Run local operator commands from `backend`:

```powershell
Set-Location backend
$env:MANAGER_PASSWORD = "replace-with-your-own-local-passphrase"
.venv\Scripts\python -m app.cli create-manager --email manager@example.com --name "Alex Manager"
.venv\Scripts\python -m app.cli list-chargers
.venv\Scripts\python -m app.cli assign-charger --email manager@example.com --station-key "EXACT HISTORICAL NAME"
.venv\Scripts\python -m app.cli configure-charger --station-key "EXACT HISTORICAL NAME" --capacity 1 --status available
$env:RESEARCHER_PASSWORD = "replace-with-another-local-passphrase"
.venv\Scripts\python -m app.cli create-researcher --email examiner@example.com --name "Project Examiner"
Set-Location ..
```

Use separate manager and examiner accounts. Research access alone grants no private-message or operational access. `create-researcher` refuses to convert an existing account silently. Exact historical keys, including suffixes such as `#2`, are required for model inputs.

For a labelled development demonstration:

```powershell
Set-Location backend
.venv\Scripts\python -m app.cli seed-demo
Set-Location ..
```

The four demo accounts share the operator's `DEMO_PASSWORD`:

- `demo.driver1@chargeconnect.local`
- `demo.driver2@chargeconnect.local`
- `demo.manager@chargeconnect.local`
- `demo.researcher@elqovanta.local`

Existing demo email identifiers remain valid. Seed only runs outside production, labels its accounts and enables the Hamilton #2 sample when it has not already been configured. Existing assignments/configuration are retained. Sample app capacity is a demonstration assumption, not verified hardware capacity.

## Run locally

Use two terminals, each starting in the project root.

Backend:

```powershell
backend\.venv\Scripts\python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

Frontend:

```powershell
Set-Location frontend
npm run dev
```

Open http://localhost:5173 . Vite proxies `/api` to the local backend. API documentation is at http://127.0.0.1:8000/docs and is not linked from driver navigation. No external deployment is part of this build.

## Driver advisory and Model lab

Sign in as the examiner and open **Historical Prediction Lab**. Select an exact supported charger/port and a 2020 local arrival date/time. The results come from the original fitted pipeline; repeated identical inputs should reproduce the same result. The seven features, 30-day completion-based history, strict greater-than-30-minute outcome and strict probability-greater-than-0.17 warning rule are unchanged.

Drivers need no examiner selection. The prominent **When will you arrive?** card checks **Now** automatically after choosing a supported charger/port. **Later** accepts a station-local date/time within seven days; **Check arrival** displays its experimental preview. Planning creates no reservation or participation. Starting/accepting rechecks the actual current arrival and offers **Continue anyway / Go back** if flagged. The card visibly labels experimental accuracy and unavailable states; manual coordination remains available. A session uses its saved port and actual plugged-in time. See [Driver advisory](docs/DRIVER_ADVISORY.md).

Current-day warnings are experimental extrapolations from a model evaluated on 2020, not validated live forecasts. The unchanged previous-30-day frozen-history protocol normally produces zero sessions and a missing rate for today's dates. No current app records are added to model history, and dates are never silently mapped to 2020. See [Automatic driver advisory](docs/DRIVER_ADVISORY.md) for the policy, exact inputs, caching and limitations. The Model lab remains independent and 2020-only for illustration.

## Checks

```powershell
Set-Location backend
.venv\Scripts\python -m pytest -q -p no:cacheprovider
.venv\Scripts\python -m alembic current
.venv\Scripts\python -m alembic check
Set-Location ..
backend\.venv\Scripts\python scripts\check_model.py
Set-Location frontend
npm test
npm run build
Set-Location ..
```

PostgreSQL tests use the separate `chargeconnect_test` database and reset test tables there. Never point tests at a real application database. Actual-artifact parity requires the trusted bundle and recorded environment; fixture tests do not replace that check. See `docs/VERIFICATION.md` for checks actually run.

## Troubleshooting and limits

- Start PostgreSQL before migrations or sign-in. Check `/api/v1/health` for database and prediction readiness.
- If model readiness fails, check the original files and recorded package/Python versions. Accounts, coordination, manually chosen reminders and communication remain independent of inference.
- Local HTTP requires `COOKIE_SECURE=false`; HTTPS deployment would require secure-cookie configuration.
- A form-token error means refresh the page and retry. Mutations use the CSRF cookie/header pair.
- Failed refreshes show stale information and disable consequential controls until updates recover. Report timestamps identify the last participant report, separately from the last successful app refresh.
- The API must be running for its reminder/offer worker. Due reminder records survive restart and are processed afterward. An in-app notification is not OS push, email or SMS.
- Managers select or update the charger timezone; manual records default to UTC. Historical Palo Alto chargers start with America/Los_Angeles. Chosen departure inputs identify device time; reports are displayed in charger time.

See `docs/REQUIREMENTS.md`, `docs/ARCHITECTURE.md`, `docs/DATA_DICTIONARY.md`, `docs/MODEL_CARD.md` and `docs/DEMO_SCRIPT.md` for the implementation and presentation guide.
