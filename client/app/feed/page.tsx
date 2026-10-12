"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import ProtectedPage from "../../components/ProtectedPage";
import DeletePostButton from "../../components/DeletePostButton";
import EditPostButton from "../../components/EditPostButton";
import PostReactions from "../../components/PostReactions";
import SavePostButton from "../../components/SavePostButton";
import {
  apiRequest,
  POST_CATEGORY_LABELS,
  POST_TYPE_LABELS,
  type Post,
  type PostReactionSummary,
  type User,
} from "../../lib/api";

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

  function updatePost(updatedPost: Post) {
    setPosts((currentPosts) => currentPosts.map(
      (post) => post.id === updatedPost.id ? updatedPost : post,
    ));
  }

  function updatePostReactions(summary: PostReactionSummary) {
    setPosts((currentPosts) => currentPosts.map((post) => (
      post.id === summary.post_id
        ? {
          ...post,
          like_count: summary.like_count,
          dislike_count: summary.dislike_count,
          my_reaction: summary.my_reaction,
        }
        : post
    )));
  }

  function updatePostSaved(postId: number, isSaved: boolean) {
    setPosts((currentPosts) => currentPosts.map((post) => (
      post.id === postId ? { ...post, my_saved: isSaved } : post
    )));
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
                <div className="post-badges">
                  <span className="category-pill">{POST_CATEGORY_LABELS[post.category]}</span>
                  <span className={`post-type-pill post-type-${post.post_type.toLowerCase()}`}>
                    {POST_TYPE_LABELS[post.post_type]}
                  </span>
                  {post.updated_at && <span className="edited-indicator">Edited</span>}
                </div>
                <span className="post-location"><span aria-hidden="true">⌖</span> {post.location}</span>
              </div>
              <h2><Link href={`/posts/${post.id}`}>{post.title}</Link></h2>
              <p className="post-description">{post.description}</p>
              <div className="post-author">
                <span className="author-avatar">N</span>
                <span>Community member</span>
                <PostReactions
                  canReact={post.user_id !== currentUserId}
                  dislikeCount={post.dislike_count}
                  likeCount={post.like_count}
                  myReaction={post.my_reaction}
                  onChanged={updatePostReactions}
                  postId={post.id}
                />
                <SavePostButton
                  isSaved={post.my_saved}
                  onChanged={(isSaved) => updatePostSaved(post.id, isSaved)}
                  postId={post.id}
                />
                <Link className="comment-count-link" href={`/posts/${post.id}`}>
                  {post.comment_count} {post.comment_count === 1 ? "comment" : "comments"}
                </Link>
                {post.user_id === currentUserId && (
                  <div className="post-owner-actions">
                    <EditPostButton onUpdated={updatePost} post={post} />
                    <DeletePostButton onDeleted={removePost} postId={post.id} />
                  </div>
                )}
              </div>
            </article>
          ))}
        </section>
      )}
    </ProtectedPage>
  );
}
