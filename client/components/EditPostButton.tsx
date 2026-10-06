"use client";

import { useState } from "react";
import EditPostForm from "./EditPostForm";
import type { Post } from "../lib/api";

export default function EditPostButton({
  post,
  onUpdated,
}: {
  post: Post;
  onUpdated: (post: Post) => void;
}) {
  const [editing, setEditing] = useState(false);

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
