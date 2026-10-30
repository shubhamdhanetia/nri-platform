"use client";

import { useEffect, useState, type FormEvent } from "react";
import { apiRequest, type Comment } from "../lib/api";
import { getEditWindowRemainingMs, isWithinEditWindow } from "../lib/edit-window";

export default function CommentActions({
  comment,
  onUpdated,
  onDeleted,
}: {
  comment: Comment;
  onUpdated: (comment: Comment) => void;
  onDeleted: (commentId: string) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [content, setContent] = useState(comment.content);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState("");
  const [canEdit, setCanEdit] = useState(() => isWithinEditWindow(comment.created_at));

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setCanEdit(false);
      setEditing(false);
    }, getEditWindowRemainingMs(comment.created_at));
    return () => window.clearTimeout(timer);
  }, [comment.created_at]);

  async function saveEdit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError("");
    try {
      const updatedComment = await apiRequest<Comment>(
        `/posts/${comment.post_id}/comments/${comment.id}`,
        {
          method: "PUT",
          body: JSON.stringify({ content }),
        },
      );
      onUpdated(updatedComment);
      setEditing(false);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to update your comment.");
    } finally {
      setSaving(false);
    }
  }

  async function removeComment() {
    if (!window.confirm("Delete your comment? This action cannot be undone.")) {
      return;
    }
    setDeleting(true);
    setError("");
    try {
      await apiRequest<{ detail: string }>(
        `/posts/${comment.post_id}/comments/${comment.id}`,
        { method: "DELETE" },
      );
      onDeleted(comment.id);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to delete your comment.");
      setDeleting(false);
    }
  }

  if (editing) {
    return (
      <form className="comment-edit-form" onSubmit={saveEdit}>
        <label className="form-field">
          <span>Edit your comment</span>
          <textarea
            maxLength={2000}
            onChange={(event) => setContent(event.target.value)}
            required
            rows={3}
            value={content}
          />
        </label>
        {error && <p className="form-error" role="alert">{error}</p>}
        <div className="comment-action-buttons">
          <button className="button button-primary" disabled={saving || !content.trim()} type="submit">
            {saving ? "Saving…" : "Save"}
          </button>
          <button
            className="button button-quiet"
            disabled={saving}
            onClick={() => {
              setContent(comment.content);
              setEditing(false);
              setError("");
            }}
            type="button"
          >
            Cancel
          </button>
        </div>
      </form>
    );
  }

  return (
    <div className="comment-owner-actions">
      {error && <p className="form-error" role="alert">{error}</p>}
      {canEdit && (
        <button
          className="comment-action-button"
          disabled={deleting}
          onClick={() => {
            setContent(comment.content);
            setEditing(true);
            setError("");
          }}
          type="button"
        >
          Edit
        </button>
      )}
      <button
        className="comment-action-button comment-delete-action"
        disabled={deleting}
        onClick={() => void removeComment()}
        type="button"
      >
        {deleting ? "Deleting…" : "Delete"}
      </button>
    </div>
  );
}
