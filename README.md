# NRI Platform

**Your people. Your place.**

A location-aware community web app for Non-Resident Indians (NRIs) to connect,
share local recommendations, discover housing and events, and arrange scheduled
community rides.

The project is an evolving MVP. The ride-sharing module's first working
baseline is **v0.1.0**; it is scheduled ride coordination, not an on-demand taxi
or dispatch service.

[Features](#features) | [Screenshots](#screenshots) |
[Technical overview](#technical-overview) | [Local setup](#local-setup) |
[Documentation](#documentation)

## Features

The main navigation has two sections: **Posts** for map-based community
discovery and **Rides** for scheduled trips. Posts is the destination after
sign-in and when selecting the brand. **Create a post** is available inside
Posts, including fullscreen map mode. Profile, saved posts, and logout are in
the account menu. The existing `/feed` route remains available as a secondary
view, but is no longer in the top navigation. Older screenshots below may show
the previous navigation labels.

### Community

- **Google sign-in** with backend credential verification and JWT-authenticated
  API access.
- **Community posts** for housing, rides, jobs, food, events, immigration,
  marketplace listings, and general discussions.
- **Offering, Looking for, and Discussion** post types.
- **Public or Only me visibility**, enforced by the backend.
- **Comments, likes/dislikes, and saved posts** to participate and revisit useful
  information.
- **Profile and post management**, including content editing within a
  30-minute window and visibility changes at any time.

### Location-based discovery

- Search a city or area using location autocomplete.
- Explore posts on a **Leaflet/OpenStreetMap map**, filtered by category and
  post type.
- Pan or zoom, then explicitly select **Search this area**.
- Clustered markers, linked result cards, and fullscreen mode with floating
  filters and collapsible results.
- Browser geolocation with a city-search fallback.

### Scheduled community rides

1. A rider requests a ride with exact pickup/drop-off locations, a pickup
   window, passenger/bag counts, and a private contact number.
2. A member completes a driver profile with vehicle details, seat capacity,
   contact number, and an eligibility acknowledgement.
3. Drivers discover open requests and propose a pickup time and cost-sharing
   contribution.
4. The rider compares offers and selects one driver.
5. Confirmation creates one booking atomically and shares contact numbers with
   the two participants.

Ride discovery supports pickup-map bounds, an optional departure date, and an
optional same-day time range. A date alone considers the whole day; a time
range matches overlapping pickup windows in each ride's saved timezone.
Members can track requests, offers, cancellations, and completion in **My rides**.

> **Privacy and scope:** exact ride addresses are visible to signed-in members
> with a completed driver profile after the rider's consent, even before a
> booking is confirmed. Phone numbers are shared only with booking participants
> after confirmation. Drivers and phone numbers are not verified or vetted.
> This version does not provide payments, chat, notifications, live tracking,
> or destination search filters. Use a public meeting point when appropriate.

## Screenshots

These are captures of the actual web UI. Authenticated screens use synthetic
sample content, not real member data. Maps retain Leaflet and OpenStreetMap
attribution.

### Welcome and sign-in

![Welcome page with Google sign-in and the Your people, Your place message](docs/screenshots/welcome.png)

### Community feed

Browse local offers, recommendations, and conversations.

![Community feed showing sample housing, event, and food posts](docs/screenshots/community-feed.png)

### Explore posts

Search the visible map area with category and post-type filters.

![Fullscreen post search with floating filters and a results panel](docs/screenshots/explore-map.png)

### Find a community ride

Discover pickup locations, choose a departure date, and optionally narrow the
pickup time range.

![Fullscreen ride search with pickup area, date, and a sample airport ride](docs/screenshots/ride-search.png)

## Technical overview

| Layer | Technology |
| --- | --- |
| Web client | Next.js App Router, React, TypeScript, CSS |
| Maps | Leaflet, React-Leaflet, marker clustering, OpenStreetMap tiles |
| API | Python, FastAPI, Pydantic |
| Persistence | PostgreSQL, SQLAlchemy |
| Authentication | Google identity verification and JWT access tokens |
| Spatial search | H3 resolution-8 cells plus exact viewport checks |
| Location lookup | Backend-mediated Uber location search/details endpoints |
| Validation | ESLint, TypeScript/Next.js build, Python unittest API tests, PostgreSQL concurrency tests |

```text
Browser / Next.js
  |
  | JSON over HTTP + JWT
  v
FastAPI routers and authentication dependencies
  |
  +-- Pydantic validation and response schemas
  +-- Services: permissions, location resolution, ride lifecycle
  +-- Repositories: SQLAlchemy queries and row locking
  |
  v
PostgreSQL
  Users, posts, comments, reactions, saves
  Driver profiles, ride requests, offers, bookings
```

- **Map search:** H3 covering cells narrow database candidates; exact
  latitude/longitude checks enforce the viewport. Searches return up to 50
  results and indicate when more match.
- **Booking consistency:** request-row locking and unique constraints protect
  confirmation against competing offers and withdrawal races.
- **Time handling:** ride timestamps are normalized to UTC and stored in
  timezone-less columns by convention, with an IANA timezone saved on the
  request. Currently, that timezone comes from the rider's browser, not the
  pickup address. Search date/time filters use the saved ride timezone.
- **External dependencies:** sign-in needs Google configuration; location
  lookup and map tiles require network access. The location integration's
  provider availability and suitability should be reviewed before deployment.

## Repository layout

```text
backend/
  app/
    api/             FastAPI routes
    core/            Settings, authentication, time helpers
    db/              Database setup and session dependencies
    models/          SQLAlchemy models
    repositories/    Database queries
    schemas/         Request and response validation
    services/        Business logic and provider integrations
  tests/             API and PostgreSQL concurrency tests
client/
  app/               Next.js pages and global styling
  components/        Shared forms, navigation, and map UI
  lib/               API helper and domain types/utilities
docs/
  feature.md         Detailed features, API, architecture, and setup notes
  screenshots/       README UI captures
```

## Local setup

The examples below use **Windows PowerShell** from the repository root.
You need Python (the backend has been tested on 3.13), a Node.js version
compatible with Next.js 16 (20.9 or newer), npm, PostgreSQL, and a Google OAuth
web client ID. Docker is optional if you already have PostgreSQL.

### 1. Start PostgreSQL

For a local development database using Docker:

```powershell
docker compose -f backend\docker-compose.yml up -d
```

The Compose file provisions PostgreSQL 16 on port 5432 with database
`nri_platform` and local-development credentials `postgres` / `postgres`.
Do not use those credentials for a deployed environment.

### 2. Configure and run the backend

Create `backend/.env` with your own configuration:

```dotenv
GOOGLE_CLIENT_ID=your-google-oauth-web-client-id
JWT_SECRET=replace-with-a-long-random-secret
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/nri_platform
```

Use the same Google client ID for the backend and frontend, and authorize
`http://localhost:3000` as a JavaScript origin in your Google OAuth configuration.
Keep real secrets and environment files out of Git.

```powershell
Set-Location backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

Startup creates missing tables and the ride pickup H3 index. This uses
SQLAlchemy `create_all`, not a versioned migration workflow; existing schema
changes require appropriate upgrade planning. The database user needs schema
creation privileges for initial setup.

### 3. Configure and run the frontend

Create `client/.env.local`:

```dotenv
NEXT_PUBLIC_GOOGLE_CLIENT_ID=your-google-oauth-web-client-id
NEXT_PUBLIC_API_URL=http://localhost:8000
```

In a second terminal, from the repository root:

```powershell
Set-Location client
npm ci
npm run dev
```

Open **http://localhost:3000**. Interactive API documentation is available at
**http://localhost:8000/docs** while the backend is running.

The backend currently allows `http://localhost:3000` through CORS. Update the
allowlist and Google OAuth origins if you use another host or deploy the app.

### Checks

Frontend, from `client`:

```powershell
npm run lint
npm run build
```

Backend, from `backend`:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-test.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The PostgreSQL concurrency test is opt-in. See the
[test and database instructions](docs/feature.md#ride-database-setup-and-validation)
before enabling it; it creates and removes an isolated test schema.

## Documentation

Start with the **[documentation folder](docs/)** for deeper implementation
details.

- **[Features, API, and architecture](docs/feature.md)**: implemented behavior,
  endpoints, permissions, data model, ride lifecycle, and current limitations.
- **[Local configuration](docs/feature.md#local-development-configuration)**:
  environment settings and backend integration notes.
- **[Ride database setup and validation](docs/feature.md#ride-database-setup-and-validation)**:
  table/index setup and test execution.
- **[Client README](client/README.md)**: frontend routes and map search behavior.

This README describes the current feature branch. Planned capabilities should
not be assumed to exist until implemented and documented.
