import type { Post } from "../lib/api";

export function postClosedLabel(post: Pick<Post, "post_type">) {
  return post.post_type === "REQUEST" ? "Resolved" : "No longer available";
}

export default function PostStatus({ post }: { post: Pick<Post, "status" | "post_type"> }) {
  return post.status === "CLOSED"
    ? <span className="post-status-pill">{postClosedLabel(post)}</span>
    : null;
}
