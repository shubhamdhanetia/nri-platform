# NRI Platform client

The client is a Next.js app that supports the MVP community flow:

- `/login` — sign in with Google
- `/feed` — legacy community feed, retained without a top-level navigation link
- `/explore` — Posts: the primary post discovery page and post-login destination
- `/create-post` — publish a post with a title, description, category, and selected location
- `/profile` — view the signed-in user and their posts
- `/rides` — Find a ride: search planned carpools and request seats
- `/rides/requests` — Find passengers: browse ride requests after completing a driver profile
- `/rides/new` — request a ride with exact pickup and drop-off location selections
- `/rides/driver` — Driver settings: register a vehicle, passenger capacity and private contact number
- `/rides/mine` — check own requests, offers and booking statuses
- `/rides/[id]` — send/review cost-sharing offers, confirm, cancel or complete a ride
- `/rides/carpools/new` — offer an outbound trip and optional independent return
- `/rides/carpools/[id]` — request seats, review approvals and manage cancellations
- `/notifications` — shared private inbox for ride, carpool, and housing updates
- `/housing` — available places and housing requests, with price/date/household filters
- `/housing/people` — people looking for accommodation or wanting to search together
- `/housing/roommates` — legacy link redirected to `/housing/people`
- `/housing/new` — list a place, request housing, or find a place together
- `/housing/mine` — manage housing status, visibility, editing, and availability renewal
- `/housing/saved` — saved housing, subject to privacy and deletion
- `/housing/inquiries` — private housing inquiry threads and replies

## Housing

Housing is a dedicated discovery/inquiry feature, separate from Community posts
and Rides. Existing Community Housing posts are not migrated or removed.
Available places support shared rooms, private rooms, and entire homes; requests
can also be flexible. Arrangements distinguish joining a household, rentals,
sublets, and lease takeovers. Short-term stays are listings, not reservations.

The form captures rent/budget with currency and period, deposit and fees,
dates and minimum stay, furnishing, bathroom, utilities, occupants, availability,
approval claims, optional practical household preferences, and up to eight
HTTPS photo URLs. Photos load directly from their hosts without sending the app's
referrer; there is no image-upload service. New and edited posts select a
location through the existing autocomplete APIs. The backend resolves city,
state, country, address, coordinates, and resolution-8 H3 cell from its provider ID;
clients cannot supply their own coordinates. Public Housing posts expose the
original selected address and exact coordinates to signed-in members, without
obfuscation. Housing requests and searching-together posts select a preferred
area, not the address of a confirmed available home.

Housing photos use a manual carousel on cards and a main image with thumbnails
on details. Clicking a photo opens a native modal viewer above fullscreen maps.
Previous/Next, Left/Right keys, and touch swipes navigate without autoplay;
navigation stops at the first/last image. Zoom is capped at native resolution
and 3x the fitted size; drag or scroll pans when zoomed. Changing photos resets
zoom. Escape closes only the photo viewer, restoring focus and underlying scroll
locks, filters, and map selection. Broken links show an explicit placeholder.
Only adjacent full-view images are preloaded; card/thumbnail images are lazy.

Search uses server-side pagination, location/keyword filters, dates, and structured
space, arrangement, price, stay, furnishing, bathroom, kitchen, parking, and
laundry filters. Budget filters require a currency and period, avoiding comparisons
between monthly/nightly or different-currency amounts. Find a place shows only
available listings, including shared/private rooms and entire homes. Find people
shows only housing requests and searching-together posts, including entire-home
requests. Its Looking for selector narrows those two types. The two discovery
views never overlap; posting still has the same three choices.

Discovery starts in Map view, remembers Map/List preference in the browser
session, and keeps applied filters and search bounds when switching views.
Like Rides, it requests browser location on entry and searches the current-location
viewport after the map centers. It does not first download unrestricted results.
If permission is denied or location is unavailable, an explicit message offers
city/area autocomplete or manual map search instead. The location input uses the
shared Community/Rides styling with an inline current-location icon; the map also
has recenter and fullscreen controls. Escape exits fullscreen and restores scrolling.
Fullscreen expands the entire Housing browser, like Rides: the heading, location
search, all filters, view switch, map, and results stay available. Filters use a
compact layout above the map; desktop results use a narrower scrolling column,
while phone layouts stack the map and results. Entering/exiting fullscreen does
not reset entered filters, selected results, or the map viewport.
The shared Leaflet map clusters results and synchronizes
marker/card selection. Subsequent panning does not fetch automatically; Search this area
applies the current viewport. Search housing applies the form filters and current
map viewport (or existing area in List view). Reset filters keeps the area;
Search all areas clears only the geographic restriction.
H3 candidates are narrowed with exact latitude/longitude bounds, including
antimeridian handling. The map shows only the current result page and explains
when more pages exist. Existing coordinate-less posts remain in unrestricted
list results but do not match bounded searches until their owners add a location.

Owners can mark filled/resolved, archive, reopen, renew, edit, make private, or
delete. Active public posts expire from discovery after 30 days; renewal explicitly
confirms freshness. Filled, archived, and expired posts retain public saved/detail
access. Private posts and their inquiries are inaccessible to other members.
New housing inquiries notify the post owner; replies notify only the other
participant through the shared notification bell and inbox. Notifications do not
include private message contents and link directly to the conversation, independent
of inbox pagination (`/housing/inquiries?inquiry_id=<id>`). Inaccessible or deleted
conversations show an explicit error. Sending shows a confirmation, not a notification
to yourself. Refresh the conversation to load new replies; there are no email or push
alerts. Existing messages are not backfilled into notifications.

Housing has no booking, payment, screening, or automated verification. Reports
are persisted for manual operator review, not automatically actioned; there is
no moderation dashboard. No gender, caste, religion, or nationality eligibility
filters are provided. Apply Alembic revision `0008` before using Housing; `0007`
creates Housing and `0008` adds its locations and indexed H3 search.

### Local Housing samples

From `backend`, run
`.\.venv\Scripts\python.exe -m scripts.seed_housing --email "existing-user@example.com"`.
This refuses non-local PostgreSQL and requires the owner to exist and migrations
through `0008`. It adds 26 `[Demo]` posts across nine public landmark anchors in
Fremont, San Jose, Sunnyvale, San Francisco, Oakland, Berkeley, and Long Beach
(downtown, Belmont Shore, Bixby Knolls). All posts explain that neither the
availability nor the illustrative stock-photo URLs represent real properties.
Coverage includes all post/space/arrangement/stay/price-period types, practical
household filters, active/filled/archived/private/expired/ended-date examples.
Inactive and private cases are intentionally absent from public discovery;
inspect them in My housing. Re-running preserves existing demo posts and owner edits.
It never creates other members, messages, saves, bookings, or notifications.

### Local ride and carpool samples

From `backend`, run
`.\.venv\Scripts\python.exe -m scripts.seed_rides --email "existing-user@example.com"`.
The script requires local PostgreSQL (no host/service overrides), the current
Alembic migration head, and an existing owner with an acknowledged, valid driver
profile. If the profile is missing, complete it locally with the user's real
details first; the script never invents or changes phone numbers, vehicles,
license plates, eligibility acknowledgements, or other account information.
The existing profile phone is reused privately for the owner's ride requests.

It inserts six OPEN carpools (including a linked same-day return) and six OPEN
ride requests across public Bay Area and Los Angeles-area landmarks. Examples
vary seats within the real driver's capacity, passengers, luggage, pickup
windows, and USD amounts (including free and unspecified preferred budgets).
All notes prominently label fictional samples, not actual offers or requests.
New departures are 3–14 days ahead in `America/Los_Angeles`; landmark coordinates
are resolved through the existing location provider, so provider access is needed
on first seed. Only landmark queries, not user/profile details, go to the provider.

One transaction commits the complete batch or nothing. Deterministic owner-scoped
IDs make reruns insert only missing samples and preserve existing dates, status,
and owner edits; rerunning does not refresh samples after they expire. No other
users, offers, seat requests, bookings, messages, or notifications are created.
Validate with
`.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_ride_seed.py`.

Ride addresses are visible to signed-in members with a driver profile after
explicit rider consent. Phone numbers are unverified and shared only with
booking participants after confirmation. The notification bell beside the profile
button opens a shared inbox with unread indicators and links to the relevant
ride, carpool, or housing inquiry. Notifications can be marked read individually or
all at once; opening a conversation does not automatically mark them read. The bell refreshes
every 30 seconds, on focus, and after notification changes; the inbox has an
explicit Refresh action. Rides has no email/SMS/push delivery, messaging,
live tracking or platform payments. Housing provides separate private inquiry threads.
See [feature documentation](../docs/feature.md) for API, privacy,
database setup and tests.

Rides has three main tabs: **Find a ride**, **Find passengers**, and **My rides**.
Find a ride is the Rides landing page and includes **Request a ride**.
Find passengers browses rider requests and includes **Offer a carpool** for
drivers who already have a planned trip. Creation pages highlight their respective
discovery tab; details and Driver settings highlight My rides.
My rides keeps separate Carpools and Ride requests & driver offers sections,
and provides the Driver settings link. Driver setup is also linked from
Find passengers, carpool creation, and ride details when needed.
Users can participate as both passengers and drivers without switching roles.
Booking workflows, cost sharing, privacy rules, and backend API paths are unchanged.

Find passengers offers Community-style **Map** and **Feed** views, defaulting to
Map. Requests load automatically after geolocation or pickup-area selection.
Map searches use the visible viewport; **Search this area** refreshes after
panning or zooming. Markers show exact pickups inside the viewport;
destinations can be outside it. Searches return up to 50 rides, earliest first.
Changing the map or date/time filters requires another explicit search.
**Apply filters** (or Enter in the date/time form) applies the date/time;
**Reset filters** clears them and reloads without changing the selected area.
Full-screen mode supports hiding/showing results and Escape to exit. Without a date,
all future open requests match; a date alone searches the whole day. An optional
same-day From/To range matches overlapping pickup windows. Dates and times use
each ride's saved timezone, shown in the results. Drop-off addresses are still
shown, but destination filters are not offered in this version.

Feed and Map share results and filters. **Show on map** selects a ride's pickup
and switches to Map. The independent all-request table and its radius/passenger
filters have been removed; its API remains available for compatibility.
Browse cards show passengers and bags without a standalone currency label.
Community also defaults to Map, while remembering an explicitly selected view
within the current browser session.

## Local setup

Community offers and requests have independent `ACTIVE`/`CLOSED` status.
Owners can Mark unavailable (offers), Mark resolved (requests), or Reopen from
discovery, My posts, and details; completion is not restricted by the edit window.
Closed posts disappear from discovery and member-profile listings but remain in
My posts (All/Active/Closed filters) and saved posts with a status label.
My posts cards separate comment/reaction counts from a wrapping owner-action
row, keeping completion, visibility, editing, and deletion controls readable on mobile.
Existing detail links work while visibility permits. Making a post private hides
it from other members, including those who saved it; deletion removes it.
Closed posts preserve comments/reactions but reject new comments until reopened.
Discussions cannot be closed; reopen before changing a closed post to Discussion.
Content edits and visibility changes never implicitly reopen a post.
Apply Alembic revision `0005` before running the updated application. Existing
posts start Active. Downgrade refuses to discard status while closed posts remain.

Ride-request and carpool discovery maps share the Pickup/Destination legend
and clear-selection control. Selecting a result's title or Show on map reveals
both endpoints and their connection (not a driving route); carpool card
selection also fits both endpoints. View carpool still opens trip details.

Community discovery categories adapt to the available width: desktop shows
complete category shortcuts and a More menu for overflow, while mobile uses
a category picker bottom sheet. A selected overflow category is named in the
desktop trigger. Both controls support keyboard navigation and Escape dismissal.

The **Sports** community category uses the API value `SPORTS` and is available
in creation/editing, discovery filters, and post/category labels. Apply backend
Alembic revision `0002` before running the updated API and frontend against an
existing database. The migration preserves all existing posts.

The **Parking** community category (`PARKING`) supports parking available,
parking wanted, and discussions using the existing post types. It is included
in creation/editing, discovery filters, and category labels, with a parking icon.
Create/edit guidance adapts to Offering (availability, pricing, restrictions,
and permission to rent out the space) or Looking for (area, duration, budget,
and vehicle size). Both explain contact and location visibility, optional landmark
selection, and keeping access credentials private. No notice appears before
choosing a post type, for discussions, or on discovery. Offer/request details
show only a brief reminder to confirm arrangements; posts are not reservations.
Apply Alembic revision `0004` before using Parking against an existing database.
Existing posts are preserved; rollback is rejected while Parking posts remain.
This adds no booking, payment, private messaging, or car-rental functionality.

The **Travel** community category (`TRAVEL`) replaces the former Rides category.
Apply Alembic revision `0003` with the development API stopped, then restart
the updated API and frontend. Existing Rides community posts become Travel
posts; the separate Rides feature, requests, carpools, and bookings are unchanged.
Community screens no longer show the ride-request notice or its links.

The **Medical support** community category includes a notice on creation, editing,
filtered discovery, and post details: use local emergency services for urgent care
and avoid sharing private medical information. Its API value is `MEDICAL_SUPPORT`.
New databases include it through the initial Alembic migration. Older local
databases need a reviewed schema upgrade before adopting the migration baseline;
see [database setup](../README.md#existing-local-databases).

The header contains **Community**, **Rides**, and **Housing**. Rides opens **Find a ride**
(`/rides`); its three tabs are **Find a ride**, **Find passengers**, and **My rides**.
Find passengers is at `/rides/requests`. Posting actions remain at `/rides/new`
and `/rides/carpools/new`. Driver settings is available from My rides.
Notifications are global, not a Rides tab.
The former `/rides/carpools/inbox` page redirects to `/notifications`.
The brand opens Posts; viewing or
creating posts keeps Posts highlighted. **Create a post** is available on the
Posts page in both normal and fullscreen map modes. My profile, Saved posts,
and Log out remain in the account menu. Ride-request and carpool detail URLs
and all backend API paths are unchanged.

Create `client/.env.local` with the Google OAuth web client ID:

```env
NEXT_PUBLIC_GOOGLE_CLIENT_ID=your-google-oauth-client-id
```

The backend API defaults to `http://localhost:8000`. To use a different API
origin, set:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Run the backend and client, then open `http://localhost:3000`:

```bash
npm run dev
```

The client sends the backend access token as a Bearer token for authenticated
requests. The backend must allow the client origin through CORS.
