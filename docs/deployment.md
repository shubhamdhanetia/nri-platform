# Deployment guide: Vercel, Render, and Neon

This guide explains the first deployment, how the three services connect, and
how to release future updates safely. It documents the deployment completed on
October 29, 2026. Provider interfaces and free-plan limits can change.

No Docker images, Kubernetes cluster, or virtual machine administration are
required for this setup.

## Contents

- [1. Understand the architecture](#1-understand-the-architecture)
- [2. Current deployment](#2-current-deployment)
- [3. Prerequisites and local checks](#3-prerequisites-and-local-checks)
- [4. Create the Neon database](#4-create-the-neon-database)
- [5. Apply the initial database migration](#5-apply-the-initial-database-migration)
- [6. Deploy FastAPI on Render](#6-deploy-fastapi-on-render)
- [7. Deploy Next.js on Vercel](#7-deploy-nextjs-on-vercel)
- [8. Authorize the website in Google OAuth](#8-authorize-the-website-in-google-oauth)
- [9. Verify the complete deployment](#9-verify-the-complete-deployment)
- [10. Deploy future changes](#10-deploy-future-changes)
- [11. Backups and recovery](#11-backups-and-recovery)
- [12. Troubleshooting](#12-troubleshooting)
- [13. Free-tier limitations and operations](#13-free-tier-limitations-and-operations)
- [14. Future GitHub Actions workflow](#14-future-github-actions-workflow)

## 1. Understand the architecture

```text
Browser
  |
  +--> Vercel: Next.js website
  |      Serves pages and frontend JavaScript
  |
  +--> Google: sign-in
  |
  +--> Render: FastAPI backend
           Verifies Google credentials, issues application JWTs,
           enforces authorization, and handles application requests
             |
             +--> Neon: PostgreSQL
             |      Stores users, posts, rides, bookings, and notifications
             |
             +--> External location provider
                    Resolves location searches and selected places
```

The browser calls Render directly using `NEXT_PUBLIC_API_URL`. Vercel does not
proxy those requests in the current configuration.

The frontend never receives a PostgreSQL connection string or the JWT signing
secret. Only the backend and authorized migration tooling need database access.

The local Docker Compose file starts a development PostgreSQL database. It is
not used to deploy Neon, Render, or Vercel.

### Database creation versus migrations

Creating a Neon project provisions PostgreSQL. It does not create this app's
tables. Alembic migrations create and subsequently update those tables.

- SQLAlchemy models describe the application's expected database structure.
- A migration is a saved instruction for changing that structure.
- `alembic upgrade head` applies revisions not yet recorded in the database.
- The `alembic_version` table records the current revision.
- Backend startup no longer runs `create_all()` or modifies the schema.

The initial migration is long because it describes all existing tables,
constraints, and indexes, not because the first deployment changes the product.
No local user data is uploaded by running this migration.

## 2. Current deployment

| Component | Configuration |
| --- | --- |
| Repository | `shubhamdhanetia/nri-platform` |
| Initial deployed backend commit | `2c86d56` |
| Backend deployment branch | `fix/destination-map-and-migration-cleanup` |
| Website | <https://client-bay-alpha-95.vercel.app> |
| Vercel project | `nri6/client` |
| API origin | <https://nri-platform-api.onrender.com> |
| API documentation | <https://nri-platform-api.onrender.com/docs> |
| API health endpoint | <https://nri-platform-api.onrender.com/health> |
| Render service | `nri-platform-api`, Free, Virginia |
| Render dashboard | <https://dashboard.render.com/web/srv-dbhfkhh42hec73cbd0og> |
| Neon project | `nri-platform`, Free, AWS US East 1 (N. Virginia) |
| Neon branch / database | `production` / `nri_platform` |
| PostgreSQL version | 16 |
| Initial migration | `0001` |
| Neon dashboard | <https://console.neon.tech/app/projects/gentle-tooth-31242827/branches/br-autumn-bonus-b8s2gr3g> |
| Render auto-deploy | Off |
| Vercel deployment method | Manual CLI; Git auto-deployment was not configured |

These are the initial deployment settings, not requirements to keep this branch
forever. Moving production to `main` should be an explicit change after merging
and validating the deployment code.

### What was verified during deployment

- All 94 backend tests passed, including PostgreSQL-enabled tests.
- Neon's initial migration completed at `0001 (head)`.
- `alembic check` reported no new upgrade operations.
- Render returned HTTP 200 from `/health` and served the OpenAPI definition.
- CORS accepted the Vercel origin.
- An unauthenticated `/users/me` request returned HTTP 401.
- The user confirmed successful Google sign-in after updating authorized origins.

The health endpoint alone does not verify database access or the location
provider. Location discovery and booking flows need their own hosted checks.

## 3. Prerequisites and local checks

You need:

1. Access to the GitHub repository.
2. Vercel, Render, and Neon accounts.
3. A Google OAuth **Web application** client.
4. Git, npm, and a Next.js-compatible Node.js release (20.9 or newer).
5. Python 3.13; the initial backend deployment uses 3.13.4.
6. A local development PostgreSQL database for PostgreSQL-specific tests.

Examples use Windows PowerShell. Commands start from the repository root unless
the preceding instruction explicitly changes the working directory. Render's
start command runs in a Linux environment, not PowerShell.

### Install and test the backend

If the virtual environment already exists, do not recreate it unnecessarily.

```powershell
Set-Location C:\personal_projects\nri-platform\backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-test.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Backend API tests need local settings, including a development `DATABASE_URL`,
`JWT_SECRET`, and `GOOGLE_CLIENT_ID`. Do not use production settings for routine
development tests.

For PostgreSQL-specific migration and concurrency coverage, point the local
configuration at a development PostgreSQL database, then run:

```powershell
$env:MIGRATION_TEST_POSTGRES = "1"
$env:RIDE_TEST_POSTGRES = "1"
try {
    .\.venv\Scripts\python.exe -m unittest discover -s tests -v
    if ($LASTEXITCODE -ne 0) { throw "Backend tests failed." }
} finally {
    Remove-Item Env:MIGRATION_TEST_POSTGRES
    Remove-Item Env:RIDE_TEST_POSTGRES
}
```

The PostgreSQL tests create and clean up isolated test schemas. Do not run these
tests against the production database.

### Build the frontend

```powershell
Set-Location C:\personal_projects\nri-platform\client
npm ci
npm run build
```

Use the committed lockfile. A successful local build does not prove that hosted
environment variables, OAuth settings, or cross-origin requests are correct.

## 4. Create the Neon database

For the existing deployment, this is already done. Do not create another project
or reset the current database just to redeploy application code.

For a new environment:

1. Sign in at <https://console.neon.tech>.
2. Create a project, for example `nri-platform`.
3. Select the Free plan.
4. Select AWS US East 1 (N. Virginia), near Render's Virginia region.
5. Select PostgreSQL 16 to match the tested setup.
6. Name the database `nri_platform`.
7. Leave unrelated services, such as object storage, functions, and alternate
   authentication products, disabled unless separately needed.
8. Open **Connect** for the intended branch and database.
9. Keep TLS enabled. Retain the supplied `sslmode=require` and any other required
   connection parameters.

Record which branch and database belong to production. Neon database branches
and Git branches are different things; choosing a Git branch does not
automatically create or select a Neon branch.

### Two database connection URLs

| Connection | Use |
| --- | --- |
| Direct, connection pooling off | Alembic migrations and database administration |
| Pooled, connection pooling on | Render's application `DATABASE_URL` |

Retrieve each through Neon's connection dialog. Do not manually edit hostnames
to guess the other connection.

The app explicitly selects the installed Psycopg 2 driver for plain
`postgresql://` URLs. `postgresql+psycopg2://` is also supported. Preserve
URL-encoded passwords and the entire query string.

**Treat both URLs as passwords.** Do not commit them, paste them into issues,
include them in screenshots, or store them in any `NEXT_PUBLIC_*` variable.

## 5. Apply the initial database migration

For the existing Neon deployment, revision `0001` has already been applied.
Running `upgrade head` again is safe when no new revisions exist; it does not
recreate existing application tables.

### 5.1 Confirm the target

Before any database command, check in the Neon dashboard:

- The intended project and branch are selected.
- The database is `nri_platform`.
- A first-time baseline is targeting an empty application database.
- You are using the direct connection URL.

Never run the initial migration blindly on a database with older application
tables.

### 5.2 Set the URL without putting it into shell history

Run this in a dedicated PowerShell window. Paste the direct URL at the masked
prompt rather than writing it as a literal in a command.

```powershell
Set-Location C:\personal_projects\nri-platform\backend
$previousDatabaseUrl = $env:DATABASE_URL
$secureUrl = Read-Host "Paste the Neon direct database URL" -AsSecureString
$env:DATABASE_URL = [System.Net.NetworkCredential]::new("", $secureUrl).Password

try {
    .\.venv\Scripts\python.exe -m alembic upgrade head
    if ($LASTEXITCODE -ne 0) { throw "Migration failed; do not deploy." }

    .\.venv\Scripts\python.exe -m alembic current
    if ($LASTEXITCODE -ne 0) { throw "Revision verification failed." }

    .\.venv\Scripts\python.exe -m alembic check
    if ($LASTEXITCODE -ne 0) { throw "Schema verification failed." }
} finally {
    $env:DATABASE_URL = $previousDatabaseUrl
    $secureUrl.Dispose()
    Remove-Variable secureUrl
}
```

The process needs the plaintext URL internally to connect, but this avoids
printing it and putting it into command history. Do not enable verbose tracing
that prints environment variables.

For the initial release, expect:

```text
0001 (head)
No new upgrade operations detected.
```

Later releases will have a different head revision. `alembic check` compares
autogeneratable changes; it is not a complete audit of data, check constraints,
or every PostgreSQL object.

Migration commands need only `DATABASE_URL`; they do not need a Google client ID
or JWT secret. The shell variable overrides the local backend environment file.
Restoring it afterward prevents accidentally using production during local work.

### 5.3 Existing databases created with create_all

An existing local database may already have all the tables but no
`alembic_version` record. In that case, the initial upgrade will fail with a
table-already-exists error rather than silently adopting it.

- **Disposable local data:** create a new empty local database, point local
  configuration at it, and run `alembic upgrade head`.
- **Data to preserve:** back up first and verify tables, columns, constraints,
  defaults, and indexes against revision `0001`. Only then consider
  `alembic stamp 0001`.

`stamp` only records a revision. It does not create, repair, or verify tables.
Never use it to bypass a failed migration without understanding the mismatch.

## 6. Deploy FastAPI on Render

### 6.1 Publish the deployment code

Render builds from GitHub, not uncommitted local files.

1. Review the intended changes with `git diff`.
2. Run the tests.
3. Commit only the intended code and migration files.
4. Push to the deployment branch.
5. Verify the commit appears on GitHub.

Never commit local environment files or credentials. The initial deployment uses
`fix/destination-map-and-migration-cleanup`, not `main`.

### 6.2 Connect the repository

1. Sign in at <https://dashboard.render.com>.
2. Select **New > Web Service**.
3. Connect GitHub.
4. Authorize the Render GitHub app, preferably only for the required repository.
5. Select `shubhamdhanetia/nri-platform`.

If the page still says **Connect Git provider**, finish the GitHub authorization,
then reload the Render page.

### 6.3 Configure the service

| Setting | Initial deployment value |
| --- | --- |
| Name | `nri-platform-api` |
| Language/runtime | Python 3 |
| Branch | `fix/destination-map-and-migration-cleanup` |
| Region | Virginia (US East) |
| Root directory | `backend` |
| Build command | `pip install -r requirements.txt` |
| Start command | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| Instance type | Free |
| Health check path, under Advanced | `/health` |
| Auto-Deploy, under Advanced | Off |
| Pre-Deploy Command | Empty; unavailable on the selected free instance |

Render supplies `$PORT`. Do not hard-code localhost or use `--reload` in
production. The build runs inside `backend`, so the requirements path does not
need a `backend/` prefix.

### 6.4 Add environment variables

| Name | Value | Secret? |
| --- | --- | --- |
| `DATABASE_URL` | Neon pooled PostgreSQL URL with TLS | Yes |
| `JWT_SECRET` | New cryptographically random production secret | Yes |
| `GOOGLE_CLIENT_ID` | Google OAuth Web client ID | Public identifier |
| `PYTHON_VERSION` | `3.13.4` | No |
| `CORS_ORIGINS` | `["https://client-bay-alpha-95.vercel.app"]` | No |

The Google client ID must match the frontend's
`NEXT_PUBLIC_GOOGLE_CLIENT_ID`. Do not use the Google client secret in its place.
The current browser sign-in flow does not require storing a Google client secret
in the frontend or backend.

Generate the JWT secret with a password manager or a cryptographically secure
generator. Keep it separate from local development and stable across redeploys.
Changing it invalidates existing application tokens.

Enter variables directly in Render or use its **Add from .env** import. If you
create a temporary import file, keep it outside Git and securely delete the
specific file after import. Masked UI fields may still expose values through
browser inspection, so avoid sharing screenshots or diagnostic dumps.

`CORS_ORIGINS` must be a JSON array, not a comma-separated string. Origins have a
scheme and hostname, with an optional port, but no page path or trailing slash.
If you change the website domain, update this setting too.

### 6.5 Deploy and inspect logs

1. Select **Deploy web service**.
2. Check that the selected commit is the expected release.
3. Wait for dependency installation and the build to complete.
4. Confirm Uvicorn starts and Render marks the service live.
5. Open `/health`.

Expected response:

```json
{"status":"ok"}
```

Do not put migrations in the build command. Do not make each web worker run
migrations on startup. The initial migration was applied separately; future
releases also need an explicit migration step.

## 7. Deploy Next.js on Vercel

### 7.1 Project settings

For a new Vercel project:

1. Import the GitHub repository or deploy the client with the Vercel CLI.
2. Select Next.js as the framework.
3. Set the project root to `client`.
4. Keep Next.js's default output configuration; do not configure a static export.
5. Use the committed npm lockfile.
6. Use a Node.js release compatible with the project's Next.js version.

For the existing project, reuse `nri6/client`; do not accidentally create a second
project from the repository root.

### 7.2 Production environment variables

| Name | Value |
| --- | --- |
| `NEXT_PUBLIC_API_URL` | `https://nri-platform-api.onrender.com` |
| `NEXT_PUBLIC_GOOGLE_CLIENT_ID` | The same OAuth Web client ID as Render |

Set these for the **Production** environment.

Both values are intentionally public and included in browser JavaScript.
Database credentials and `JWT_SECRET` must never be placed here.

If `NEXT_PUBLIC_API_URL` is absent, the client falls back to
`http://localhost:8000`. For a visitor, that means the visitor's computer, not
your computer or Render.

Next.js includes these public values during the build. **Saving an environment
variable is not enough: redeploy the frontend afterward.**

### 7.3 Existing-project CLI deployment

The local `client\.vercel` directory links this checkout to the Vercel project
and is ignored by Git. On a new machine, run `vercel link` and select the existing
project rather than creating another one.

From the repository root:

```powershell
npx --yes vercel login
npx --yes vercel link --cwd client
npx --yes vercel deploy --prod --yes --cwd client
```

Check the selected account/project before accepting prompts. `--prod` publishes
the checkout's client files to the production domain; it is not restricted to
the Git `main` branch. Review local changes before running it.

### Preview deployments

Preview environment variables are separate from Production variables. A preview
URL is also a different origin for CORS and Google OAuth.

Do not automatically point every preview at production data or allow every
`*.vercel.app` origin. Use a deliberate preview environment and allowlist exact
origins if preview testing is needed.

## 8. Authorize the website in Google OAuth

1. Open Google Cloud Console and select the project owning the OAuth client.
2. Open **Google Auth Platform > Clients**, or **APIs & Services > Credentials**
   in the older interface.
3. Select the OAuth **Web application** client whose ID matches both deployments.
4. Under **Authorized JavaScript origins**, add:

   ```text
   https://client-bay-alpha-95.vercel.app
   ```

5. Keep `http://localhost:3000` if local development uses the same client.
6. Save and allow time for changes to propagate, then reload the website.

Do not add `/login` or a trailing slash. The Render API URL is not the website
origin for this browser-based sign-in.

The current flow sends a Google credential to FastAPI; it does not define a
backend OAuth callback route. Do not invent a redirect URI to resolve an
authorized-JavaScript-origin error.

If Google restricts the OAuth application to test users, ensure the intended
account is allowed. Do not share Google passwords or login tokens in deployment
logs or issue reports.

## 9. Verify the complete deployment

### 9.1 Public backend checks

```powershell
curl.exe -i --max-time 90 https://nri-platform-api.onrender.com/health
curl.exe -i --max-time 90 https://nri-platform-api.onrender.com/users/me
```

Expected:

- `GET /health`: HTTP 200 with `{"status":"ok"}`.
- `GET /users/me` without a token: HTTP 401, not a user profile.

Use GET for the health check. `curl.exe -I` sends HEAD, which the current
GET-only health route does not implement.

### 9.2 CORS preflight

```powershell
curl.exe -i --max-time 90 -X OPTIONS `
  https://nri-platform-api.onrender.com/users/me `
  -H "Origin: https://client-bay-alpha-95.vercel.app" `
  -H "Access-Control-Request-Method: GET" `
  -H "Access-Control-Request-Headers: authorization"
```

Expect HTTP 200 and:

```text
access-control-allow-origin: https://client-bay-alpha-95.vercel.app
```

CORS controls browser cross-origin access; it does not replace authentication.

### 9.3 Browser smoke test

1. Open the production website.
2. Sign in with Google.
3. Confirm the app reaches its authenticated pages.
4. Open your profile to verify an authenticated database-backed request.
5. Search for a location to verify the external provider from Render.
6. If needed, create clearly marked test content and remove it afterward.
7. Check the browser Network panel: application requests should go to
   `https://nri-platform-api.onrender.com`, not localhost.
8. Inspect Render logs for unexpected errors without copying sensitive data.

Successful sign-in is a useful database smoke test because the backend finds or
creates a user. It is not proof that every ride/carpool operation or external
provider works.

## 10. Deploy future changes

### 10.1 Frontend-only change

1. Review and test the client change.
2. Commit and push the intended release.
3. Deploy the Vercel project manually.
4. Verify the updated page and API calls.

No database migration is needed for a purely visual change.

### 10.2 Backend change without schema changes

1. Run relevant backend tests.
2. Commit and push to the configured Render branch.
3. In Render, choose **Manual Deploy > Deploy latest commit**.
4. Verify the release commit, health endpoint, and affected functionality.

Do not deploy the latest commit blindly if another person pushed unrelated work.
Use a specific release commit where the deployment interface supports it.

### 10.3 Change to database structure

Work on a local or isolated development database:

1. Make sure the development database is migrated to the current head.
2. Change the SQLAlchemy models.
3. Generate a revision:

   ```powershell
   Set-Location C:\personal_projects\nri-platform\backend
   .\.venv\Scripts\python.exe -m alembic revision --autogenerate -m "Describe the schema change"
   ```

4. Review the generated migration. Autogeneration is a starting point, not a
   guarantee. Renames, backfills, check constraints, enum changes, and destructive
   operations need particular attention.
5. Test upgrading a fresh database and an existing database with representative
   data. Test failure/recovery behavior when relevant.
6. Apply it locally and run `alembic check` and the relevant tests.
7. Commit the model change and migration together.

For the production release:

```text
Review and test the exact release
              |
Create and verify a recovery point
              |
Run pending migrations once against the Neon direct URL
              |
Verify revision and migration outcome
              |
Deploy the compatible backend commit to Render
              |
Verify backend functionality
              |
Deploy the matching frontend to Vercel, if needed
              |
Run end-to-end smoke tests
```

If migrations fail, stop the release and investigate. Do not automatically
continue deployment, stamp the database, or retry a destructive operation.

Running migrations before deploying means the old backend may still be running.
Keep changes backward-compatible:

- Add a new nullable column first.
- Deploy code that can use it.
- Backfill data in a controlled step if needed.
- Only remove old columns or enforce tighter constraints in a later release.

Do not edit an already-applied migration to make a new change. Add a new revision.
Do not run two production migration jobs concurrently; the current setup does
not implement a cross-process deployment lock.

### 10.4 Move production to main later

The initial backend branch is temporary. To switch:

1. Review and merge the deployment work into `main`.
2. Run checks on the merged commit.
3. Update Render's configured branch to `main`.
4. Keep auto-deploy off until the release workflow is ready.
5. Deploy and verify the chosen `main` commit.
6. If connecting Vercel to Git later, configure `main` as its production branch
   and coordinate that deployment with backend/migration releases.

Changing the deployment branch does not migrate or replace the Neon database.

## 11. Backups and recovery

The initial empty database did not contain user data to preserve. Once real
users sign in or publish content, treat it as persistent production data.

Before risky schema changes:

1. Check the actual recovery features and retention available on your Neon plan.
2. Create a recovery point or logical backup appropriate to that plan.
3. Keep backups private and encrypted; they can contain emails, phone numbers,
   ride addresses, and other personal data.
4. Test restoring to a separate database or branch.
5. Record the deployed application commit and Alembic revision.

Do not assume the Free plan includes indefinite backups or recovery guarantees.
Deleting a database or branch is not a deployment step.

### Application rollback

Redeploying an older application commit does **not** roll back the database.
Only roll back code if that version remains compatible with the current schema.

### Database recovery

Do not run `alembic downgrade base` on production as a routine rollback.
The initial migration's downgrade drops application tables and their data.

Prefer a reviewed forward fix when possible. For destructive data/schema
problems, restore into an isolated recovery database first, verify the result,
and plan the cutover. Restoring an older backup can lose writes made since that
backup, so it requires an explicit recovery decision.

If credentials are exposed, rotate them through the provider, update the affected
service settings, redeploy as needed, and revoke the old credentials. Never
include their values in the incident record.

## 12. Troubleshooting

| Symptom | Likely cause / next step |
| --- | --- |
| First API request is very slow | Render Free may be waking; allow time and inspect service status. Neon compute may also need to resume. |
| `/health` is 200 but database requests fail | Health checks only the process. Check `DATABASE_URL`, TLS, permissions, migration revision, and Render logs. |
| API root `/` returns 404 | No root route is defined. Use `/health` or `/docs`. |
| `HEAD /health` returns 405 | Use `GET /health`; HEAD is not defined for this route. |
| Requests go to localhost | Production `NEXT_PUBLIC_API_URL` was missing at build time or the client was not redeployed. |
| Browser reports CORS failure | Check the exact website origin in Render's JSON `CORS_ORIGINS`, redeploy, and run the OPTIONS check. Also inspect whether an underlying API error caused the symptom. |
| Google says origin not allowed | Add the exact Vercel origin to the correct OAuth Web client's Authorized JavaScript origins. |
| Google says client ID not found | Verify the actual Web client ID, ensure frontend/backend match, and rebuild the frontend. |
| Render reports missing settings | Add the required variables in Render; local environment files are not uploaded automatically. |
| `ModuleNotFoundError: psycopg` | Verify the deployment includes the explicit URL parsing helper and pinned Psycopg 2 dependency. Do not rely on an undeclared package installed locally. |
| `relation ... does not exist` | Migrations were not applied to the database/branch the app is using, or configuration points to the wrong database. |
| Initial migration says table already exists | Existing tables have no baseline record. Stop and follow the verified-baseline procedure; do not blindly stamp. |
| `alembic check` reports new operations | Models and migrated schema differ. Review and add the missing migration; the command does not apply changes. |
| Render deploys old code | Check the configured Git branch and deployed commit, and make sure changes were committed and pushed. |
| Render cannot find requirements or app | Set root directory to `backend` and use the documented build/start commands. |
| Location search returns 502 or 504 | Check provider errors in Render. The current external HTTP integration has no separately configured provider API key and hosted access is not guaranteed. |
| Old JWT stops working after deployment | Check whether the production JWT secret changed; sign in again after an intentional rotation. |
| Vercel preview cannot call API or sign in | Preview URL/environment differs from production. Configure a deliberate preview environment rather than broadly opening production CORS. |

## 13. Free-tier limitations and operations

- Render Free can sleep after inactivity, leading to noticeable cold starts.
- Neon Free has storage/compute limits and can suspend idle compute.
- Vercel Hobby is intended for personal, non-commercial use; confirm eligibility
  before using it for a commercial service.
- Provider subdomains avoid buying a custom domain. A custom domain itself is
  usually a separate cost.
- Monitor usage and current provider terms. Free service availability is not an
  uptime guarantee and does not mean unlimited usage.
- Keep secrets in provider environment settings, not source code.
- Use a separate database/environment for development and previews.
- CORS is an allowlist, not a protection against direct non-browser API calls.
- The current deployment is a starter architecture, not a production-hardening
  checklist completed in full. Reassess backups, monitoring, abuse controls,
  provider suitability, and access policies as real usage grows.

## 14. Future GitHub Actions workflow

The current deployment is manual. No migration-aware GitHub Actions release
workflow was added as part of this deployment.

A future workflow can implement:

```text
Push/merge to main
       |
Tests and frontend build
       |
Serialized production migration job
       |
Deploy Render and wait for the exact release to become healthy
       |
Deploy Vercel
       |
Smoke tests and deployment result
```

Required safeguards:

- A GitHub production environment and appropriate approval/branch controls.
- Secrets for the direct database URL and deployment credentials.
- One production release at a time; do not cancel a running migration mid-release.
- Explicit failure handling: no app deployment after a migration failure.
- Deployment pinned to the tested commit, not whatever branch head happens to be.
- Provider auto-deploy disabled or coordinated to avoid duplicate/out-of-order
  deployments.
- Backward-compatible migrations and a documented recovery process.

## Related files and official references

Repository:

- [Local setup and project overview](../README.md)
- [Feature and API documentation](./feature.md)
- [FastAPI entry point](../backend/app/main.py)
- [Backend settings](../backend/app/core/config.py)
- [Database connection setup](../backend/app/db/session.py)
- [PostgreSQL URL handling](../backend/app/db/url.py)
- [Alembic configuration](../backend/alembic.ini)
- [Migration environment](../backend/migrations/env.py)
- [Initial schema migration](../backend/migrations/versions/0001_initial_application_schema.py)
- [Migration tests](../backend/tests/test_migrations.py)
- [Deployment tests](../backend/tests/test_deployment.py)
- [Frontend API helper](../client/lib/api.ts)

Providers:

- [Render free services](https://render.com/docs/free)
- [Render deployments](https://render.com/docs/deploys)
- [Render health checks](https://render.com/docs/health-checks)
- [Neon connection documentation](https://neon.com/docs/connect/connect-from-any-app)
- [Neon plans](https://neon.com/docs/introduction/plans)
- [Vercel environment variables](https://vercel.com/docs/environment-variables)
- [Vercel Git integration](https://vercel.com/docs/git)
- [Vercel Hobby plan](https://vercel.com/docs/plans/hobby)
- [Alembic tutorial](https://alembic.sqlalchemy.org/en/latest/tutorial.html)
