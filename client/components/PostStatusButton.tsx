"use client";

import { useState } from "react";
import { apiRequest, type Post } from "../lib/api";

export default function PostStatusButton({ post, onChanged }: {
  post: Post;
  onChanged: (post: Post) => void;
}) {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");

  if (post.post_type === "DISCUSSION") return null;

  async function toggleStatus() {
    setPending(true);
    setError("");
    try {
      const updated = await apiRequest<Post>(`/posts/${post.id}/status`, {
        method: "PUT",
        body: JSON.stringify({ status: post.status === "CLOSED" ? "ACTIVE" : "CLOSED" }),
      });
      onChanged(updated);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to update post status.");
    } finally {
      setPending(false);
    }
  }

  return <span className="post-visibility-control">
    <button className="edit-post-button" type="button" disabled={pending}
      aria-busy={pending} onClick={() => void toggleStatus()}>
      {pending ? "Updating..." : post.status === "CLOSED" ? "Reopen"
        : post.post_type === "REQUEST" ? "Mark resolved" : "Mark unavailable"}
    </button>
    {error && <span className="post-visibility-error" role="alert">{error}</span>}
  </span>;
}
