import Link from "next/link";
import { ArrowUpRight, Car } from "lucide-react";

export default function RideCommunityNotice({ compact = false }: { compact?: boolean }) {
  return (
    <aside className="ride-community-notice" aria-label="Community rides information">
      <Car size={20} aria-hidden="true" />
      <div>
        <strong>Ride discussions, not ride requests</strong>
        <p>
          {compact
            ? "This is a community post. Posting or commenting here does not create a ride request or booking."
            : "These are community posts about rides. Posting or commenting here does not create a ride request or booking. To request a ride or offer to drive, use the dedicated Rides section."}
        </p>
        <div className="ride-community-notice-links">
          <Link className="text-link" href="/rides">Browse ride requests <ArrowUpRight size={14} aria-hidden="true" /></Link>
          <Link className="text-link" href="/rides/new">Request a ride <ArrowUpRight size={14} aria-hidden="true" /></Link>
        </div>
      </div>
    </aside>
  );
}
