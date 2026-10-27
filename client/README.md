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

Ride addresses are visible to signed-in members with a driver profile after
explicit rider consent. Phone numbers are unverified and shared only with
booking participants after confirmation. There are no notifications, messaging,
live tracking or platform payments in this version; refresh My rides to check
updates. See [feature documentation](../docs/feature.md) for API, privacy,
database setup and tests.

Ride discovery uses the same clustered map as Explore posts. Find a pickup
area, pan/zoom, optionally select a departure date and expand **Add time range**,
then click **Search this area**. Markers show exact pickups inside the viewport;
destinations can be outside it. Searches return up to 50 rides, earliest first.
Changing the map or filters requires another explicit search. Full-screen
mode uses Explore's floating filter card over the full map and an overlaid
results panel, with hiding/showing results and Escape to exit. Without a date,
all future open requests match; a date alone searches the whole day. An optional
same-day From/To range matches overlapping pickup windows. Dates and times use
each ride's saved timezone, shown in the results. Drop-off addresses are still
shown, but destination filters are not offered in this version.

## Local setup

The header contains **Posts** and **Rides**. Rides opens **My rides**
(`/rides/mine`); tabs are **My rides**, **Browse requests**, and **Driver profile**.
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
