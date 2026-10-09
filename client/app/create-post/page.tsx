"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import ProtectedPage from "../../components/ProtectedPage";
import LocationAutocomplete from "../../components/LocationAutocomplete";
import {
  apiRequest,
  POST_CATEGORIES,
  POST_CATEGORY_LABELS,
  POST_TYPES,
  POST_TYPE_LABELS,
  type Post,
  type PostCategory,
  type PostType,
} from "../../lib/api";

function isPostCategory(value: string): value is PostCategory {
  return POST_CATEGORIES.some((category) => category === value);
}

function isPostType(value: string): value is PostType {
  return POST_TYPES.some((postType) => postType === value);
}

export default function CreatePostPage() {
  const router = useRouter();
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState<PostCategory | "">("");
  const [postType, setPostType] = useState<PostType | "">("");
  const [selectedLocation, setSelectedLocation] = useState<{
    locationId: string;
    location: string;
  } | null>(null);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedLocation) {
      setError("Select a suggested location before publishing.");
      return;
    }
    setError("");
    setSubmitting(true);
    try {
      await apiRequest<Post>("/posts", {
        method: "POST",
        body: JSON.stringify({
          title,
          description,
          category,
          post_type: postType,
          location_id: selectedLocation.locationId,
        }),
      });
      router.push("/feed");
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to create your post.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <ProtectedPage>
      <section className="page-heading">
        <div>
          <p className="eyebrow">Make a connection</p>
          <h1>Create a post</h1>
          <p className="muted">Share a recommendation, ask a question, or let the community know what’s on your mind.</p>
        </div>
      </section>

      <form className="form-card" onSubmit={handleSubmit}>
        <label className="form-field">
          <span>Post title</span>
          <input
            autoComplete="off"
            maxLength={140}
            onChange={(event) => setTitle(event.target.value)}
            placeholder="Give your post a clear title"
            required
            value={title}
          />
        </label>
        <label className="form-field">
          <span>Your post</span>
          <textarea
            maxLength={5000}
            onChange={(event) => setDescription(event.target.value)}
            placeholder="What would you like to share with the community?"
            required
            rows={7}
            value={description}
          />
        </label>
        <div className="form-row">
          <label className="form-field">
            <span>Category</span>
            <select
              onChange={(event) => {
                const value = event.target.value;
                setCategory(isPostCategory(value) ? value : "");
              }}
              required
              value={category}
            >
              <option disabled value="">Choose a category</option>
              {POST_CATEGORIES.map((value) => (
                <option key={value} value={value}>{POST_CATEGORY_LABELS[value]}</option>
              ))}
            </select>
          </label>
          <label className="form-field">
            <span>Post type</span>
            <select
              onChange={(event) => {
                const value = event.target.value;
                setPostType(isPostType(value) ? value : "");
              }}
              required
              value={postType}
            >
              <option disabled value="">Choose a post type</option>
              {POST_TYPES.map((value) => (
                <option key={value} value={value}>{POST_TYPE_LABELS[value]}</option>
              ))}
            </select>
          </label>
        </div>
        <LocationAutocomplete onAddressSelected={setSelectedLocation} />
        {error && <p className="form-error" role="alert">{error}</p>}
        <div className="form-actions">
          <button
            className="button button-primary"
            disabled={submitting}
            type="submit"
          >
            {submitting ? "Publishing…" : "Publish post"}
          </button>
          <button className="button button-quiet" onClick={() => router.push("/feed")} type="button">
            Cancel
          </button>
        </div>
      </form>
    </ProtectedPage>
  );
}
