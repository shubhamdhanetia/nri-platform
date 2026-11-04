import Link from "next/link";
import type { PostType } from "../lib/api";

export default function CommunityRideNotice({ postType, compact = false }: {
  postType?: PostType | "";
  compact?: boolean;
}) {
  const action = postType === "OFFER"
    ? <Link href="/rides/carpools/new">Offer a carpool</Link>
    : postType === "REQUEST"
      ? <Link href="/rides/new">Request a ride</Link>
      : <><Link href="/rides/new">Request a ride</Link><Link href="/rides/carpools/new">Offer a carpool</Link></>;

  return <aside className={`community-ride-notice${compact ? " is-compact" : ""}`} aria-label="Ride and carpool post guidance">
    <strong>{compact ? "Community post only, not a booking." : "Community post only, not a ride request or booking."}</strong>
    <p>It won&apos;t reserve a seat or confirm a trip. For a specific trip, route, or carpool offer, use the dedicated ride tools.</p>
    <div className="community-ride-notice-actions">{action}</div>
  </aside>;
}