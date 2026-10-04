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




Categories for post feature

ROOMMATE
HOUSING
RIDE
FOOD
EVENT
JOB
VISA
GENERAL


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

DELETE /posts/{id}


POST /conversations

GET /conversations

POST /messages

/feed
/profile
/create-post




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
city
created_at

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
