"use client";

import Link from "next/link";
import { CalendarDays, Home, MapPin } from "lucide-react";
import { useState } from "react";
import { HOUSING_KINDS, ROOM_TYPES, UTILITIES, housingDate, housingExpired, housingMoney, type HousingItem } from "../lib/housing";

export function HousingPhoto({ url, title }: { url?: string; title: string }) {
  const [failedUrl, setFailedUrl] = useState<string | null>(null);
  return url && failedUrl !== url
    // User-supplied external images are loaded directly, never through an image proxy.
    // eslint-disable-next-line @next/next/no-img-element
    ? <img className="housing-photo" src={url} alt={title} loading="lazy" referrerPolicy="no-referrer" onError={() => setFailedUrl(url)} />
    : <div className="housing-photo housing-photo-placeholder"><Home size={30} aria-hidden="true" /><span>{url ? "Photo unavailable" : "No photos added"}</span></div>;
}

export function HousingStatusBadge({ item }: { item: HousingItem }) {
  const label = item.status === "FILLED" ? (item.kind === "LISTING" ? "No longer available" : "Resolved")
    : item.status === "ARCHIVED" ? "Archived" : housingExpired(item) ? "Expired" : null;
  return <>{label && <span className="post-status-pill">{label}</span>}{item.is_private && <span className="visibility-private-pill">Only me</span>}</>;
}

export default function HousingCard({ item, children }: { item: HousingItem; children?: React.ReactNode }) {
  return <article className="housing-card">
    <Link className="housing-card-image" href={`/housing/${item.id}`} aria-label={`View ${item.title}`}>
      <HousingPhoto url={item.photo_urls[0]} title={item.title} />
    </Link>
    <div className="housing-card-body">
      <div className="post-badges"><span className="category-pill">{HOUSING_KINDS[item.kind]}</span><HousingStatusBadge item={item} /></div>
      <h2><Link href={`/housing/${item.id}`}>{item.title}</Link></h2>
      <p className="housing-card-location"><MapPin size={14} aria-hidden="true" />{item.kind !== "LISTING" ? "Preferred area: " : ""}{item.location || [item.area, item.city, item.country_code].filter(Boolean).join(", ")}</p>
      <p className="housing-price">{housingMoney(item.amount, item.currency)} <span>/ {item.price_period.toLowerCase()}{item.kind !== "LISTING" ? " budget" : ""}</span></p>
      <div className="housing-facts"><span>{ROOM_TYPES[item.room_type]}</span><span>{UTILITIES[item.utilities]}</span></div>
      <p className="housing-card-location"><CalendarDays size={14} aria-hidden="true" />{item.kind === "LISTING" ? "Available" : "Move-in"} {housingDate(item.available_from)}{item.available_until ? ` – ${housingDate(item.available_until)}` : ""}</p>
      <p className="housing-card-excerpt">{item.description}</p>
      {children || <Link className="text-link" href={`/housing/${item.id}`}>View details &rarr;</Link>}
    </div>
  </article>;
}
