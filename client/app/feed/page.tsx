"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import ProtectedPage from "../../components/ProtectedPage";
import DeletePostButton from "../../components/DeletePostButton";
import { apiRequest, type Post, type User } from "../../lib/api";

export default function FeedPage() {
  const [posts, setPosts] = useState<Post[]>([]);
  const [currentUserId, setCurrentUserId] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const fetchFeed = useCallback(
    () => Promise.all([
      apiRequest<Post[]>("/posts"),
      apiRequest<User>("/users/me"),
    ]),
    [],
  );

  useEffect(() => {
    let active = true;
    fetchFeed()
      .then(([data, user]) => {
        if (active) {
          setPosts(data);
          setCurrentUserId(user.id);
        }
      })
      .catch((requestError: unknown) => {
        if (active) {
          setError(requestError instanceof Error ? requestError.message : "Unable to load posts.");
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [fetchFeed]);

  async function retryLoadPosts() {
    setLoading(true);
    setError("");
    try {
      const [data, user] = await fetchFeed();
      setPosts(data);
      setCurrentUserId(user.id);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to load posts.");
    } finally {
      setLoading(false);
    }
  }

  function removePost(postId: number) {
    setPosts((currentPosts) => currentPosts.filter((post) => post.id !== postId));
  }

  return (
    <ProtectedPage>
      <section className="page-heading">
        <div>
          <p className="eyebrow">The community</p>
          <h1>What’s happening</h1>
          <p className="muted">Ideas, recommendations, and conversations from your community.</p>
        </div>
        <Link className="button button-primary" href="/create-post">
          <span aria-hidden="true">＋</span> Share something
        </Link>
      </section>

      {loading ? (
        <div className="state-card"><span className="spinner" /> Loading posts…</div>
      ) : error ? (
        <div className="state-card error-state" role="alert">
          <p>{error}</p>
          <button className="button button-secondary" onClick={() => void retryLoadPosts()} type="button">
            Try again
          </button>
        </div>
      ) : posts.length === 0 ? (
        <div className="empty-state">
          <span className="empty-icon">✦</span>
          <h2>It’s quiet around here</h2>
          <p className="muted">Be the first to share a tip or start a conversation.</p>
          <Link className="button button-primary" href="/create-post">Create the first post</Link>
        </div>
      ) : (
        <section className="post-grid" aria-label="Community posts">
          {posts.map((post) => (
            <article className="post-card" key={post.id}>
              <div className="post-meta">
                <span className="category-pill">{post.category}</span>
                <span className="post-location"><span aria-hidden="true">⌖</span> {post.city}</span>
              </div>
              <h2>{post.title}</h2>
              <p className="post-description">{post.description}</p>
              <div className="post-author">
                <span className="author-avatar">N</span>
                <span>Community member</span>
                {post.user_id === currentUserId && (
                  <DeletePostButton onDeleted={removePost} postId={post.id} />
                )}
              </div>
            </article>
          ))}
        </section>
      )}
    </ProtectedPage>
  );
}
