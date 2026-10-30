"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowDown, ArrowUpRight, FileText, Users } from "lucide-react";
import ProtectedPage from "../../../components/ProtectedPage";
import { CopyProfileLink, MemberDetails, MemberIdentity } from "../../../components/MemberProfile";
import { apiRequest, isUuid, POST_CATEGORY_LABELS, POST_TYPE_LABELS, type MemberProfile, type MemberPost, type MemberPostsResponse } from "../../../lib/api";

export default function MemberProfilePage() {
  const { id } = useParams<{ id: string }>();
  return <ProtectedPage>
    {isUuid(id) ? <MemberProfileContent key={id} userId={id} /> : <div className="state-card error-state" role="alert">
      <p>Member not found.</p><Link className="button button-secondary" href="/explore">Back to community</Link>
    </div>}
  </ProtectedPage>;
}

function MemberProfileContent({ userId }: { userId: string }) {
  const [profile, setProfile] = useState<MemberProfile | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [attempt, setAttempt] = useState(0);
  const [posts, setPosts] = useState<MemberPost[]>([]);
  const [hasMore, setHasMore] = useState(false);
  const [postsLoading, setPostsLoading] = useState(true);
  const [postsError, setPostsError] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    apiRequest<MemberProfile>(`/users/${userId}`, { signal: controller.signal })
      .then(setProfile)
      .catch((requestError: unknown) => {
        if (!controller.signal.aborted) setError(requestError instanceof Error ? requestError.message : "Unable to load this profile.");
      })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    apiRequest<MemberPostsResponse>(`/users/${userId}/posts`, { signal: controller.signal })
      .then(result => { setPosts(result.posts); setHasMore(result.has_more); })
      .catch((requestError: unknown) => {
        if (!controller.signal.aborted) setPostsError(requestError instanceof Error ? requestError.message : "Unable to load posts.");
      })
      .finally(() => { if (!controller.signal.aborted) setPostsLoading(false); });
    return () => controller.abort();
  }, [userId, attempt]);

  async function loadMorePosts() {
    setPostsLoading(true);
    setPostsError("");
    try {
      const result = await apiRequest<MemberPostsResponse>(`/users/${userId}/posts?offset=${posts.length}`);
      setPosts(current => [...current, ...result.posts]);
      setHasMore(result.has_more);
    } catch (requestError) {
      setPostsError(requestError instanceof Error ? requestError.message : "Unable to load posts.");
    } finally {
      setPostsLoading(false);
    }
  }

  if (loading) return <div className="state-card"><span className="spinner" /> Loading member profile...</div>;
  if (error || !profile) return <div className="state-card error-state" role="alert">
    <p>{error || "Member not found."}</p>
    <button type="button" className="button button-secondary" onClick={() => { setLoading(true); setPostsLoading(true); setError(""); setPostsError(""); setAttempt(current => current + 1); }}>Try again</button>
    <Link className="text-link" href="/explore">Back to community</Link>
  </div>;

  return <div className="member-profile-page">
    <section className="page-heading"><div><p className="eyebrow">Your community</p><h1>Member profile</h1></div></section>
    <MemberIdentity name={profile.name} picture={profile.picture} memberSince={profile.member_since} />
    <div className="member-profile-actions"><CopyProfileLink userId={userId} /><span className="member-audience"><Users size={16} aria-hidden="true" /> Signed-in members only</span></div>
    <MemberDetails profile={profile} />
    <section className="member-profile-section" aria-labelledby="member-posts-heading">
      <div className="section-title-row"><h2 id="member-posts-heading">Public posts</h2></div>
      {posts.length > 0 && <div className="post-grid">
        {posts.map(post => <article className="post-card" key={post.id}>
          <div className="post-meta"><div className="post-badges"><span className="category-pill">{POST_CATEGORY_LABELS[post.category]}</span><span className={`post-type-pill post-type-${post.post_type.toLowerCase()}`}>{POST_TYPE_LABELS[post.post_type]}</span></div><span className="post-location">{post.city}</span></div>
          <h3><Link href={`/posts/${post.id}`}>{post.title}</Link></h3>
          <p className="post-description">{post.description}</p>
          <div className="member-post-footer"><span>{post.comment_count} {post.comment_count === 1 ? "comment" : "comments"}</span><Link className="button button-secondary" href={`/posts/${post.id}`}>View post <ArrowUpRight size={16} aria-hidden="true" /></Link></div>
        </article>)}
      </div>}
      {postsLoading && <div className="state-card" role="status"><span className="spinner" /> Loading posts...</div>}
      {postsError ? <div className="state-card error-state" role="alert"><p>{postsError}</p><button type="button" className="button button-secondary" disabled={postsLoading} onClick={() => void loadMorePosts()}>Try again</button></div> : !postsLoading && posts.length === 0 && <div className="empty-state compact-empty"><span className="empty-icon"><FileText size={24} aria-hidden="true" /></span><h3>No public posts yet</h3></div>}
      {hasMore && !postsError && <button className="button button-secondary member-load-more" type="button" disabled={postsLoading} onClick={() => void loadMorePosts()}><ArrowDown size={16} aria-hidden="true" />{postsLoading ? "Loading..." : "Load more posts"}</button>}
    </section>
  </div>;
}