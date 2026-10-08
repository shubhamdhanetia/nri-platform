export interface User {
  id: number;
  email: string;
  name: string;
  picture?: string | null;
  provider?: string;
}

export const POST_CATEGORIES = [
  "HOUSING",
  "RIDES",
  "JOBS",
  "FOOD",
  "EVENTS",
  "IMMIGRATION",
  "MARKETPLACE",
  "GENERAL",
] as const;

export const POST_TYPES = ["OFFER", "REQUEST", "DISCUSSION"] as const;

export type PostCategory = (typeof POST_CATEGORIES)[number];
export type PostType = (typeof POST_TYPES)[number];
export type PostReactionType = "LIKE" | "DISLIKE";

export const POST_CATEGORY_LABELS: Record<PostCategory, string> = {
  HOUSING: "Housing",
  RIDES: "Rides",
  JOBS: "Jobs",
  FOOD: "Food",
  EVENTS: "Events",
  IMMIGRATION: "Immigration & visa",
  MARKETPLACE: "Marketplace",
  GENERAL: "General",
};

export const POST_TYPE_LABELS: Record<PostType, string> = {
  OFFER: "Offering",
  REQUEST: "Looking for",
  DISCUSSION: "Discussion",
};

export interface Post {
  id: number;
  created_at: string;
  updated_at: string | null;
  title: string;
  description: string;
  category: PostCategory;
  post_type: PostType;
  city: string;
  user_id: number;
  comment_count: number;
  like_count: number;
  dislike_count: number;
  my_reaction: PostReactionType | null;
}

export interface PostReactionSummary {
  post_id: number;
  like_count: number;
  dislike_count: number;
  my_reaction: PostReactionType | null;
}

export interface PostAuthor {
  id: number;
  name: string;
  picture: string | null;
}

export interface PostDetail extends Post {
  created_at: string;
  author: PostAuthor;
}

export interface Comment {
  id: number;
  content: string;
  user_id: number;
  post_id: number;
  created_at: string;
  updated_at: string | null;
  author: PostAuthor;
}

export interface LoginResponse {
  access_token: string;
  user: Pick<User, "id" | "email" | "name">;
}

const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000")
  .replace(/\/$/, "");

export async function apiRequest<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const token = typeof window === "undefined"
    ? null
    : window.localStorage.getItem("access_token");
  const headers = new Headers(options.headers);

  if (options.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const responseText = await response.text();
    let message = responseText || `Request failed (${response.status})`;

    if (responseText) {
      try {
        const payload: { detail?: string } = JSON.parse(responseText);
        if (payload.detail) {
          message = payload.detail;
        }
      } catch {
        // Keep the response text when the server does not return JSON.
      }
    }

    throw new Error(message);
  }

  return response.json() as Promise<T>;
}
