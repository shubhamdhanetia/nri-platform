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
- `/notifications` — shared private inbox for ride and carpool updates

Ride addresses are visible to signed-in members with a driver profile after
explicit rider consent. Phone numbers are unverified and shared only with
booking participants after confirmation. The notification bell beside the profile
button opens a shared inbox with unread indicators and links to the relevant
ride or carpool. Messages can be marked read individually. The bell refreshes
every 30 seconds, on focus, and after notification changes; the inbox has an
explicit Refresh action. There is no email/SMS/push delivery, messaging,
live tracking or platform payments in this version.
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

The header contains **Posts** and **Rides**. Rides opens **Find a ride**
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
