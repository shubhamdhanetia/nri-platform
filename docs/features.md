Architecture

Flow 1 (WORKING) - login with Google, create user, return JWT access token to frontend from backend.

User
  ↓
Google Login
  ↓
Google Credential
  ↓
FastAPI /auth/google
  ↓
Verify token
  ↓
Create User if needed
  ↓
Issue NRI Platform JWT
  ↓
Store JWT
  ↓
Redirect to /feed






Commands needed to run this project.

How to run backend => go to the backend folder in terminal -> uvicorn app.main:app --reload

How to run frontend => npm run dev

Google OAuth keys

339379291313-6opn25dfthhgkuqldm5mmbbp6g4u5kcn.apps.googleusercontent.com
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



















Housing - Looking for roommate in Sunnyvale
Ride - Need ride from SFO to Fremont Sunday evening
Food - Gujarati tiffin available in Santa Clara
Job - Looking for referral at Microsoft
Event - Garba Event this Saturday
Visa - Need advice on H1B renewal stamping

Dating/Matrimony
Travel with strangers




Post categories

HOUSING
RIDES
JOBS
FOOD
EVENTS
IMMIGRATION
MARKETPLACE
GENERAL

Post types

OFFER
REQUEST
DISCUSSION

Every post has one category and one type. For example, a room available is
HOUSING + OFFER, while looking for a roommate is HOUSING + REQUEST.
Use DISCUSSION for open-ended posts that are neither an offer nor a request.


Version 1

✅ Google Login
✅ Profile
✅ Feed
✅ Categories
✅ Create Post
✅ Search Posts
✅ Direct Message



=======MVP Screens=========





========API==============

POST /auth/google

GET /users/me

PATCH /users/me

POST /posts
GET /posts
GET /posts/{id}
PUT /posts/{id}
DELETE /posts/{id}
PUT /posts/{id}/reaction
DELETE /posts/{id}/reaction
GET /posts/{id}/comments
POST /posts/{id}/comments
PUT /posts/{id}/comments/{comment_id}
DELETE /posts/{id}/comments/{comment_id}
POST /locations/search
POST /locations/details

All post and comment endpoints require a valid JWT, except `POST /auth/google`
which issues the JWT used for subsequent API requests.
`POST /locations/search` is public and forwards a validated latitude,
longitude, query, and pickup type to Uber's location search endpoint. The
pickup type defaults to `PICKUP` when omitted.
`POST /locations/details` is public and forwards a selected Uber place ID,
locale, provider, and type to Uber's place details endpoint. The provider
defaults to `uber_places`, locale to `en`, and type to lowercase `pickup`.
The Explore page uses these endpoints to suggest locations near the current map
center and to center the map on the selected place. It also requests browser
geolocation on page load; if access is unavailable or denied, it keeps the
default map view.
Post create and edit requests accept the selected `location_id`; the backend
resolves the place details and stores its full address, coordinates, country
code, postal code, state, city, and H3 cell ID at resolution 8.

`POST /posts/search` requires authentication and accepts map viewport bounds
plus a result limit of at most 50. It uses a conservative H3 resolution-8
bounding-box cover to find candidate posts, then filters by exact coordinates
and returns newest posts with a `has_more` indicator. The optional `category`
filter narrows results to a single post category; omitting it searches all
categories. Oversized map searches are rejected with a request to zoom in.

Search request:

```json
{
  "bounds": {
    "north": 37.8,
    "east": -122.3,
    "south": 37.6,
    "west": -122.5
  },
  "limit": 50,
  "category": "HOUSING"
}
```

The response contains `posts` and `has_more`; when `has_more` is true, users
should zoom in to narrow the map area. Omit `category` or pass `null` to search
all categories.

Authenticated users can like or dislike another user's post. Each user can
have one reaction per post; setting the other reaction switches it, and
deleting the reaction removes it. Post owners cannot react to their own posts.

Post and comment authors may edit their content during the first 30 minutes
after creation. The backend enforces this limit; deletion permissions are
unchanged.
Edited posts and comments expose an `updated_at` timestamp and display an
“Edited” indicator.


POST /conversations

GET /conversations

POST /messages

/feed
/profile
/create-post
/posts/[id]




======DATABASE=========

Users table

id
name
email
picture
city


posts table

id
user_id
title
description
category
post_type
city
location_id
location
country_code
postal_code
state
latitude
longitude
h3_cell_id
created_at
updated_at

comments table

id
post_id
user_id
content









Backend side 

User table
JWT
Refresh tokens
Middleware
Guards
Session management






Collaborate with tech influences in California for marketing







Docker commmands


docker compose up -d
docker exec -it nri-postgres psql -U postgres -d nri_platform