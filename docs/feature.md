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
- The main Rides link opens `/rides` (Ride requests). Ride tabs are ordered
  Ride requests, Find a carpool, Request a ride, Offer a carpool, My rides, Driver profile.
  Request a ride opens the existing creation form at `/rides/new`.
  Offer a carpool opens the existing publishing form at `/rides/carpools/new`.
  Ride requests describes people looking for transportation, with guidance to
  offer to drive someone going your way.
  A notification bell beside the profile button opens the shared inbox at
  `/notifications`; it is not a Rides-specific tab.
  Discovery remains at `/rides`; members without
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
  ride requests or bookings, and links to Ride requests and Request a ride.
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
- Ride lifecycle updates use the shared notification inbox. **No private
  messaging, SMS verification, live tracking, dispatch, or payment processing
  are included.** Members refresh detail pages for current state and coordinate
  using the contact numbers after booking.
  Local licensing, insurance, and cost-sharing rules still apply.

### Planned-trip carpools

- Carpools are a driver-first flow alongside existing rider requests. A driver
  publishes an already-planned journey, not an on-demand transport service.
- Publishing requires a driver profile and explicit consent that full public
  meeting-point addresses are visible to signed-in members. The server resolves
  location IDs; phone numbers are not part of trip listings.
- Each direction has its own future departure window (zero to two hours),
  browser-derived IANA timezone, available seats (1-8, no more than the driver
  profile's passenger capacity), bag allowance per person, fixed contribution
  per passenger, currency, vehicle snapshot, and notes. No bargaining or
  payment collection is offered. Supported currencies match ride requests.
- An optional linked return is created atomically with the outbound trip.
  Its route defaults to reversed meeting points in the UI, but can be changed;
  its time, seats, luggage allowance, and contribution are independent.
  Return departure must follow the outbound departure window.
- Search accepts optional pickup/destination areas, a radius of 1-100 km
  (default 25), a departure date in each trip's saved timezone, and seats needed.
  Results exclude the viewer's own, full, cancelled, and departed trips.
  Filtering happens before offset pagination; list responses include `has_more`.
- Passengers request seats and total bags for one or both directions. Both
  requests are created in a single transaction, or neither is created if one
  direction is unavailable, already requested, or cannot accommodate the party.
  Each direction is approved independently, and UI status explicitly distinguishes
  pending requests from confirmed bookings.
- Pending requests do not hold capacity. Approval locks the trip row and
  rechecks remaining confirmed seats, preventing overbooking. Duplicate approval
  is idempotent and does not send duplicate events. Each passenger account can
  submit one request per direction; declined/cancelled requests remain historical,
  and cannot be resubmitted in v1.
- Drivers see passenger names, party sizes, luggage, and messages for their own
  trips; passengers see only their own request. Neither phone is returned until
  confirmation. Confirmation snapshots the driver's phone; the passenger phone
  comes from the request. Confirmed contact details are available only to that
  passenger and driver, and are hidden again after cancellation.
- Driver approval/decline and participant cancellation are permission-checked.
  Pending request cards show drivers **Accept request** and **Decline request**;
  passengers see **Withdraw request** for their own pending request. Either
  participant can **Cancel booking** after confirmation. Driver cards do not
  show a redundant cancellation action for pending requests. Card action buttons
  are stacked at full width so labels do not collapse into narrow text columns.
  Cancellation requires a reason. Cancelling a confirmed seat request releases
  capacity; driver trip cancellation cancels all pending/confirmed requests on
  that direction. Linked directions are never implicitly cancelled.
- Published terms are immutable. Changes require cancellation and a new trip,
  so confirmed passengers are never silently moved to different terms.
  New requests, approvals, and declines close when the earliest departure time
  arrives; cancellations remain available until the departure window ends.
  The response's `can_cancel` flag controls last-minute cancellation actions.
  Pending requests then display `EXPIRED`; trip status
  displays `DEPARTED`, without a scheduler. `FULL` is derived from confirmed seats.
- Durable notifications are written in the same transaction as each new request,
  approval, decline, or cancellation. The counterpart receives an inbox event;
  cancelling an entire trip notifies every pending/confirmed passenger.
  Inbox records are private to the recipient, paginated, and individually marked
  read. The global bell refreshes the unread count every 30 seconds, on focus,
  and after in-app mutations. The inbox itself has an explicit Refresh button.
- My rides lists both carpool directions separately, including closed/historical
  trips. It separates **Carpools** from **Requests & offers** with keyboard-accessible
  tabs, defaulting to Carpools. The selected tab is remembered in session storage
  when returning from trip details. Each section retains its own pagination,
  loading/error/empty states, and creation actions; switching tabs preserves both
  lists and page positions while the page remains mounted. Cards show your role
  as **Driver** or **Passenger**. In-app notifications cover rides and carpools.
  No email, SMS, push, chat,
  route optimization, intermediate-segment bookings, verification, reviews,
  reporting/blocking system, or live tracking is provided in this first version.

### Shared notifications

- `/notifications` is an authenticated, app-wide inbox, opened directly by the
  bell beside the profile button. The badge shows unread count (visually capped
  at `99+`, with the full count in its accessible name). Loading failures are
  visible as an error indicator and accessible error text, not an empty count.
- Events include a recipient, category, event type, resource ID, internal detail
  path, message, read state, and UTC creation time. The model has no ride/carpool
  foreign key, so future features can use the same service and inbox.
- Feature services call `app.services.notifications.notify` within their
  existing transaction; the helper does not commit. Business changes and
  events succeed or roll back together. No public event-creation endpoint exists.
- Inboxes, unread counts, and read actions are scoped to the signed-in member.
  Reading another member's event returns 404. Marking an event read is idempotent.
  Detail links still use each feature's authorization checks.
- Events are newest first by creation time and ID. Read and unread events remain
  in the same paginated history. Opening the inbox does not implicitly mark all
  events read; each has a Mark as read action. The inbox has an explicit Refresh.
- The global bell refreshes on mount, every 30 seconds, on browser focus, and
  after local notification changes. Stale overlapping count responses cannot
  overwrite newer results.
- Rides notify the rider on new/resubmitted offers and withdrawals; selected
  drivers on confirmation; other pending offer drivers when not selected;
  pending offer drivers when a request is cancelled; and the other booking
  participant when a confirmed ride is cancelled or marked completed.
  Actors do not receive notifications about their own actions. Creating a ride
  request does not broadcast to all drivers, and failed/idempotent operations
  do not generate additional events.
- Carpool recipients and lifecycle rules are unchanged, but their events now use
  the shared storage and API. Notification messages do not include phone numbers
  or private cancellation reasons; participants open the authorized detail view.
- Startup creates the new `notifications` table and idempotently copies existing
  `carpool_notifications` history, preserving recipients, messages, timestamps,
  and read state. A unique legacy source ID prevents duplicate imports or read
  state resets. PostgreSQL startup workers serialize the copy using a transaction
  advisory lock. The legacy table is retained, no longer written by new actions.
- This is in-app delivery only; there is no email, SMS, push, or real-time socket
  delivery, and no notification integration for other features yet.

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
| `/notifications` | Shared private inbox for platform notifications |
| `/rides` | Driver-only map discovery of open ride pickups and exact locations |
| `/rides/new` | Request a scheduled ride |
| `/rides/driver` | Register/update the current user's driver profile |
| `/rides/mine` | Own carpools, seat requests, rider requests, and driver offers |
| `/rides/[id]` | Request details, offers, confirmation and booking management |
| `/rides/carpools` | Search driver-published planned trips |
| `/rides/carpools/new` | Publish an outbound trip and optional linked return |
| `/rides/carpools/[id]` | Trip details, seat requests, approvals, and cancellation |
| `/rides/carpools/inbox` | Legacy redirect to `/notifications` |

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

The independent request table has been removed from Ride requests. Feed and
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

#### Carpool API

All paths below are under `/rides/carpools` and require authentication.
Browsing does not require a driver profile; publishing does.

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/trips` | Publish `{outbound, return_trip?, public_meeting_point_consent: true}` |
| `GET` | `/trips` | Browse with optional `pickup_location_id`, `dropoff_location_id`, `departure_date`, `passengers`, `radius_km`, `offset`, `limit` |
| `GET` | `/mine` | Own published trips and requested directions |
| `GET` | `/trips/{id}` | Trip, linked direction, and permitted seat requests |
| `POST` | `/trips/{id}/requests` | Request `{passengers, bags, rider_phone, message?, include_return?: false}` |
| `POST` | `/trips/{id}/requests/{request_id}/accept` | Driver confirms seats |
| `POST` | `/trips/{id}/requests/{request_id}/decline` | Driver declines a pending request |
| `POST` | `/trips/{id}/requests/{request_id}/cancel` | Participant cancels with `{reason}` |
| `POST` | `/trips/{id}/cancel` | Driver cancels one direction with `{reason}` |

Each leg contains `pickup_location_id`, `dropoff_location_id`, `pickup_start`,
`pickup_end`, `timezone`, `seats`, `bags_per_person`, `amount`, `currency`, and
optional `notes`. Times require UTC offsets and amounts serialize as decimal
strings. List/mine responses are `{trips, has_more}`; trip creation, detail,
and trip/request mutations return `{trip, linked_trip, requests}`.
Lists accept `offset` (default 0) and `limit` (default 20, maximum 50).
Missing/inaccessible resources return 404, permission failures 403,
lifecycle/capacity conflicts 409, and invalid input 422.

Carpool storage adds `carpool_trips` and `carpool_seat_requests`, with events in
the shared `notifications` table (`carpool_notifications` is retained for migration).
The existing startup `Base.metadata.create_all`
creates these new tables on backend restart; no existing columns are changed.
PostgreSQL race tests use isolated schemas with `RIDE_TEST_POSTGRES=1`, covering
last-seat approvals, duplicate approvals/requests, and cancellation races.

#### Shared notification API

All endpoints require authentication and operate only on the current member's
notifications. New features publish through the internal notification service.

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/notifications` | Paginated `{notifications, unread_count, has_more}` |
| `GET` | `/notifications/unread-count` | Lightweight `{unread_count}` for the global bell |
| `POST` | `/notifications/{id}/read` | Idempotently mark an owned notification read |

List pagination uses `offset` (default 0, nonnegative) and `limit` (default 20,
1-50). Each notification contains `id`, `category`, `event_type`, `resource_id`,
`target_path`, `message`, `is_read`, and UTC `created_at`. Unread count covers
all the current member's notifications, not just the current page.
Carpool and ride events both use this shared API. The former carpool-only inbox
API endpoints have been removed.

The original ride-request list endpoints accept `offset` (default 0) and `limit` (default 20, maximum
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
