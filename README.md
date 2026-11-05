# SkillSync — Setup and Verification

This is the main setup and verification guide for this local integrated-testing checkout. These commands are not production deployment instructions.

## Architecture

| Workspace folder | Purpose |
| --- | --- |
| `skill-sync/frontend` | Laravel/Filament/Livewire website and local session identities |
| `skill-sync/backend` | FastAPI business API and PostgreSQL business records |
| `skillsync-ai-model` | Classification, reliability predictions and scoring API |
| `scripts` | Setup, startup and integration verification utilities |
| `.integration-runtime` | Generated logs and checkout-specific Laravel cache paths |

Laravel calls the business API server-side. Backend access tokens are not exposed to the browser. AI performs inference without database credentials.

Specialized references: [model training](skillsync-ai-model/MODEL_TRAINING_STEPS.md) and [API contract](skill-sync/frontend/docs/api-contract.md). Developer instructions such as AGENTS.md remain separate.

## Start the application

Start PostgreSQL, then run from the workspace root:

```powershell
Set-Location 'C:\Users\User\Desktop\test'
powershell -NoProfile -ExecutionPolicy Bypass -File .\start-skillsync.ps1
```

Keep the terminal open; Ctrl+C stops the services started by the launcher. It refuses occupied ports without stopping unrelated processes. Add `-Check` to validate setup without starting services, or `-SmokeTest` to start, check readiness and stop.

| Service | URL |
| --- | --- |
| Website | http://127.0.0.1:8100 |
| Business API docs | http://127.0.0.1:8101/docs |
| Business readiness | http://127.0.0.1:8101/health/ready |
| AI docs | http://127.0.0.1:8102/docs |
| AI readiness | http://127.0.0.1:8102/health |

If PHP is not on PATH, set `$env:PHP_BINARY = 'C:\php\php.exe'` before using the launcher. Routine startup does not require reseeding, resetting data or training models.

## First setup on another computer

### Install the required software first

These instructions are for a Windows 10/11 x64 laptop. Use a normal PowerShell window for project commands; Windows installers may request administrator permission. A browser and internet connection are needed to download dependencies. VS Code is optional.

Install the following in order:

| Software | Installation steps | Purpose |
| --- | --- | --- |
| Git | Download and run [Git for Windows](https://git-scm.com/install/windows). Enable command-line access when the installer asks about PATH. | Clone the repository |
| Node.js 24.x and npm | Select version 24.x and the Windows x64 MSI on the [Node.js download page](https://nodejs.org/en/download). Keep npm and PATH options enabled. | Build frontend CSS and JavaScript |
| PHP 8.4 | Follow the PHP steps below before installing Composer. | Run Laravel and Filament |
| Composer 2 | Run the Windows installer from [Composer's installation guide](https://getcomposer.org/doc/00-intro.md#installation-windows). Select your PHP executable, for example `C:\php\php.exe`. | Install PHP packages |
| PostgreSQL | Use the installer linked from [PostgreSQL for Windows](https://www.postgresql.org/download/windows/). Install the server and command-line tools; pgAdmin is optional. Keep port 5432, record the password for the `postgres` administrator, and finish installation. Stack Builder add-ons are not required. | Store application data |
| uv and Python 3.12 | Follow the commands below. uv can install Python, so a separate Python installer is unnecessary for this route. | Install and run backend/AI packages |

#### Configure PHP

Use the [official PHP Windows installation instructions](https://www.php.net/manual/en/install.windows.manual.php). Download the PHP 8.4 x64 Non Thread Safe ZIP linked there, extract it to `C:\php`, and install the matching Microsoft Visual C++ runtime required by that build if prompted.

Copy `php.ini-development` to `php.ini` in that folder. Open `php.ini` in a text editor, set `extension_dir = "ext"`, and enable these existing lines by removing their leading semicolon:

```ini
extension=curl
extension=fileinfo
extension=intl
extension=mbstring
extension=openssl
extension=pdo_sqlite
extension=sqlite3
extension=zip
```

Do not add duplicate settings. The standard PHP build also provides extensions such as DOM, XML and PDO; Composer checks the project's platform requirements during installation.

Add `C:\php` to your **user Path**: search Windows for “Edit environment variables for your account” → select Path → Edit → New → enter `C:\php` → save. Close and reopen PowerShell (and VS Code if using its terminal).

#### Install uv and Python

Run the Windows command from the [official uv installation guide](https://docs.astral.sh/uv/getting-started/installation/):

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Close and reopen PowerShell so it can find uv. Then install Python using [uv's Python management](https://docs.astral.sh/uv/guides/install-python/):

```powershell
uv python install 3.12
uv python find 3.12
```

#### Verify before cloning

Run each command and confirm it displays a version or configuration information:

```powershell
git --version
node --version
npm.cmd --version
php --version
php --ini
php -m
composer --version
uv --version
uv python find 3.12
```

Use Node 24.x and PHP 8.4.x for these instructions. Check that `php --ini` loads the file you edited and `php -m` includes the required extensions. If a command is “not recognized”, reopen the terminal and check the installer's PATH configuration before proceeding.

Press Win+R, enter `services.msc`, and find the PostgreSQL service. Confirm its status is **Running**, or start it. The setup script below asks for the password you chose during installation and creates the application's database and restricted role; you do not need to create them manually.

### Clone from GitHub (Windows / PowerShell)

Install Git alongside the prerequisites below, then clone the whole workspace:

```powershell
git clone https://github.com/Vithurshan2002/Skill-sync-Project.git skillsync
Set-Location skillsync
$skillSyncRoot = (Get-Location).Path
```

The repository root must contain `skill-sync/`, `skillsync-ai-model/`, `scripts/` and `start-skillsync.ps1`. Publish the whole workspace rather than only the frontend.

The commands below use the original laptop's example path, `C:\Users\User\Desktop\test`. Replace that prefix with your actual clone location (the value of `$skillSyncRoot`) before running them. Start PostgreSQL before database setup and keep its administrator password available.

Git ignores local environment files, virtual environments, Composer/npm dependencies, databases and generated frontend assets. Setup, dependency installation, migrations and the asset build below recreate these. Existing accounts, bookings and reviews are not transferred by cloning.

Before publishing, include source code, migrations, environment examples, dependency lockfiles, `skillsync-ai-model/feature_contract.json`, and both saved model files: `skillsync-ai-model/models/nlp_svm.joblib` and `skillsync-ai-model/models/reliability_rf.joblib`. If model artifacts are distributed separately, provide download instructions and restore them to those paths before startup. Do not publish private environment files, credentials, logs or database backups.

### Install dependencies and provision storage

After completing the software installation above, run the following commands in the same terminal used for cloning. Preserve existing environment files and keep credentials private.

```powershell
Set-Location (Join-Path $skillSyncRoot 'skill-sync/backend')
uv sync --locked --python 3.12
Set-Location (Join-Path $skillSyncRoot 'skillsync-ai-model')
uv sync --locked --python 3.12
Set-Location (Join-Path $skillSyncRoot 'skill-sync/frontend')
composer install
npm.cmd ci
if (-not (Test-Path -LiteralPath '.env')) {
    Copy-Item -LiteralPath '.env.example' -Destination '.env'
}
Set-Location $skillSyncRoot
& '.\skill-sync\backend\.venv\Scripts\python.exe' .\scripts\setup_integration.py --admin-user postgres
```

The command above is for a newly provisioned installation. Setup prompts for PostgreSQL administrator credentials and configures the restricted role and database below. It refuses to replace existing storage when using `--admin-user`. It also updates the absolute SQLite path and manages the isolated Laravel application key. Do not regenerate an existing key.

If this checkout already has valid integration database credentials, reuse them instead of provisioning again:

```powershell
# From the workspace root, after moving or renaming this checkout.
& '.\skill-sync\backend\.venv\Scripts\python.exe' .\scripts\setup_integration.py
```

This checks the existing database identity, preserves its data and refreshes the frontend path. PostgreSQL must be running. If credentials are missing, restore the correct environment configuration; do not reset the database to bypass the setup refusal.

| Setting | Value |
| --- | --- |
| Business database | `skillsync_integration_test` |
| Restricted role | `skillsync_integration_app` |
| Default database server | localhost:5432 |
| Frontend SQLite | `frontend/database/integration-testing.sqlite` |
| Backend AI settings | `AI_ENABLED=true`, `AI_BASE_URL=http://127.0.0.1:8102` |
| Frontend API | `FASTAPI_BASE_URL=http://127.0.0.1:8101` |

Backend guards reject other database names. The original `skillsync` database is not used. Apply migrations and build assets:

```powershell
Set-Location (Join-Path $skillSyncRoot 'skill-sync/backend')
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m app.cli seed-categories
.\.venv\Scripts\python.exe -m app.cli create-admin
Set-Location (Join-Path $skillSyncRoot 'skill-sync/frontend')
php artisan config:clear
php artisan migrate --no-interaction
php artisan filament:assets
npm.cmd run build
```

Create-admin prompts for your own credentials; public registration cannot create administrators. Keep migrations for fresh installations and future upgrades. Preserve the AI artifacts `models/nlp_svm.joblib`, `models/reliability_rf.joblib` and feature contract. Restore missing artifacts rather than retraining merely to start the site.

### Check and launch the new installation

Return to your clone's root directory and run:

```powershell
Set-Location $skillSyncRoot
powershell -NoProfile -ExecutionPolicy Bypass -File .\start-skillsync.ps1 -Check
powershell -NoProfile -ExecutionPolicy Bypass -File .\start-skillsync.ps1
```

Open http://127.0.0.1:8100. Register customer and worker accounts and use your administrator account to approve a completed worker profile. On subsequent runs, start PostgreSQL and run the launcher; do not repeat initial database provisioning. If opening a new terminal, set `$skillSyncRoot` to your clone location again.

## Manual startup

After setup, keep PostgreSQL running and use three separate terminals:

```powershell
# Terminal 1: AI
Set-Location 'C:\Users\User\Desktop\test\skillsync-ai-model'
.\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8102
```

```powershell
# Terminal 2: business API
Set-Location 'C:\Users\User\Desktop\test\skill-sync\backend'
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8101
```

```powershell
# Terminal 3: frontend
Set-Location 'C:\Users\User\Desktop\test'
New-Item -ItemType Directory -Path '.integration-runtime' -Force | Out-Null
$env:APP_CONFIG_CACHE = Join-Path (Get-Location).Path '.integration-runtime\frontend-config.php'
$env:APP_ROUTES_CACHE = Join-Path (Get-Location).Path '.integration-runtime\frontend-routes.php'
Set-Location '.\skill-sync\frontend'
php artisan serve --host=127.0.0.1 --port=8100
```

The cache variables isolate Laravel cache paths; they do not start CSS or AI. Manual PHP commands need PHP on PATH or its full executable path.

Public HTML may render with only the frontend running. Authentication and business operations require the backend; predictions require AI. A visible homepage does not verify the whole application.

CSS needs no separate server after `npm.cmd run build`. During development, optionally run `npm.cmd run dev` in another terminal and keep it running for live assets.

## Verify the complete flow

Use separate browser sessions for customer, worker and administrator.

1. Check public pages, directory filters, navigation and desktop/mobile layouts.
2. Register a worker and complete biography, categories, service towns, experience, positive rate and availability. Check starting coordinates and service radius where applicable.
3. As administrator, open Manage records → Workers → Details → Change requests. Approve the completed application or request changes with a note. Only approved workers should appear publicly and qualify for new bookings.
4. Register a customer. Check profile details and field-level validation.
5. Create a request with job description, location and preferred time. Choose a category or use classification where offered.
6. Select Find suitable workers; check category, coverage, availability and rate filters. Empty results are valid when no worker qualifies.
7. Request a booking and inspect quoted rate and schedule. Enter appointment time and expected end time. The completion deadline defaults to the expected end; select **Set a different deadline** only when needed. The API receives all three values: end must follow start and deadline must be at or after end.
8. As worker, accept, start and request completion confirmation. Check notifications and both users' booking views.
9. As customer, confirm completion and submit one review. Verify the correct worker profile, rating and completed-job count.
10. Check declines, cancellation reasons, correction requests and overlap rejection, including pending reservations.
11. Verify ownership and role restrictions, expired sessions, logout, invalid input, refresh, empty states and service failures.

## Business rules and predictions

- Lifecycle: `pending → accepted → in_progress → awaiting_confirmation → completed`. Customer confirmation finalizes completion.
- Booking rates are snapshots, not final invoices. Backend timestamps use UTC; the website displays Asia/Colombo time.
- Changes to worker identity, skills, experience or coverage can require reapproval. Contact, rate and availability changes follow separate update rules.
- With both coordinates available, coverage uses straight-line Haversine distance and worker radius; otherwise town matching applies. Multiple service towns describe coverage, not multiple map starting points. Distance is not driving distance, ETA or live tracking.
- Maps retain OpenStreetMap attribution. Explicit address searches use caching and rate limiting; `GEOCODING_SEARCH_URL` configures the provider. Multi-host deployments need shared rate-limit coordination. Private coordinates belong only in authorized views.
- Demo, test and real records have separate provenance. Do not relabel historical synthetic records as real outcomes. Demo seeding is optional, not routine startup.
- TF-IDF + Linear SVM classifies categories; Random Forest estimates on-time completion. Skill and match scores use weighted formulas, not separately trained models. DistilBERT is a separate training/comparison workflow.
- Missing reliability inputs use fitted training medians. Missing optional scoring components are excluded and remaining weights normalized. Estimates are not guarantees.
- Inference failures use labeled backend fallback where supported, with unavailable scores null. Audit snapshots preserve past classification/ranking provenance.
- Real-outcome exports use pre-outcome features and customer-confirmed results. Candidate training does not automatically replace active models; see the training guide.

AI endpoints include `/classify`, `/reliability`, `/recommend-score`, `/recommend` and `/smart-recommend`. Swagger documents payloads. Missing required artifacts cause unavailable-model responses.

For authorized business API testing, use login response `data.accessToken` in Swagger Authorize. Backend tokens are stored as digests; default expiry is eight hours without refresh tokens. Website tokens stay server-side.

Backend entry points: `app/main.py`, `routes.py`, `admin.py`, `auth.py`, `schemas.py`, `services.py`, `models.py`, `ai_client.py`. Frontend API boundaries: `SkillSyncGateway`, `FastApiSkillSyncGateway`, `BackendClient`.

Stable categories: Carpentry `cat03`, Electrical `cat04`, Plumbing `cat08`, Welding `cat10`. Administration edits descriptions/examples rather than changing model taxonomy.

## Automated verification

```powershell
# From skill-sync/backend
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
# Optional integrated browser suite, also from backend
$env:RUN_FRONTEND_BROWSER = '1'
$env:PHP_BINARY = 'C:/php/php.exe'
.\.venv\Scripts\python.exe -m pytest tests/test_frontend_browser.py -q -s -p no:cacheprovider
# From skill-sync/frontend
php vendor/phpunit/phpunit/phpunit tests/Feature/ApiIntegrationTest.php --no-progress
# From skillsync-ai-model
.\.venv\Scripts\python.exe -m unittest test_service -v
```

Backend tests use disposable schemas in the integration database. Browser tests use temporary SQLite storage and their own processes. Frontend integration tests use HTTP fakes. `test_nlp.py` is an interactive model utility, not the automated service suite.

## Troubleshooting and cleanup

| Problem | Check |
| --- | --- |
| Huge logo or missing styles | Run `npm.cmd run build`. If Vite is stopped but `public/hot` remains, remove that stale file and refresh. |
| PHP missing | Add installed PHP to PATH or set PHP_BINARY for the launcher. |
| Connection refused | Check PostgreSQL, ports, environment URLs and launcher logs. |
| Port occupied | Identify its owner or stop your own earlier server before restarting. |
| No workers match | Check approval, category, coverage, availability and rate filters. |
| AI unavailable | Check artifacts, dependencies, port 8102 and AI health. |
| Workspace moved | Check absolute SQLite path and environment settings; preserve existing data. |
| Frontend must use its isolated integration-testing.sqlite store | Check `DB_DATABASE` in `skill-sync/frontend/.env`. After a folder rename, run the existing-installation setup command above without `--admin-user`, then rerun launcher `-Check`. |
| Stale Laravel configuration | With intended environment/cache paths selected, run `php artisan config:clear` and `php artisan route:clear`, then restart. |

Keep source, migrations, lockfiles, environment configuration, active databases and saved model artifacts. Back up persistent data before storage changes. The launcher recreates `.integration-runtime` for logs/cache paths; that folder is not the business database.

## Logs, backups and deployment scope

- Launcher logs: `.integration-runtime/frontend.log`, `backend.log` and `ai.log`.
- Laravel logs: `skill-sync/frontend/storage/logs/`. Logs can contain account or request information; review them before sharing.
- Back up PostgreSQL business data, the frontend SQLite database, environment files (including the existing Laravel key), uploaded files and model artifacts. Stop writes or use database-supported backup tools for a consistent backup.
- Keep `composer.lock`, both `uv.lock` files and `package-lock.json` so installations use the recorded dependency versions.
- Local virtual environments may need recreation after moving the checkout; run `uv sync --locked` from each Python project. Do not copy a virtual environment between operating systems.
- These commands bind to localhost and use development servers. Production release additionally requires a deployment plan for HTTPS, secrets, process supervision, persistent storage, backups, monitoring and appropriate map-provider usage. The backend currently enforces the integration database name; deployment is not achieved just by changing its environment variable.

No default login credentials are documented. Create your own accounts and administrator. Optional demo data is not evidence of real completed work or model accuracy.
