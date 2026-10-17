"use client";

import { useState } from "react";
import { apiRequest, type Post } from "../lib/api";

export default function PostVisibilityButton({
  post,
  onChanged,
}: {
  post: Post;
  onChanged: (post: Post) => void;
}) {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");

  async function toggleVisibility() {
    setPending(true);
    setError("");
    try {
      const updatedPost = await apiRequest<Post>(`/posts/${post.id}/visibility`, {
        method: "PUT",
        body: JSON.stringify({ is_private: !post.is_private }),
      });
      onChanged(updatedPost);
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Unable to update post visibility.",
      );
    } finally {
      setPending(false);
    }
  }

  return (
    <span className="post-visibility-control">
      <button
        aria-busy={pending}
        aria-pressed={post.is_private}
        className="edit-post-button"
        disabled={pending}
        onClick={() => void toggleVisibility()}
        type="button"
      >
        {pending
          ? "Updating…"
          : post.is_private
            ? "Make public"
            : "Make private"}
      </button>
      {error && <span className="post-visibility-error" role="alert">{error}</span>}
    </span>
  );
}
