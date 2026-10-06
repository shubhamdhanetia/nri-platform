"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import ProtectedPage from "../../components/ProtectedPage";
import { apiRequest, type Post } from "../../lib/api";

export default function CreatePostPage() {
  const router = useRouter();
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState("");
  const [city, setCity] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await apiRequest<Post>("/posts", {
        method: "POST",
        body: JSON.stringify({ title, description, category, city }),
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
            <input
              onChange={(event) => setCategory(event.target.value)}
              placeholder="e.g. Recommendations"
              required
              value={category}
            />
          </label>
          <label className="form-field">
            <span>City</span>
            <input
              autoComplete="address-level2"
              onChange={(event) => setCity(event.target.value)}
              placeholder="e.g. Toronto"
              required
              value={city}
            />
          </label>
        </div>
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
