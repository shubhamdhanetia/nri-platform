# NRI Platform: Features, API, and Architecture

This document describes the features and API currently implemented in the
repository. The API is served by FastAPI; the web client is a Next.js
application.

## Product features

### Authentication and navigation

- Sign in with Google from `/login`.
- The backend verifies the Google credential, creates a user on first sign-in,
  and returns a seven-day JWT access token.
- The client stores the access token in browser local storage and sends it as a
  Bearer token for authenticated API requests.
- Protected pages redirect unauthenticated visitors to `/login`.
- Main navigation contains Posts and Rides. Posts uses the existing `/explore`
  map route and is the post-login and brand-link destination. Feed remains
  accessible at `/feed` without a top-level navigation link.
- The main Rides link opens `/rides` (Browse requests). Ride tabs are ordered
  Browse requests, My rides, Driver profile. Discovery remains at `/rides`; members without
  a driver profile see setup guidance there. My rides includes request creation
  and empty-state links to request a ride or browse requests.
- Create a post is a page action in normal and fullscreen Posts views. Post
  details, creation, and the legacy feed keep Posts highlighted in navigation.
  My profile, Saved posts, and Log out are available in the account menu.
  Signing out removes the local access token.

### Posts

- Create a post with a title, description, category, post type, and a selected
  location. Posts are Public by default; authors may choose Only me.
- Categories: Housing, Rides, Jobs, Food, Events, Immigration & visa,
  Marketplace, Medical support (`MEDICAL_SUPPORT`), and General.
- Medical support is for blood-donor requests, caregiver help, and community
  resources, not emergency response. Creation, editing, category-filtered discovery,
  and post details display an emergency-services and privacy notice. Users should
  call local emergency services for immediate danger or urgent medical care.
  Posts are not monitored for emergencies and responses are not guaranteed.
  Avoid private medical records, identifying patient details, or another person's
  health information.
- Post types: Offering, Looking for, and Discussion.
- Browse the community feed, open post details, and see the author, location,
  comments, and reaction counts.
- Edit and delete your own posts. Editing is allowed only within 30 minutes of
  creation; deletion is not subject to that edit window.
- Change the visibility of your post at any time from Feed or My profile.
  Visibility changes are separate from content editing and are not restricted
  by the 30-minute edit window.
- Private (Only me) posts appear in the author's profile but not in public
  feeds, Explore results, or another user's saved-post list. Only the author
  can open a private post or access its comments and interactions.
- Post details include an author profile image/name when available.

### Comments

- Read comments on a post and add a comment.
- Edit or delete your own comments. Editing is allowed only within 30 minutes
  of comment creation.
- Comment content is trimmed and must contain 1–2,000 characters.
- Post responses include a comment count.

### Reactions

- Users can like or dislike another user's post.
- A user has at most one reaction per post; selecting the opposite reaction
  switches it, and selecting the active reaction again removes it.
- Post owners cannot react to their own posts. Their reaction controls are
  displayed as non-interactive counts.
- Reaction counts and the signed-in user's reaction are included in post
  responses.

### Saved posts

- Save and unsave posts from the feed, Explore results, post details, and the
  saved-posts page.
- `/saved` lists only the signed-in user's saved posts.
- Saving and unsaving are idempotent. A post response includes `my_saved` for
  the current user.
- Saved-post associations are unique per user/post and are deleted when the
  associated post is deleted.

### Explore map and location selection

- Explore displays an OpenStreetMap-backed Leaflet map and a list of posts in
  the searched map area. Community defaults to Map; a view selected during the
  current browser session is still remembered.
- The map requests browser geolocation on first load and has a
  **Center on my location** action. If location access is unavailable or
  denied, the map remains at its default view and displays an explanatory
  message.
- A location autocomplete lets the user search for a city or area and center
  the map on a selected result. Post creation/editing also requires selection
  of a location suggestion.
- Map searches are explicit: pan/zoom the map, choose category and/or post
  type filters, then select **Search this area**. Filter or map changes do not
  silently refresh the results.
- Post search is bounded to the current map viewport. Results are limited to
  50 and indicate when more matching posts exist.
- Nearby post markers are clustered; selecting a cluster zooms in, and
  overlapping markers can be spiderfied at maximum zoom.
- Selecting a result highlights its card and pans the map to its marker.
- A full-screen map mode is available, with collapsible search results.

### User profile

- `/profile` shows the signed-in user's profile and their posts.
- Own posts can be edited or deleted within the applicable rules. Reaction
  counts are visible but non-interactive for own posts.

### Scheduled community rides

- `/rides` is a separate ride board, not an extension of post comments.
  Members may request rides without registering as drivers.
  Existing posts in the Rides category remain community content, not bookings;
  selecting that category in Community (Feed or Map), post creation, or editing
  displays a neutral "Ride discussions, not ride requests" notice. Post details
  show a compact version. The notice explains that posts/comments do not create
  ride requests or bookings, and links to Browse ride requests and Request a ride.
  It is not repeated on individual browse cards.
- Request creation selects **both exact pickup and drop-off** through the same
  location autocomplete/provider used by posts. The server resolves both IDs;
  client-supplied coordinates and address strings are not trusted.
- Riders explicitly consent to sharing both full addresses with any signed-in
  member who has a completed driver profile. This is not a public anonymous board.
  Public meeting points are recommended instead of home addresses.
- A driver profile includes vehicle make/model, passenger seats excluding the
  driver, an international-format phone number, and an eligibility/privacy
  acknowledgement. It is marked Required, with explanatory helper text;
  creating or updating a profile stays disabled until it is checked. Browser
  validation and backend enforcement remain in place. Drivers and phone
  numbers are **not verified or vetted**.
- Requests contain a future pickup window (at most two hours), an IANA timezone,
  passengers, bags, notes, a rider contact phone, and a cost-sharing currency.
  Creation uses the browser's timezone, explicitly displayed alongside inputs.
- Drivers discover requests through Community-style **Feed** and **Map** views,
  defaulting to Map. Both share the same pickup-area search, departure date/time
  filters, results, and ride-detail actions; there is no separate table view.
  On geolocation success or pickup-area selection, requests load automatically.
  In Map, this waits for the map to center and uses its actual visible bounds;
  in Feed, it uses the selected area's initial bounds. **Search requests** in
  Feed refreshes results. Map supports panning/zooming and **Search this area**.
  Location selection uses the same initial area bounds as Community; map search
  uses the visible viewport. Only open requests with exact pickups inside the
  searched bounds are returned. Switching views preserves results and filters.
  **Show on map** switches a feed card to Map and selects its pickup. Pickup markers
  cluster and overlapping markers can be spiderfied. Selecting a marker or
  **Show on map** highlights its result; popups link to ride details.
- Discovery offers pickup area and an optional departure date. A date alone
  searches the whole day; **Add time range** reveals optional same-day From/To
  controls. Requests match when their pickup window overlaps the selected range,
  including its time endpoints. Date-only searches exclude the following midnight.
  Dates and times use each request's saved timezone, explicitly explained in the
  filter card and shown in results. Without a date, all future open requests match.
  **Apply filters** (or Enter in the date/time form) searches with the edited
  date/time in either view. **Reset filters** clears the date and time range and
  immediately reloads requests without moving or clearing the selected area.
  Both actions use the visible viewport in Map or the selected area in Feed.
  Destination filters are deferred; drop-off addresses remain visible.
- Location IDs are resolved server-side. H3 resolution-8 cells covering the
  viewport narrow database candidates using the pickup H3 expression index;
  exact latitude/longitude checks remove cell-boundary false positives.
  Viewports crossing the antimeridian are supported. As with post search,
  areas over 10,000 square kilometers or 20,000 covering cells are rejected.
- Map search returns at most 50 rides, ordered by earliest pickup, with
  `has_more` prompting users to zoom in or add filters. Map/filter changes
  display a refresh hint; panning, zooming, and filter edits require an explicit
  search. Geolocation and pickup-area selection trigger automatic searches. A
  full-screen map has collapsible results and Escape/Exit controls.
- Browser geolocation can center the map; denied/unavailable access displays
  an error and users can still search for a city without location permission.
- An offer includes a pickup time within the requested window, a message, a
  vehicle/capacity snapshot, and a proposed contribution (0–9,999.99).
  Supported currencies are USD, CAD, INR, GBP, EUR, and AUD; the rider chooses
  the currency and every offer on that request uses it. No currency conversion
  or payment collection occurs.
- Each driver has at most one offer per request. A withdrawn or time-expired
  offer can be resubmitted while the request is open. Contributions are total
  amounts for the requested trip, not per passenger. Drivers cannot offer on their own
  requests or when their passenger capacity is insufficient.
- The rider reviews offers and explicitly confirms one driver. A transaction
  locks the request, rechecks availability/eligibility/time, creates a unique
  booking, accepts the selected offer, and closes other pending offers.
  Repeating the same confirmation returns the existing confirmed booking;
  selecting another driver after booking returns a conflict.
- Before confirmation, the rider sees all offers and drivers see only their
  own. **Neither contact phone number is included in these responses.** After
  confirmation, only the rider and selected driver receive the booking and
  both phone numbers. Bookings snapshot vehicle, time, contribution, currency,
  and contacts so later profile edits do not change an agreed booking.
- Both participants can cancel a confirmed booking with a reason. The rider
  can cancel an open request. Cancellation never reopens the request; the
  rider can explicitly create another request.
- Only the rider can mark a confirmed ride completed, after the pickup window
  ends. This is a self-reported status, not proof the journey occurred.
- Expired requests/offers are derived at read time and are rejected on writes;
  no scheduler is needed. `/rides/mine` includes the rider's requests and
  requests the member offered to drive, with their offer and booking statuses.
- **No notifications, private messaging, SMS verification, live tracking,
  dispatch, or payment processing are included.** Members must refresh My
  rides/detail pages and coordinate using the contact numbers after booking.
  Local licensing, insurance, and cost-sharing rules still apply.

## Web application routes

| Route | Purpose |
| --- | --- |
| `/` | Entry page / application landing route |
| `/login` | Google sign-in |
| `/feed` | Community post feed |
| `/explore` | Map-based post discovery |
| `/create-post` | Create a post |
| `/posts/[id]` | Post details, reactions, saves, and comments |
| `/saved` | Current user's saved posts |
| `/profile` | Current user's profile and posts |
| `/rides` | Driver-only map discovery of open ride pickups and exact locations |
| `/rides/new` | Request a scheduled ride |
| `/rides/driver` | Register/update the current user's driver profile |
| `/rides/mine` | Own rider requests and driver offers |
| `/rides/[id]` | Request details, offers, confirmation and booking management |

## Backend API

Base URL defaults to `http://localhost:8000`. API documentation generated by
FastAPI is available at `/docs` while the backend is running.

All endpoints below require a valid Bearer access token except
`POST /auth/google`. Requests and responses use JSON unless otherwise noted.

### Authentication and user

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/auth/google` | Exchange a Google credential for a platform access token |
| `GET` | `/users/me` | Return the authenticated user's profile |

`POST /auth/google` accepts `{ "token": "<Google credential>" }` and returns
`access_token` plus the user's `id`, `email`, and `name`.

### Locations

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/locations/search` | Search for location suggestions |
| `POST` | `/locations/details` | Resolve a selected provider location ID to address and coordinates |

Location search accepts `latitude`, `longitude`, and `query`; its default
search type is `PICKUP`. Location details accepts an `id` and uses the
`uber_places` provider by default. The backend calls the location provider and
validates its response before returning it. Provider timeouts and invalid
responses are reported as API errors rather than silently substituted.
`addressComponents.HOUSE_NUMBER` is optional and may be null: valid places
and meeting points do not always have a street number. Their full address,
coordinates, and the address components used by posts and rides remain required.

### Rides

#### Legacy all-request search API

The independent request table has been removed from Browse requests. Feed and
Map both use the area-scoped search described above, not all-request browsing.
The table-search endpoint remains available for API compatibility and retains
the driver-profile gate and contact privacy.
`POST /rides/requests/table-search` accepts:

```json
{
  "pickup_location_id": "<optional selected provider ID>",
  "radius_km": 40.2336,
  "departure_date": "2026-11-02",
  "pickup_time_from": "09:00",
  "pickup_time_to": "10:00",
  "max_passengers": 3,
  "limit": 20,
  "cursor": null
}
```

All filters are optional; the default is all active requests except the
driver's own. The API keeps its 1–100 km range and 25 km default for
compatibility. The former table-only radius and maximum-passenger controls are
not part of the Feed/Map UI. No destination filter is accepted. Date/time validation
matches map search; date-only searches the whole day in each ride's timezone.
The response contains `rides`, `has_more`, and `next_cursor` (null on the last
page). Send the returned `{pickup_start, id}` cursor for the next page, with
the same filters. Results sort by pickup start then ID.
Pagination is live rather than a historical snapshot: newly closed requests
disappear and returning to a previous page may show updated results.

The PostgreSQL query applies status/expiry, passenger, local date/time overlap,
H3 candidates, and exact spherical distance before its limit. Radius coverings
use boundary-overlapping resolution-8 cells, including antimeridian and polar
areas, with a 200,000-cell cap; cells are bound as one PostgreSQL array.
`ix_ride_requests_status_pickup_id` supports ordered keyset browsing. The
two-hour maximum request window permits an indexed lower pickup-start bound
when excluding expired requests. Startup creates this index on existing tables.
There is no OFFSET or per-search exact COUNT. This avoids application-wide
scans, but does not guarantee million-row latency: check query plans and
representative data before production scaling, particularly large radii and
per-row timezone calculations. The new table query targets PostgreSQL.

All ride endpoints require authentication. Browse and non-owner open-request
details additionally require a driver profile. Historical details are retained
for the owner, selected driver, and drivers who previously offered, but only
booking participants receive phone numbers.

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/rides/driver-profile` | Own profile including own phone, or `null` |
| `PUT` | `/rides/driver-profile` | Create/update profile with eligibility acknowledgement |
| `POST` | `/rides/requests` | Resolve both selected locations and create a request |
| `GET` | `/rides/requests` | Browse open requests; optional `pickup_location_id`, `dropoff_location_id`, `departure_date`, `radius_km` |
| `POST` | `/rides/requests/search` | Map search: pickup viewport plus optional date and pickup time range |
| `GET` | `/rides/mine` | Own requests and trips offered as driver |
| `GET` | `/rides/requests/{id}` | Request, permitted offers, and participant-only booking |
| `POST` | `/rides/requests/{id}/offers` | Send/resubmit own offer |
| `POST` | `/rides/requests/{id}/offers/{offer_id}/withdraw` | Withdraw own pending offer |
| `POST` | `/rides/requests/{id}/confirm` | Rider chooses `{ "offer_id": 1 }` |
| `POST` | `/rides/requests/{id}/cancel` | Cancel an open owned request |
| `POST` | `/rides/requests/{id}/booking/cancel` | Participant cancels with `{ "reason": "..." }` |
| `POST` | `/rides/requests/{id}/booking/complete` | Rider marks the ride completed |

Both list endpoints accept `offset` (default 0) and `limit` (default 20, maximum
50). Browse distance defaults to 25 km and accepts 1–100 km. API datetimes
must include a UTC offset; stored UTC values are returned with explicit UTC
offsets. Amounts use database decimals and serialize as decimal strings.
Phones must use `+` followed by 8–15 digits, starting with a nonzero digit.
Validation failures return 422; permission failures 403; unavailable/changed
offers and lifecycle conflicts 409. Missing/inaccessible requests return 404.

The map uses `POST /rides/requests/search`:

```json
{
  "bounds": { "north": 37.6, "south": 37.5, "west": -122.05, "east": -121.9 },
  "limit": 50,
  "departure_date": "2026-11-02",
  "pickup_time_from": "09:00",
  "pickup_time_to": "10:00"
}
```

Only `bounds` is required. Both time endpoints must be supplied together with a
date, without UTC offsets, and the end must be later on the same day.
No time range means the whole selected day. Overlap checks use each request's
saved IANA timezone; repeated fall-back hours include both occurrences.
Destination/radius parameters remain supported by the API for compatibility,
but are no longer offered in the UI. The response is
`{ "rides": [...], "has_more": false }`. Filtering occurs before the limit.
The existing `GET /rides/requests` radius/list API remains available for
compatibility but is no longer used by the Ride requests discovery page.

### Posts

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/posts` | Create a post |
| `GET` | `/posts` | List posts for the feed |
| `POST` | `/posts/search` | Search posts in map bounds, optionally by category and post type |
| `GET` | `/posts/me` | List the authenticated user's posts |
| `GET` | `/posts/saved` | List the authenticated user's saved posts |
| `GET` | `/posts/{post_id}` | Get a post and its author details |
| `PUT` | `/posts/{post_id}` | Edit an owned post within the 30-minute edit window |
| `PUT` | `/posts/{post_id}/visibility` | Change visibility of an owned post at any time |
| `DELETE` | `/posts/{post_id}` | Delete an owned post |
| `POST` | `/posts/{post_id}/save` | Save a post |
| `DELETE` | `/posts/{post_id}/save` | Remove a post from saved posts |
| `PUT` | `/posts/{post_id}/reaction` | Set or switch the current user's reaction |
| `DELETE` | `/posts/{post_id}/reaction` | Remove the current user's reaction |

Post creation and update accept `title`, `description`, `category`,
`post_type`, optional `is_private` (defaults to `false` for creation), and a
selected `location_id`. Set `is_private` to `true` for Only me visibility.
Visibility can also be changed at any time with
`PUT /posts/{post_id}/visibility` and `{ "is_private": true }`. The backend
resolves the location ID to address fields and coordinates; clients do not
submit trusted map coordinates directly.

`POST /posts/search` accepts:

```json
{
  "bounds": {
    "north": 37.45,
    "east": -122.0,
    "south": 37.3,
    "west": -122.2
  },
  "limit": 50,
  "category": "HOUSING",
  "post_type": "REQUEST"
}
```

`category` and `post_type` are optional; `limit` defaults to 50 and cannot
exceed 50. The response shape is `{ "posts": [...], "has_more": false }`.
Search areas larger than 10,000 square kilometers or containing more than
20,000 H3 cells are rejected; zoom in and try again.

Post responses contain the post's location, category, type, timestamps, owner
ID, `is_private`, comment/like/dislike counts, `my_reaction`, and `my_saved`. The
`/posts/{post_id}` detail response additionally includes author `id`, `name`,
and optional `picture`.

The feed (`GET /posts`) and map search (`POST /posts/search`) return only
public posts. `GET /posts/me` returns all posts belonging to the authenticated
user. A private post requested by another user returns HTTP `404`, including
when accessed through detail, comments, saves, or reactions.

### Comments

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/posts/{post_id}/comments` | List comments on a post |
| `POST` | `/posts/{post_id}/comments` | Add a comment |
| `PUT` | `/posts/{post_id}/comments/{comment_id}` | Edit an owned comment within its edit window |
| `DELETE` | `/posts/{post_id}/comments/{comment_id}` | Delete an owned comment |

Create/update comment requests use `{ "content": "..." }`. Comment responses
include the author, post ID, and timestamps. An expired edit window returns
HTTP `403`; nonexistent or inaccessible owned resources return HTTP `404`.

### Common API behavior

- Missing or invalid Bearer credentials return HTTP `401`.
- Private posts are filtered and access-checked by the backend; hiding them in
  the client is not the privacy boundary.
- Invalid request payloads are validated by Pydantic and return HTTP `422`.
- Missing resources generally return HTTP `404`.
- Attempting to react to your own post returns HTTP `403`.
- Post and comment edit-window violations return HTTP `403`.
- The API's configured CORS origin currently includes
  `http://localhost:3000`; update the backend CORS configuration when deploying
  the client at another origin.

## Architecture and data model

```text
Next.js client
  ├─ App Router pages and shared UI components
  ├─ apiRequest helper (JSON, Bearer token, API error handling)
  ├─ Leaflet / React-Leaflet Explore map
  └─ FastAPI backend
       ├─ API routers and Bearer-auth dependency
       ├─ Pydantic request/response schemas
       ├─ Services: Google token verification, location resolution, H3 search
       ├─ Repositories: SQLAlchemy data access
       └─ SQLAlchemy models / configured relational database
```

The API is organized into routers, schemas, services, repositories, models,
and database dependencies. Google sign-in is verified server-side. The
backend signs a JWT using HS256; the token identifies the user by its `sub`
claim and expires after seven days.

Core persisted entities:

- **User** — Google identity and profile information.
- **Post** — content, category/type, resolved address, coordinates, H3 cell,
  and owner.
- **Comment** — post content, author, and timestamps.
- **PostReaction** — one `LIKE` or `DISLIKE` per user/post pair.
- **SavedPost** — one saved-post association per user/post pair.
- **DriverProfile** — self-reported vehicle/capacity, private phone and eligibility acknowledgement.
- **RideRequest** — provider-resolved exact endpoint snapshots, UTC pickup
  window, IANA timezone, rider, private contact and requirements.
- **RideOffer** — unique driver/request association with time, contribution,
  message and vehicle snapshot.
- **RideBooking** — unique booking per request/offer with agreed contact and
  contribution snapshots; confirmed/completed/cancelled lifecycle.

Posts store latitude/longitude and an H3 cell at resolution 8. Map search
first identifies candidate H3 cells intersecting the requested bounds, then
filters posts against the actual bounds. Longitude bounds that cross the
antimeridian are split into two ranges.

## Technology

- **Client:** Next.js App Router, React, TypeScript, Leaflet,
  React-Leaflet, and `react-leaflet-cluster`.
- **Backend:** Python, FastAPI, Pydantic, SQLAlchemy, and H3.
- **Authentication:** Google credential verification and JWT Bearer access
  tokens.
- **Maps:** Leaflet with OpenStreetMap tiles and attribution.
- **Location lookup:** Backend-mediated Uber Places search/details provider.

## Local development configuration

The client README documents the local client setup. Create
`client/.env.local` with:

```env
NEXT_PUBLIC_GOOGLE_CLIENT_ID=your-google-oauth-client-id
NEXT_PUBLIC_API_URL=http://localhost:8000
```

`NEXT_PUBLIC_API_URL` is optional and defaults to
`http://localhost:8000`. The backend settings are loaded from `.env` and
require `DATABASE_URL`, `JWT_SECRET`, and `GOOGLE_CLIENT_ID` as declared in
`backend/app/core/config.py`. Do not commit real credentials or secrets.

From the client directory:

```powershell
npm run dev
npm run lint
npm run build
```

Run the FastAPI application with the backend's configured ASGI entry point
(the application object is `app` in `backend/app/main.py`).

### Ride database setup and validation

Install the updated backend requirements before starting/restarting the API;
`tzdata` supplies IANA timezone data on Windows. Startup creates the four new
ride tables (`driver_profiles`, `ride_requests`, `ride_offers`, `ride_bookings`)
through the repository's existing `Base.metadata.create_all` setup. This is
additive: existing user/post tables and rows are not rewritten. The configured
database user must have permission to create tables. No manual column
alterations are needed for this feature.

The ride-map update adds `ix_ride_requests_pickup_h3`, an expression index on
the pickup JSON's `h3_cell_id`. Startup explicitly creates this index if missing,
including on an existing ride table (`create_all` alone does not add indexes
to existing tables). Restart the API after updating. No location backfill is
needed: requests already store resolution-8 H3 cells in their pickup snapshots.

From the backend directory, using your configured Python environment:

```powershell
python -m pip install -r requirements-test.txt
python -W ignore::DeprecationWarning -m unittest discover -s tests -v
```

The API tests use an isolated in-memory SQLite database, synthetic users, real
authentication dependencies, and mocked location-provider responses. To
additionally verify actual PostgreSQL row-lock behavior:

```powershell
$env:RIDE_TEST_POSTGRES = "1"
python -W ignore::DeprecationWarning -m unittest discover -s tests -v
Remove-Item Env:RIDE_TEST_POSTGRES
```

The opt-in concurrency test uses the configured PostgreSQL connection, creates
a uniquely named `ride_test_*` schema, tests competing confirmations, duplicate
confirmation retries, and withdrawal-versus-confirmation races, then drops only
that test schema. It does not insert fixtures into the application's tables.
The database user needs schema creation permission for this optional test.

Ride map discovery filters pickup candidates in SQL using the H3 index and
exact viewport bounds, then streams those candidates for per-request local
date/time overlap checks (and compatibility destination filters) before
enforcing the result cap. The legacy
radius-only list endpoint still streams open candidates without a spatial
prefilter. A larger deployment may also benefit from destination geospatial
indexing and database-side timezone/date filtering.

## Current implementation notes

- Backend startup calls SQLAlchemy `Base.metadata.create_all` to create missing
  tables. It does not alter existing tables; databases created before post
  visibility was added must already have the `posts.is_private` column.
  Existing posts are Public by default.
- Map-result searches are initiated by the user and are limited to 50
  returned posts per request.
- Geolocation depends on browser permission and device availability.
- The client and backend should be kept in sync when changing category/type
  enums or post/comment response fields.
