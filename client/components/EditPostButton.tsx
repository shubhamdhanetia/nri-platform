"use client";

import { useEffect, useState } from "react";
import EditPostForm from "./EditPostForm";
import type { Post } from "../lib/api";

import { getEditWindowRemainingMs, isWithinEditWindow } from "../lib/edit-window";

export default function EditPostButton({
  post,
  onUpdated,
}: {
  post: Post;
  onUpdated: (post: Post) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [canEdit, setCanEdit] = useState(() => isWithinEditWindow(post.created_at));

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setCanEdit(false);
      setEditing(false);
    }, getEditWindowRemainingMs(post.created_at));
    return () => window.clearTimeout(timer);
  }, [post.created_at]);

  if (!canEdit) {
    return null;
  }

  return (
    <>
      <button
        className="edit-post-button"
        onClick={() => setEditing(true)}
        type="button"
      >
        Edit
      </button>
      {editing && (
        <EditPostForm
          onCancel={() => setEditing(false)}
          onUpdated={(updatedPost) => {
            onUpdated(updatedPost);
            setEditing(false);
          }}
          post={post}
        />
      )}
    </>
  );
}
