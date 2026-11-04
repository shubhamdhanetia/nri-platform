import Link from "next/link";
import type { PostType } from "../lib/api";

export default function CommunityHousingNotice({ postType, compact = false }: {
  postType?: PostType | "";
  compact?: boolean;
}) {
  const action = postType === "OFFER"
    ? <Link href="/housing/new">List a place</Link>
    : postType === "REQUEST"
      ? <Link href="/housing/new?kind=REQUEST">Post a housing request</Link>
      : <><Link href="/housing">Find a place</Link><Link href="/housing/people">Find roommates</Link></>;

  return <aside className="community-housing-notice" aria-label="Housing post guidance">
    <strong>{compact ? "Community post only, not a housing listing." : "Community post only, not a housing listing or request."}</strong>
    <p>It won&apos;t create a structured listing or request. For availability, budget, filters, and private inquiries, use the dedicated Housing section.</p>
    <div className="community-housing-notice-actions">{action}</div>
  </aside>;
}