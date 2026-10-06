"use client";

import { useState } from "react";
import { apiRequest } from "../lib/api";

export default function DeletePostButton({
  postId,
  onDeleted,
}: {
  postId: number;
  onDeleted: (postId: number) => void;
}) {
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState("");

  async function handleDelete() {
    if (!window.confirm("Delete this post? This action cannot be undone.")) {
      return;
    }

    setDeleting(true);
    setError("");
    try {
      await apiRequest<{ detail: string }>(`/posts/${postId}`, {
        method: "DELETE",
      });
      onDeleted(postId);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to delete this post.");
    } finally {
      setDeleting(false);
    }
  }

  return (
    <div className="post-delete-control">
      <button
        className="delete-post-button"
        disabled={deleting}
        onClick={() => void handleDelete()}
        type="button"
      >
        {deleting ? "Deleting…" : "Delete"}
      </button>
      {error && <p className="form-error" role="alert">{error}</p>}
    </div>
  );
}
