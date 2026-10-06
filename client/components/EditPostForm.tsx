"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import {
  apiRequest,
  POST_CATEGORIES,
  POST_CATEGORY_LABELS,
  POST_TYPES,
  POST_TYPE_LABELS,
  type Post,
  type PostCategory,
  type PostType,
} from "../lib/api";

function isPostCategory(value: string): value is PostCategory {
  return POST_CATEGORIES.some((category) => category === value);
}

function isPostType(value: string): value is PostType {
  return POST_TYPES.some((postType) => postType === value);
}

export default function EditPostForm({
  post,
  onUpdated,
  onCancel,
}: {
  post: Post;
  onUpdated: (post: Post) => void;
  onCancel: () => void;
}) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const [title, setTitle] = useState(post.title);
  const [description, setDescription] = useState(post.description);
  const [category, setCategory] = useState<PostCategory>(post.category);
  const [postType, setPostType] = useState<PostType>(post.post_type);
  const [city, setCity] = useState(post.city);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;

    dialog.showModal();
    return () => dialog.close();
  }, []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setSaving(true);
    try {
      const updatedPost = await apiRequest<Post>(`/posts/${post.id}`, {
        method: "PUT",
        body: JSON.stringify({
          title,
          description,
          category,
          post_type: postType,
          city,
        }),
      });
      onUpdated(updatedPost);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to update your post.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <dialog
      aria-labelledby="edit-post-title"
      className="edit-post-dialog"
      onCancel={(event) => {
        event.preventDefault();
        onCancel();
      }}
      ref={dialogRef}
    >
      <div className="edit-dialog-header">
        <div>
          <p className="eyebrow">Your post</p>
          <h2 id="edit-post-title">Edit post</h2>
        </div>
        <button
          aria-label="Close edit dialog"
          className="dialog-close-button"
          disabled={saving}
          onClick={onCancel}
          type="button"
        >
          ×
        </button>
      </div>
      <form className="edit-post-form" onSubmit={handleSubmit}>
        <div className="edit-fields-grid">
          <label className="form-field">
            <span>Post title</span>
            <input
              maxLength={255}
              onChange={(event) => setTitle(event.target.value)}
              required
              value={title}
            />
          </label>
          <label className="form-field">
            <span>City</span>
            <input
              autoComplete="address-level2"
              maxLength={100}
              onChange={(event) => setCity(event.target.value)}
              required
              value={city}
            />
          </label>
          <label className="form-field">
            <span>Category</span>
            <select
              onChange={(event) => {
                if (isPostCategory(event.target.value)) {
                  setCategory(event.target.value);
                }
              }}
              required
              value={category}
            >
              {POST_CATEGORIES.map((value) => (
                <option key={value} value={value}>{POST_CATEGORY_LABELS[value]}</option>
              ))}
            </select>
          </label>
          <label className="form-field">
            <span>Post type</span>
            <select
              onChange={(event) => {
                if (isPostType(event.target.value)) {
                  setPostType(event.target.value);
                }
              }}
              required
              value={postType}
            >
              {POST_TYPES.map((value) => (
                <option key={value} value={value}>{POST_TYPE_LABELS[value]}</option>
              ))}
            </select>
          </label>
          <label className="form-field edit-description-field">
            <span>Description</span>
            <textarea
              onChange={(event) => setDescription(event.target.value)}
              required
              rows={5}
              value={description}
            />
          </label>
        </div>
        {error && <p className="form-error" role="alert">{error}</p>}
        <div className="form-actions">
          <button className="button button-primary" disabled={saving} type="submit">
            {saving ? "Saving…" : "Save changes"}
          </button>
          <button className="button button-quiet" disabled={saving} onClick={onCancel} type="button">
            Cancel
          </button>
        </div>
      </form>
    </dialog>
  );
}
