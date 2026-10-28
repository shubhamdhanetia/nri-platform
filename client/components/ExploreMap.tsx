"use client";

import CommunityMap from "./CommunityMap";
import { useMemo } from "react";
import type { Post, PostSearchBounds } from "../lib/api";

export default function ExploreMap(props: {
  posts: Post[];
  fullscreen: boolean;
  selectedPostId: number | null;
  selectionVersion: number;
  onSelectPost: (postId: number) => void;
  onBoundsChange: (bounds: PostSearchBounds) => void;
  onCenterChange: (center: [number, number]) => void;
  onViewportChange?: (center: [number, number], zoom: number) => void;
  center: [number, number];
  initialZoom: number;
}) {
  const points = useMemo(() => props.posts.map(post => ({
    id: post.id,
    latitude: post.latitude,
    longitude: post.longitude,
    title: post.title,
    description: post.city,
    href: `/posts/${post.id}`,
    linkLabel: "View post details",
  })), [props.posts]);
  return <CommunityMap {...props} posts={points} />;
}
