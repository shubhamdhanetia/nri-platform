"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import ProtectedPage from "../../components/ProtectedPage";
import SavePostButton from "../../components/SavePostButton";
import {
  apiRequest,
  POST_CATEGORY_LABELS,
  POST_TYPE_LABELS,
  type Post,
} from "../../lib/api";

export default function SavedPostsPage() {
  const [posts, setPosts] = useState<Post[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    apiRequest<Post[]>("/posts/saved")
      .then((savedPosts) => {
        if (active) setPosts(savedPosts);
      })
      .catch((requestError: unknown) => {
        if (active) {
          setError(
            requestError instanceof Error
              ? requestError.message
              : "Unable to load saved posts.",
          );
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, []);

  const retryLoadSavedPosts = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setPosts(await apiRequest<Post[]>("/posts/saved"));
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Unable to load saved posts.",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  function removeSavedPost(postId: number, isSaved: boolean) {
    if (!isSaved) {
      setPosts((currentPosts) => currentPosts.filter((post) => post.id !== postId));
    }
  }

  return (
    <ProtectedPage>
      <section className="page-heading">
        <div>
          <p className="eyebrow">Your reading list</p>
          <h1>Saved posts</h1>
          <p className="muted">Posts you’ve saved for later.</p>
        </div>
      </section>

      {loading ? (
        <div className="state-card"><span className="spinner" /> Loading saved posts…</div>
      ) : error ? (
        <div className="state-card error-state" role="alert">
          <p>{error}</p>
          <button
            className="button button-secondary"
            onClick={() => void retryLoadSavedPosts()}
            type="button"
          >
            Try again
          </button>
        </div>
      ) : posts.length === 0 ? (
        <div className="empty-state">
          <span className="empty-icon" aria-hidden="true">▱</span>
          <h2>No saved posts yet</h2>
          <p className="muted">Save posts that you want to come back to later.</p>
          <Link className="button button-primary" href="/feed">Browse the feed</Link>
        </div>
      ) : (
        <section className="post-grid" aria-label="Saved posts">
          {posts.map((post) => (
            <article className="post-card" key={post.id}>
              <div className="post-meta">
                <div className="post-badges">
                  <span className="category-pill">{POST_CATEGORY_LABELS[post.category]}</span>
                  <span className={`post-type-pill post-type-${post.post_type.toLowerCase()}`}>
                    {POST_TYPE_LABELS[post.post_type]}
                  </span>
                </div>
                <span className="post-location">
                  <span aria-hidden="true">⌖</span> {post.location}
                </span>
              </div>
              <h2><Link href={`/posts/${post.id}`}>{post.title}</Link></h2>
              <p className="post-description">{post.description}</p>
              <div className="saved-post-actions">
                <Link className="text-link" href={`/posts/${post.id}`}>View post</Link>
                <SavePostButton
                  isSaved={post.my_saved}
                  onChanged={(isSaved) => removeSavedPost(post.id, isSaved)}
                  postId={post.id}
                />
              </div>
            </article>
          ))}
        </section>
      )}
    </ProtectedPage>
  );
}
