export interface User {
  id: number;
  email: string;
  name: string;
  picture?: string | null;
  provider?: string;
}

export interface Post {
  id: number;
  title: string;
  description: string;
  category: string;
  city: string;
  user_id: number;
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
