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
            aria-label={summary.my_reaction === "LIKE"
              ? `Remove like, ${summary.like_count} ${summary.like_count === 1 ? "like" : "likes"}`
              : `Like, ${summary.like_count} ${summary.like_count === 1 ? "like" : "likes"}`}
            aria-pressed={summary.my_reaction === "LIKE"}
            className={`post-reaction-button${summary.my_reaction === "LIKE" ? " is-selected" : ""}`}
            disabled={pending}
            onClick={() => void react("LIKE")}
            title={summary.my_reaction === "LIKE" ? "Remove like" : "Like"}
            type="button"
          >
            <span aria-hidden="true">👍</span>
            <span>{summary.like_count}</span>
          </button>
          <button
            aria-label={summary.my_reaction === "DISLIKE"
              ? `Remove dislike, ${summary.dislike_count} ${summary.dislike_count === 1 ? "dislike" : "dislikes"}`
              : `Dislike, ${summary.dislike_count} ${summary.dislike_count === 1 ? "dislike" : "dislikes"}`}
            aria-pressed={summary.my_reaction === "DISLIKE"}
            className={`post-reaction-button${summary.my_reaction === "DISLIKE" ? " is-selected" : ""}`}
            disabled={pending}
            onClick={() => void react("DISLIKE")}
            title={summary.my_reaction === "DISLIKE" ? "Remove dislike" : "Dislike"}
            type="button"
          >
            <span aria-hidden="true">👎</span>
            <span>{summary.dislike_count}</span>
          </button>
        </>
      ) : (
        <>
          <span
            aria-label={`${summary.like_count} ${summary.like_count === 1 ? "like" : "likes"}. You cannot react to your own post.`}
            className="post-reaction-count is-disabled"
            role="img"
            title="You cannot react to your own post"
          >
            <span aria-hidden="true">👍</span>
            <span aria-hidden="true">{summary.like_count}</span>
          </span>
          <span
            aria-label={`${summary.dislike_count} ${summary.dislike_count === 1 ? "dislike" : "dislikes"}. You cannot react to your own post.`}
            className="post-reaction-count is-disabled"
            role="img"
            title="You cannot react to your own post"
          >
            <span aria-hidden="true">👎</span>
            <span aria-hidden="true">{summary.dislike_count}</span>
          </span>
        </>
      )}
      {error && <span className="post-reaction-error" role="alert">{error}</span>}
    </div>
  );
}
