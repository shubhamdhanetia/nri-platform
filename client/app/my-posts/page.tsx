"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowRight, FileText } from "lucide-react";
import ProtectedPage from "../../components/ProtectedPage";
import DeletePostButton from "../../components/DeletePostButton";
import EditPostButton from "../../components/EditPostButton";
import PostReactions from "../../components/PostReactions";
import PostVisibilityButton from "../../components/PostVisibilityButton";
import {
  apiRequest,
  POST_CATEGORY_LABELS,
  POST_TYPE_LABELS,
  type Post,
  type PostReactionSummary,
} from "../../lib/api";

export default function MyPostsPage() {
  const [posts, setPosts] = useState<Post[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    apiRequest<Post[]>("/posts/me")
      .then((userPosts) => {
        if (active) setPosts(userPosts);
      })
      .catch((requestError: unknown) => {
        if (active) {
          setError(requestError instanceof Error ? requestError.message : "Unable to load your posts.");
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  async function retryLoadPosts() {
    setLoading(true);
    setError("");
    try {
      setPosts(await apiRequest<Post[]>("/posts/me"));
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to load your posts.");
    } finally {
      setLoading(false);
    }
  }

  function removePost(postId: string) {
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

  return (
    <ProtectedPage>
      <section className="page-heading">
        <div>
          <p className="eyebrow">Your contributions</p>
          <h1>My posts {!loading && !error && <span className="count-pill">{posts.length}</span>}</h1>
        </div>
        <Link className="button button-secondary" href="/create-post">Write a post <ArrowRight size={16} aria-hidden="true" /></Link>
      </section>
      {loading ? (
        <div className="state-card"><span className="spinner" /> Loading your posts...</div>
      ) : error ? (
        <div className="state-card error-state" role="alert">
          <p>{error}</p>
          <button className="button button-secondary" onClick={() => void retryLoadPosts()} type="button">
            Try again
          </button>
        </div>
      ) : posts.length === 0 ? (
        <div className="empty-state compact-empty">
          <span className="empty-icon"><FileText size={24} aria-hidden="true" /></span>
          <h3>No posts yet</h3>
        </div>
      ) : (
        <div className="post-grid">
          {posts.map((post) => (
            <article className="post-card" key={post.id}>
              <div className="post-meta">
                <div className="post-badges">
                  <span className="category-pill">{POST_CATEGORY_LABELS[post.category]}</span>
                  <span className={`post-type-pill post-type-${post.post_type.toLowerCase()}`}>
                    {POST_TYPE_LABELS[post.post_type]}
                  </span>
                  {post.updated_at && <span className="edited-indicator">Edited</span>}
                  {post.is_private && <span className="visibility-private-pill">Only me</span>}
                </div>
                <span className="post-location">{post.location}</span>
              </div>
              <h3><Link href={`/posts/${post.id}`}>{post.title}</Link></h3>
              <p className="post-description">{post.description}</p>
              <div className="profile-post-actions">
                <Link className="comment-count-link" href={`/posts/${post.id}`}>
                  {post.comment_count} {post.comment_count === 1 ? "comment" : "comments"}
                </Link>
                <PostReactions
                  canReact={false}
                  dislikeCount={post.dislike_count}
                  likeCount={post.like_count}
                  myReaction={post.my_reaction}
                  onChanged={updatePostReactions}
                  postId={post.id}
                />
                <PostVisibilityButton onChanged={updatePost} post={post} />
                <EditPostButton onUpdated={updatePost} post={post} />
                <DeletePostButton onDeleted={removePost} postId={post.id} />
              </div>
            </article>
          ))}
        </div>
      )}
    </ProtectedPage>
  );
}