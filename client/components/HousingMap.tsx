"use client";

import { useMemo } from "react";
import CommunityMap from "./CommunityMap";
import type { PostSearchBounds } from "../lib/api";
import { housingMoney, type HousingItem } from "../lib/housing";

export default function HousingMap({ items, ...props }: {
  items: HousingItem[];
  fullscreen: boolean;
  center: [number, number];
  initialZoom: number;
  selectedPostId: string | null;
  selectionVersion: number;
  onSelectPost: (id: string) => void;
  onBoundsChange: (bounds: PostSearchBounds) => void;
  onCenterChange: (center: [number, number]) => void;
  onViewportChange: (center: [number, number], zoom: number) => void;
}) {
  const points = useMemo(() => items.flatMap(item => item.latitude === null || item.longitude === null ? [] : [{
    id: item.id, latitude: item.latitude, longitude: item.longitude,
    title: item.title,
    description: `${item.kind === "LISTING" ? "Place available" : "Preferred search area"} · ${housingMoney(item.amount, item.currency)} / ${item.price_period.toLowerCase()} · ${item.location}`,
    href: `/housing/${item.id}`, linkLabel: "View housing details",
  }]), [items]);
  return <CommunityMap {...props} posts={points} />;
}
