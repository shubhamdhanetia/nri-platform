# NRI Platform client

The client is a Next.js app that supports the MVP community flow:

- `/login` — sign in with Google
- `/feed` — browse community posts
- `/create-post` — publish a post with a title, description, category, and city
- `/profile` — view the signed-in user and their posts

## Local setup

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
