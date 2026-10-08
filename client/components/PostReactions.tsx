"use client";

import { useState } from "react";
import {
  apiRequest,
  type PostReactionSummary,
  type PostReactionType,
} from "../lib/api";

export default function PostReactions({
  postId,
  likeCount,
  dislikeCount,
  myReaction,
  canReact,
  onChanged,
}: {
  postId: number;
  likeCount: number;
  dislikeCount: number;
  myReaction: PostReactionType | null;
  canReact: boolean;
  onChanged: (summary: PostReactionSummary) => void;
}) {
  const summary: PostReactionSummary = {
    post_id: postId,
    like_count: likeCount,
    dislike_count: dislikeCount,
    my_reaction: myReaction,
  };
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");

  async function react(reaction: PostReactionType) {
    setPending(true);
    setError("");
    try {
      const updated = summary.my_reaction === reaction
        ? await apiRequest<PostReactionSummary>(`/posts/${postId}/reaction`, {
          method: "DELETE",
        })
        : await apiRequest<PostReactionSummary>(`/posts/${postId}/reaction`, {
          method: "PUT",
          body: JSON.stringify({ reaction }),
        });
      onChanged(updated);
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Unable to update your reaction.",
      );
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="post-reactions">
      {canReact ? (
        <>
          <button
            aria-pressed={summary.my_reaction === "LIKE"}
            className={`post-reaction-button${summary.my_reaction === "LIKE" ? " is-selected" : ""}`}
            disabled={pending}
            onClick={() => void react("LIKE")}
            type="button"
          >
            <span aria-hidden="true">👍</span> Like <span>{summary.like_count}</span>
          </button>
          <button
            aria-pressed={summary.my_reaction === "DISLIKE"}
            className={`post-reaction-button${summary.my_reaction === "DISLIKE" ? " is-selected" : ""}`}
            disabled={pending}
            onClick={() => void react("DISLIKE")}
            type="button"
          >
            <span aria-hidden="true">👎</span> Dislike <span>{summary.dislike_count}</span>
          </button>
        </>
      ) : (
        <>
          <span className="post-reaction-count"><span aria-hidden="true">👍</span> {summary.like_count}</span>
          <span className="post-reaction-count"><span aria-hidden="true">👎</span> {summary.dislike_count}</span>
        </>
      )}
      {error && <span className="post-reaction-error" role="alert">{error}</span>}
    </div>
  );
}
