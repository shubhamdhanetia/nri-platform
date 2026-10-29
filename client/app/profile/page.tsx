"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
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
  type User,
} from "../../lib/api";

export default function ProfilePage() {
  const [user, setUser] = useState<User | null>(null);
  const [posts, setPosts] = useState<Post[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const fetchProfile = useCallback(
    () => Promise.all([
      apiRequest<User>("/users/me"),
      apiRequest<Post[]>("/posts/me"),
    ]),
    [],
  );

  useEffect(() => {
    let active = true;
    fetchProfile()
      .then(([currentUser, userPosts]) => {
        if (active) {
          setUser(currentUser);
          setPosts(userPosts);
        }
      })
      .catch((requestError: unknown) => {
        if (active) {
          setError(requestError instanceof Error ? requestError.message : "Unable to load your profile.");
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [fetchProfile]);

  async function retryLoadProfile() {
    setLoading(true);
    setError("");
    try {
      const [currentUser, userPosts] = await fetchProfile();
      setUser(currentUser);
      setPosts(userPosts);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to load your profile.");
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
          <p className="eyebrow">Your corner of the community</p>
          <h1>My profile</h1>
        </div>
      </section>
      {loading ? (
        <div className="state-card"><span className="spinner" /> Loading your profile…</div>
      ) : error ? (
        <div className="state-card error-state" role="alert">
          <p>{error}</p>
          <button className="button button-secondary" onClick={() => void retryLoadProfile()} type="button">
            Try again
          </button>
        </div>
      ) : user ? (
        <>
          <section className="profile-card">
            {user.picture ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img className="profile-avatar" src={user.picture} alt="" />
            ) : (
              <span className="profile-avatar profile-avatar-fallback">{user.name.charAt(0).toUpperCase()}</span>
            )}
            <div>
              <h2>{user.name}</h2>
              <p className="muted">{user.email}</p>
              {user.provider && <span className="provider-label">Signed in with {user.provider}</span>}
            </div>
          </section>
          <section className="profile-posts">
            <div className="section-title-row">
              <div>
                <p className="eyebrow">Your contributions</p>
                <h2>Your posts <span className="count-pill">{posts.length}</span></h2>
              </div>
              <Link className="text-link" href="/create-post">Write a post <span aria-hidden="true">→</span></Link>
            </div>
            {posts.length === 0 ? (
              <div className="empty-state compact-empty">
                <span className="empty-icon">✦</span>
                <h3>No posts yet</h3>
                <p className="muted">Your posts will show up here when you share with the community.</p>
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
                      <span className="post-location"><span aria-hidden="true">⌖</span> {post.location}</span>
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
          </section>
        </>
      ) : null}
    </ProtectedPage>
  );
}
