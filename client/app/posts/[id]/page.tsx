"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import ProtectedPage from "../../../components/ProtectedPage";
import CommentActions from "../../../components/CommentActions";
import {
  apiRequest,
  POST_CATEGORY_LABELS,
  POST_TYPE_LABELS,
  type Comment,
  type PostDetail,
  type User,
} from "../../../lib/api";

function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export default function PostDetailsPage() {
  const params = useParams<{ id: string }>();
  const postId = Number(params.id);

  return (
    <ProtectedPage>
      {Number.isInteger(postId) && postId > 0 ? (
        <PostDetailsContent key={postId} postId={postId} />
      ) : (
        <div className="state-card error-state" role="alert">
          <p>Post not found.</p>
          <Link className="button button-secondary" href="/feed">Back to feed</Link>
        </div>
      )}
    </ProtectedPage>
  );
}

function PostDetailsContent({ postId }: { postId: number }) {
  const [post, setPost] = useState<PostDetail | null>(null);
  const [comments, setComments] = useState<Comment[]>([]);
  const [currentUserId, setCurrentUserId] = useState<number | null>(null);
  const [pageError, setPageError] = useState("");
  const [commentsError, setCommentsError] = useState("");
  const [loading, setLoading] = useState(true);
  const [commentsLoading, setCommentsLoading] = useState(true);
  const [content, setContent] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState("");
  const [success, setSuccess] = useState("");

  const loadPost = useCallback(async () => {
    if (!Number.isInteger(postId) || postId < 1) {
      throw new Error("Post not found.");
    }
    const [postResult, userResult] = await Promise.all([
      apiRequest<PostDetail>(`/posts/${postId}`),
      apiRequest<User>("/users/me"),
    ]);
    return { post: postResult, user: userResult };
  }, [postId]);

  const loadComments = useCallback(async () => {
    if (!Number.isInteger(postId) || postId < 1) {
      throw new Error("Post not found.");
    }
    return apiRequest<Comment[]>(`/posts/${postId}/comments`);
  }, [postId]);

  useEffect(() => {
    let active = true;

    loadPost()
      .then(({ post: postResult, user }) => {
        if (active) {
          setPost(postResult);
          setCurrentUserId(user.id);
        }
      })
      .catch((requestError: unknown) => {
        if (active) {
          setPageError(requestError instanceof Error ? requestError.message : "Unable to load this post.");
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    loadComments()
      .then((result) => {
        if (active) setComments(result);
      })
      .catch((requestError: unknown) => {
        if (active) {
          setCommentsError(requestError instanceof Error ? requestError.message : "Unable to load comments.");
        }
      })
      .finally(() => {
        if (active) setCommentsLoading(false);
      });

    return () => {
      active = false;
    };
  }, [loadComments, loadPost]);

  async function retryComments() {
    setCommentsLoading(true);
    setCommentsError("");
    try {
      setComments(await loadComments());
    } catch (requestError) {
      setCommentsError(requestError instanceof Error ? requestError.message : "Unable to load comments.");
    } finally {
      setCommentsLoading(false);
    }
  }

  async function submitComment(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setSubmitError("");
    setSuccess("");
    try {
      const comment = await apiRequest<Comment>(`/posts/${postId}/comments`, {
        method: "POST",
        body: JSON.stringify({ content }),
      });
      setComments((currentComments) => [...currentComments, comment]);
      setContent("");
      setSuccess("Your comment was posted.");
      setPost((currentPost) => currentPost
        ? { ...currentPost, comment_count: currentPost.comment_count + 1 }
        : currentPost);
      try {
        const refreshedComments = await loadComments();
        setComments(refreshedComments);
        setPost((currentPost) => currentPost
          ? { ...currentPost, comment_count: refreshedComments.length }
          : currentPost);
      } catch (refreshError) {
        setCommentsError(
          refreshError instanceof Error
            ? `Your comment was posted, but comments could not be refreshed: ${refreshError.message}`
            : "Your comment was posted, but comments could not be refreshed.",
        );
      }
    } catch (requestError) {
      setSubmitError(requestError instanceof Error ? requestError.message : "Unable to post your comment.");
    } finally {
      setSubmitting(false);
    }
  }

  function updateComment(updatedComment: Comment) {
    setComments((currentComments) => currentComments.map(
      (comment) => comment.id === updatedComment.id ? updatedComment : comment,
    ));
  }

  function removeComment(commentId: number) {
    setComments((currentComments) => currentComments.filter(
      (comment) => comment.id !== commentId,
    ));
    setPost((currentPost) => currentPost
      ? { ...currentPost, comment_count: Math.max(0, currentPost.comment_count - 1) }
      : currentPost);
  }

  return (
    <>
      <div className="detail-back-link">
        <Link href="/feed"><span aria-hidden="true">←</span> Back to the community</Link>
      </div>
      {loading ? (
        <div className="state-card"><span className="spinner" /> Loading post…</div>
      ) : pageError ? (
        <div className="state-card error-state" role="alert">
          <p>{pageError}</p>
          <Link className="button button-secondary" href="/feed">Back to feed</Link>
        </div>
      ) : post ? (
        <>
          <article className="post-detail-card">
            <div className="post-meta">
              <div className="post-badges">
                <span className="category-pill">{POST_CATEGORY_LABELS[post.category]}</span>
                <span className={`post-type-pill post-type-${post.post_type.toLowerCase()}`}>
                  {POST_TYPE_LABELS[post.post_type]}
                </span>
              </div>
              <span className="post-location"><span aria-hidden="true">⌖</span> {post.city}</span>
            </div>
            <h1>{post.title}</h1>
            <p className="post-detail-description">{post.description}</p>
            <div className="post-detail-author">
              {post.author.picture ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img className="author-photo" src={post.author.picture} alt="" />
              ) : (
                <span className="author-avatar">{post.author.name.charAt(0).toUpperCase()}</span>
              )}
              <div>
                <strong>{post.author.name}</strong>
                <div className="post-detail-timestamp">
                  <time dateTime={post.created_at}>{formatDate(post.created_at)}</time>
                  {post.updated_at && <span className="edited-indicator">Edited</span>}
                </div>
              </div>
            </div>
          </article>

          <section className="comments-section" aria-labelledby="comments-heading">
            <div className="comments-heading">
              <div>
                <p className="eyebrow">Join the conversation</p>
                <h2 id="comments-heading">
                  Comments <span className="count-pill">{comments.length}</span>
                </h2>
              </div>
            </div>

            <form className="comment-form" onSubmit={submitComment}>
              <label className="form-field">
                <span>Add a comment</span>
                <textarea
                  maxLength={2000}
                  onChange={(event) => {
                    setContent(event.target.value);
                    setSuccess("");
                    setSubmitError("");
                  }}
                  placeholder="Share a helpful thought or ask a follow-up…"
                  required
                  rows={4}
                  value={content}
                />
              </label>
              <div className="comment-form-footer">
                {submitError && <p className="form-error" role="alert">{submitError}</p>}
                {success && <p className="form-success" role="status">{success}</p>}
                <button
                  className="button button-primary"
                  disabled={submitting || !content.trim()}
                  type="submit"
                >
                  {submitting ? "Posting…" : "Post comment"}
                </button>
              </div>
            </form>

            {commentsLoading ? (
              <div className="state-card"><span className="spinner" /> Loading comments…</div>
            ) : commentsError ? (
              <div className="state-card error-state" role="alert">
                <p>{commentsError}</p>
                <button className="button button-secondary" onClick={() => void retryComments()} type="button">
                  Try again
                </button>
              </div>
            ) : comments.length === 0 ? (
              <div className="empty-state comments-empty">
                <span className="empty-icon">✦</span>
                <h3>Start the conversation</h3>
                <p className="muted">There are no comments yet. Add the first one.</p>
              </div>
            ) : (
              <div className="comment-list">
                {comments.map((comment) => (
                  <article className="comment-card" key={comment.id}>
                    {comment.author.picture ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img className="author-photo" src={comment.author.picture} alt="" />
                    ) : (
                      <span className="author-avatar">{comment.author.name.charAt(0).toUpperCase()}</span>
                    )}
                    <div className="comment-content">
                      <div className="comment-meta">
                        <strong>{comment.author.name}</strong>
                        <span className="comment-timestamp">
                          <time dateTime={comment.created_at}>{formatDate(comment.created_at)}</time>
                          {comment.updated_at && <span className="edited-indicator">Edited</span>}
                        </span>
                      </div>
                      <p>{comment.content}</p>
                      {comment.user_id === currentUserId && (
                        <CommentActions
                          comment={comment}
                          onDeleted={removeComment}
                          onUpdated={updateComment}
                        />
                      )}
                    </div>
                  </article>
                ))}
              </div>
            )}
          </section>
        </>
      ) : null}
    </>
  );
}
