# NRI Platform client

The client is a Next.js app that supports the MVP community flow:

- `/login` — sign in with Google
- `/feed` — legacy community feed, retained without a top-level navigation link
- `/explore` — Posts: the primary post discovery page and post-login destination
- `/create-post` — publish a post with a title, description, category, and selected location
- `/profile` — view the signed-in user and their posts
- `/rides` — search scheduled ride pickups on a map after completing a driver profile
- `/rides/new` — request a ride with exact pickup and drop-off location selections
- `/rides/driver` — register a vehicle, passenger capacity and private contact number
- `/rides/mine` — check own requests, offers and booking statuses
- `/rides/[id]` — send/review cost-sharing offers, confirm, cancel or complete a ride
- `/rides/carpools` — find driver-published planned trips
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

Ride discovery offers Community-style **Map** and **Feed** views, defaulting to
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

The **Medical support** community category includes a notice on creation, editing,
filtered discovery, and post details: use local emergency services for urgent care
and avoid sharing private medical information. Its API value is `MEDICAL_SUPPORT`.
New databases include it through the post model. Existing local databases need
the category column widened to `VARCHAR(15)` and the `post_category` check updated
to include `MEDICAL_SUPPORT`; `create_all` does not alter existing tables.

The header contains **Posts** and **Rides**. Rides opens **Ride requests**
(`/rides`); tabs are **Ride requests**, **Find a carpool**, **Request a ride**,
**Offer a carpool**, **My rides**, and **Driver profile**. Offer a carpool opens
the existing publishing form at `/rides/carpools/new`. My rides separates
**Carpools** from **Requests & offers**. Notifications are global, not a Rides tab.
The former `/rides/carpools/inbox` page redirects to `/notifications`.
Discovery stays at `/rides`, including driver-profile setup guidance.
My rides keeps request creation prominent and offers a browse action when empty.
The brand opens Posts; viewing or
creating posts keeps Posts highlighted. **Create a post** is available on the
Posts page in both normal and fullscreen map modes. My profile, Saved posts,
and Log out remain in the account menu. Existing URLs are unchanged.

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
