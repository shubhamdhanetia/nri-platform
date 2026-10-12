"use client";

import { useState } from "react";
import { apiRequest } from "../lib/api";

export default function SavePostButton({
  postId,
  isSaved,
  onChanged,
}: {
  postId: number;
  isSaved: boolean;
  onChanged?: (isSaved: boolean) => void;
}) {
  const [saved, setSaved] = useState(isSaved);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");

  async function toggleSaved() {
    setPending(true);
    setError("");
    try {
      const response = await apiRequest<{ post_id: number; is_saved: boolean }>(
        `/posts/${postId}/save`,
        { method: saved ? "DELETE" : "POST" },
      );
      setSaved(response.is_saved);
      onChanged?.(response.is_saved);
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Unable to update saved post.",
      );
    } finally {
      setPending(false);
    }
  }

  return (
    <span className="save-post-control">
      <button
        aria-label={saved ? "Remove from saved posts" : "Save post"}
        aria-busy={pending}
        aria-pressed={saved}
        className={saved ? "save-post-button is-saved" : "save-post-button"}
        disabled={pending}
        onClick={() => void toggleSaved()}
        title={pending ? "Saving post…" : saved ? "Remove from saved posts" : "Save post"}
        type="button"
      >
        <svg aria-hidden="true" fill={saved ? "currentColor" : "none"} viewBox="0 0 20 20">
          <path d="M5 3.75h10v13l-5-3.25-5 3.25v-13Z" />
        </svg>
      </button>
      {error && <span className="save-post-error" role="alert">{error}</span>}
    </span>
  );
}
